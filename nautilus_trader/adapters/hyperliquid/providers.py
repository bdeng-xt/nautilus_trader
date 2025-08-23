# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

import json
import asyncio
from decimal import Decimal
from typing import Any

from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID_VENUE
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.model.currencies import Currency
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


class HyperliquidInstrumentProvider(InstrumentProvider):
    """
    Provides Nautilus instrument definitions from Hyperliquid.

    Parameters
    ----------
    client : HyperliquidHttpClient
        The Hyperliquid HTTP client.
    clock : LiveClock
        The clock instance.
    config : InstrumentProviderConfig, optional
        The instrument provider configuration.

    """

    def __init__(
        self,
        client: Any,  # HyperliquidHttpClient from Rust bindings
        clock: LiveClock,
        config: InstrumentProviderConfig | None = None,
        venue: Venue = HYPERLIQUID_VENUE,
    ) -> None:
        super().__init__(config=config)
        self._clock = clock
        self._client = client
        self._venue = venue
        self._log_warnings = config.log_warnings if config else True

    async def load_all_async(self, filters: dict[str, Any] | None = None) -> None:
        """
        Load all instruments asynchronously.
        """
        filters_str = "..." if not filters else f" with filters {filters}..."
        self._log.info(f"Loading all instruments{filters_str}")

        await self._load_instruments()
        self._log.info(f"Loaded {len(self._instruments)} instruments")

    async def load_ids_async(
        self,
        instrument_ids: list[InstrumentId],
        filters: dict | None = None,
    ) -> None:
        """
        Load specific instruments by their IDs.
        """
        if not instrument_ids:
            self._log.info("No instrument IDs given for loading.")
            return

        # Check all instrument IDs have correct venue
        for instrument_id in instrument_ids:
            PyCondition.equal(
                instrument_id.venue, 
                self._venue, 
                "instrument_id.venue", 
                self._venue.value
            )

        # For now, load all instruments and filter
        await self._load_instruments()

    async def load_async(self, instrument_id: InstrumentId, filters: dict | None = None) -> None:
        """
        Load a single instrument by its ID.
        """
        PyCondition.not_none(instrument_id, "instrument_id")
        PyCondition.equal(
            instrument_id.venue, 
            self._venue, 
            "instrument_id.venue", 
            self._venue.value
        )

        filters_str = "..." if not filters else f" with filters {filters}..."
        self._log.debug(f"Loading instrument {instrument_id}{filters_str}.")

        # For now, load all instruments
        await self._load_instruments()

    async def _load_instruments(self) -> None:
        """
        Load instruments from Hyperliquid API.
        """
        try:
            # Get instruments from Rust HTTP client
            # The client should return JSON string that we can parse
            instruments_response = await asyncio.get_event_loop().run_in_executor(
                None, self._get_instruments_sync
            )
            
            if not instruments_response:
                self._log.error("Failed to fetch instruments from Hyperliquid")
                return

            # Parse instruments response
            instruments_data = json.loads(instruments_response)
            ts_init = self._clock.timestamp_ns()

            for instrument_data in instruments_data:
                try:
                    instrument = self._parse_instrument(instrument_data, ts_init)
                    if instrument:
                        self.add(instrument)
                        # Add USD currency if not already added
                        usd = Currency.from_str("USD")
                        self.add_currency(usd)
                except Exception as e:
                    if self._log_warnings:
                        self._log.warning(f"Failed to parse instrument: {e}")

        except Exception as e:
            self._log.error(f"Error loading instruments: {e}")

    def _get_instruments_sync(self) -> str:
        """
        Synchronous wrapper for getting instruments (to be called in executor).
        """
        # This will call the Rust client synchronously
        return self._client.get_instruments()

    def _parse_instrument(self, data: dict, ts_init: int) -> CryptoPerpetual | None:
        """
        Parse instrument data from Hyperliquid API response.
        """
        try:
            name = data.get("name", "")
            sz_decimals = data.get("sz_decimals", 0)
            
            # Create symbol (Hyperliquid uses perpetual contracts)
            symbol = Symbol(f"{name}-PERP")
            instrument_id = InstrumentId(symbol, self._venue)

            # Base currency is the asset (e.g., BTC, ETH)
            base_currency = Currency.from_str(name)
            # Quote currency is USD for Hyperliquid
            quote_currency = Currency.from_str("USD")

            # Calculate precision based on sz_decimals
            size_precision = sz_decimals
            price_precision = 8  # Default price precision for crypto

            # Create instrument
            instrument = CryptoPerpetual(
                instrument_id=instrument_id,
                raw_symbol=Symbol(name),
                base_currency=base_currency,
                quote_currency=quote_currency,
                price_precision=price_precision,
                size_precision=size_precision,
                price_increment=Price(10 ** -price_precision, price_precision),
                size_increment=Quantity(10 ** -size_precision, size_precision),
                maker_fee=Decimal("0.0002"),  # 0.02% default maker fee
                taker_fee=Decimal("0.0005"),  # 0.05% default taker fee
                margin_init=Decimal("0.1"),   # 10% initial margin
                margin_maint=Decimal("0.05"), # 5% maintenance margin
                ts_event=ts_init,
                ts_init=ts_init,
            )

            return instrument

        except Exception as e:
            self._log.warning(f"Failed to parse instrument {data}: {e}")
            return None
