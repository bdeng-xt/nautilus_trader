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

"""
Instrument provider for Hyperliquid.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from nautilus_trader.adapters.hyperliquid.config import HyperliquidDataClientConfig
from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID_VENUE
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.model.instruments.crypto_perpetual import CryptoPerpetual
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AssetClass, InstrumentClass
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Currency, Money, Price, Quantity
from nautilus_trader.common.providers import InstrumentProvider

if TYPE_CHECKING:
    from collections.abc import Coroutine


class HyperliquidInstrumentProvider(InstrumentProvider):
    """
    Provides a means of loading instruments from Hyperliquid.

    Parameters
    ----------
    client : HyperliquidHttpClient
        The Hyperliquid HTTP client.
    config : HyperliquidDataClientConfig
        The data client configuration.

    """

    def __init__(
        self,
        client: Any,  # HyperliquidHttpClient type hint causes circular import
        config: HyperliquidDataClientConfig,
    ) -> None:
        super().__init__()

        self._client = client
        self._config = config
        
        # Cache for loaded instruments
        self._instruments: dict[InstrumentId, Instrument] = {}

    async def load_all_async(self, correlation_id: UUID4 | None = None) -> None:
        """
        Load all instruments for the Hyperliquid venue.

        Parameters
        ----------
        correlation_id : UUID4, optional
            The correlation ID for the request.

        """
        PyCondition.not_none(self._client, "client")
        
        try:
            # Get market metadata from Hyperliquid
            meta = await self._client.get_meta()
            
            instruments: list[Instrument] = []
            
            # Parse universe (perpetual futures)
            if hasattr(meta, 'universe') and meta.universe:
                for asset_info in meta.universe:
                    instrument = self._parse_instrument_info(asset_info)
                    if instrument:
                        instruments.append(instrument)
                        self._instruments[instrument.id] = instrument

            # Load instruments into the provider
            self.add_instruments(instruments)
            
            self._log.info(f"Loaded {len(instruments)} Hyperliquid instruments")
            
        except Exception as e:
            self._log.error(f"Failed to load Hyperliquid instruments: {e}")

    async def load_ids_async(
        self,
        instrument_ids: list[InstrumentId],
        correlation_id: UUID4 | None = None,
    ) -> None:
        """
        Load specific instruments by their IDs.

        Parameters
        ----------
        instrument_ids : list[InstrumentId]
            The instrument IDs to load.
        correlation_id : UUID4, optional
            The correlation ID for the request.

        """
        # For now, we load all instruments and filter
        await self.load_all_async(correlation_id)

    async def load_async(
        self,
        instrument_id: InstrumentId,
        correlation_id: UUID4 | None = None,
    ) -> None:
        """
        Load a specific instrument.

        Parameters
        ----------
        instrument_id : InstrumentId
            The instrument ID to load.
        correlation_id : UUID4, optional
            The correlation ID for the request.

        """
        # Check if already loaded
        if instrument_id in self._instruments:
            return

        # Load all instruments (Hyperliquid API doesn't support single instrument queries)
        await self.load_all_async(correlation_id)

    def _parse_instrument_info(self, asset_info: Any) -> Instrument | None:
        """
        Parse instrument information from Hyperliquid API response.

        Parameters
        ----------
        asset_info : Any
            The asset information from the API.

        Returns
        -------
        Instrument | None
            The parsed instrument or None if parsing failed.

        """
        try:
            # Extract asset information
            if hasattr(asset_info, 'name'):
                symbol_name = asset_info.name
            else:
                # Handle dictionary format
                symbol_name = asset_info.get('name', '')

            if not symbol_name:
                return None

            # Create instrument ID
            symbol = Symbol(f"{symbol_name}-USD")
            instrument_id = InstrumentId(symbol, HYPERLIQUID_VENUE)

            # Extract size decimals for precision
            if hasattr(asset_info, 'szDecimals'):
                size_decimals = asset_info.szDecimals
            else:
                size_decimals = asset_info.get('szDecimals', 6)

            # Calculate tick size and step size
            price_precision = 6  # Hyperliquid typically uses 6 decimal places for prices
            size_precision = max(0, size_decimals)
            
            tick_size = Decimal(f"1e-{price_precision}")
            step_size = Decimal(f"1e-{size_precision}")

            # Extract maximum leverage
            if hasattr(asset_info, 'maxLeverage'):
                max_leverage = asset_info.maxLeverage
            else:
                max_leverage = asset_info.get('maxLeverage', 50)

            # Create the instrument (CryptoPerpetual for Hyperliquid)
            instrument = CryptoPerpetual(
                instrument_id=instrument_id,
                raw_symbol=Symbol(symbol_name),
                base_currency=self._get_base_currency(symbol_name),
                quote_currency=USD,  # All Hyperliquid perpetuals are quoted in USD
                settlement_currency=USD,
                is_inverse=False,  # Hyperliquid uses linear contracts
                price_precision=price_precision,
                size_precision=size_precision,
                price_increment=Price(tick_size, precision=price_precision),
                size_increment=Quantity(step_size, precision=size_precision),
                max_quantity=None,  # Not specified by Hyperliquid
                min_quantity=Quantity(step_size, precision=size_precision),
                max_notional=None,  # Not specified by Hyperliquid
                min_notional=Money(1.0, USD),  # Minimum $1 notional
                max_price=None,  # Not specified
                min_price=Price(tick_size, precision=price_precision),
                margin_init=Decimal(1) / Decimal(max_leverage),  # Initial margin = 1/leverage
                margin_maint=Decimal(1) / Decimal(max_leverage * 2),  # Maintenance margin (estimated)
                maker_fee=Decimal("0.0002"),  # 0.02% (typical for Hyperliquid)
                taker_fee=Decimal("0.0005"),  # 0.05% (typical for Hyperliquid)
                ts_event=0,
                ts_init=0,
            )

            return instrument

        except Exception as e:
            self._log.error(f"Failed to parse instrument info {asset_info}: {e}")
            return None

    def _get_base_currency(self, symbol: str) -> Currency:
        """
        Get the base currency for a symbol.

        Parameters
        ----------
        symbol : str
            The symbol name.

        Returns
        -------
        Currency
            The base currency.

        """
        # Map common symbols to currencies
        currency_map = {
            "BTC": Currency.from_str("BTC"),
            "ETH": Currency.from_str("ETH"),
            "SOL": Currency.from_str("SOL"),
            "AVAX": Currency.from_str("AVAX"),
            "MATIC": Currency.from_str("MATIC"),
            "ADA": Currency.from_str("ADA"),
            "DOT": Currency.from_str("DOT"),
            "LINK": Currency.from_str("LINK"),
            "UNI": Currency.from_str("UNI"),
            "AAVE": Currency.from_str("AAVE"),
        }

        # Try to get from map, otherwise create new currency
        if symbol in currency_map:
            return currency_map[symbol]
        else:
            return Currency.from_str(symbol)

    def get_all(self) -> dict[InstrumentId, Instrument]:
        """
        Return all loaded instruments.

        Returns
        -------
        dict[InstrumentId, Instrument]
            All loaded instruments.

        """
        return self._instruments.copy()

    def find(self, instrument_id: InstrumentId) -> Instrument | None:
        """
        Find an instrument by its ID.

        Parameters
        ----------
        instrument_id : InstrumentId
            The instrument ID to find.

        Returns
        -------
        Instrument | None
            The instrument if found, otherwise None.

        """
        return self._instruments.get(instrument_id)
