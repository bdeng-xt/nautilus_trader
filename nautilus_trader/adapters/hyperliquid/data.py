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
Provides a data client for Hyperliquid.

This module provides the `HyperliquidDataClient` class which connects to the
Hyperliquid WebSocket API and HTTP API to provide real-time market data.
"""

import asyncio
from typing import Any

from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID_VENUE
from nautilus_trader.adapters.hyperliquid.providers import HyperliquidInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.enums import LogColor
from nautilus_trader.core import nautilus_pyo3
from nautilus_trader.data.messages import DataRequest
from nautilus_trader.data.messages import SubscribeBars
from nautilus_trader.data.messages import SubscribeInstrument
from nautilus_trader.data.messages import SubscribeInstruments
from nautilus_trader.data.messages import SubscribeOrderBook
from nautilus_trader.data.messages import SubscribeQuoteTicks
from nautilus_trader.data.messages import SubscribeTradeTicks
from nautilus_trader.data.messages import UnsubscribeBars
from nautilus_trader.data.messages import UnsubscribeInstrument
from nautilus_trader.data.messages import UnsubscribeInstruments
from nautilus_trader.data.messages import UnsubscribeOrderBook
from nautilus_trader.data.messages import UnsubscribeQuoteTicks
from nautilus_trader.data.messages import UnsubscribeTradeTicks
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import InstrumentId


class HyperliquidDataClient(LiveMarketDataClient):
    """
    Provides a data client for the `Hyperliquid` DEX.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    client : nautilus_pyo3.HyperliquidHttpClient
        The Hyperliquid HTTP client.
    ws_client : nautilus_pyo3.HyperliquidWebSocketClient
        The Hyperliquid WebSocket client.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : HyperliquidInstrumentProvider
        The instrument provider.
    base_url_http : str, optional
        The base HTTP URL.
    base_url_ws : str, optional
        The base WebSocket URL.
    update_instruments_interval_mins : int, optional
        The interval for updating instruments.
    name : str, optional
        The custom client name.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: nautilus_pyo3.HyperliquidHttpClient,
        ws_client: nautilus_pyo3.HyperliquidWebSocketClient,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: HyperliquidInstrumentProvider,
        base_url_http: str | None = None,
        base_url_ws: str | None = None,
        update_instruments_interval_mins: int | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=ClientId(name or "HYPERLIQUID"),
            venue=HYPERLIQUID_VENUE,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
        )

        # Clients
        self._http_client = client
        self._ws_client = ws_client

        # Configuration
        self._base_url_http = base_url_http
        self._base_url_ws = base_url_ws
        self._update_instruments_interval_mins = update_instruments_interval_mins

        # Subscription management
        self._subscribed_instruments: set[InstrumentId] = set()

    @property
    def hyperliquid_instrument_provider(self) -> HyperliquidInstrumentProvider:
        return self._instrument_provider

    async def _connect(self) -> None:
        # Load instruments
        self._log.info("Loading Hyperliquid instruments...")
        await self._instrument_provider.load_all_async()
        
        # Send instruments to data engine
        self._send_all_instruments_to_data_engine()

        # Connect WebSocket
        if self._ws_client:
            self._log.info("Connecting to Hyperliquid WebSocket...")
            await self._ws_client.connect()
            self._log.info("Connected to Hyperliquid WebSocket", LogColor.GREEN)

    async def _disconnect(self) -> None:
        # Disconnect WebSocket
        if self._ws_client:
            self._log.info("Disconnecting from Hyperliquid WebSocket...")
            await self._ws_client.disconnect()
            self._log.info("Disconnected from Hyperliquid WebSocket", LogColor.BLUE)

        # Clear subscriptions
        self._subscribed_instruments.clear()

    def _send_all_instruments_to_data_engine(self) -> None:
        """Send all instruments to the data engine."""
        for currency in self._instrument_provider.currencies().values():
            self._cache.add_currency(currency)

        instruments = self._instrument_provider.get_all()
        self._log.info(f"📊 Sending {len(instruments)} instruments to data engine")
        
        for instrument in instruments.values():
            # Add to cache first
            self._cache.add_instrument(instrument)
            # Then send to data engine
            self._handle_data(instrument)

    # -- SUBSCRIPTIONS ----------------------------------------------------------------------------

    async def _subscribe_instrument(self, command: SubscribeInstrument) -> None:
        # Instruments are loaded on connection
        pass

    async def _subscribe_instruments(self, command: SubscribeInstruments) -> None:
        # Instruments are loaded on connection
        pass

    async def _subscribe_order_book_deltas(self, command: SubscribeOrderBook) -> None:
        self._subscribed_instruments.add(command.instrument_id)
        self._log.info(f"📚 Subscribed to order book for {command.instrument_id}")
        
        # Extract coin symbol for subscription
        coin = command.instrument_id.symbol.value.replace("-PERP", "")
        if self._ws_client:
            await self._ws_client.subscribe_l2_book(coin)

    async def _subscribe_quote_ticks(self, command: SubscribeQuoteTicks) -> None:
        self._subscribed_instruments.add(command.instrument_id)
        self._log.info(f"📊 Subscribed to quotes for {command.instrument_id}")
        
        if self._ws_client:
            await self._ws_client.subscribe_all_mids()

    async def _subscribe_trade_ticks(self, command: SubscribeTradeTicks) -> None:
        self._subscribed_instruments.add(command.instrument_id)
        self._log.info(f"📈 Subscribed to trades for {command.instrument_id}")
        
        # Extract coin symbol for subscription
        coin = command.instrument_id.symbol.value.replace("-PERP", "")
        if self._ws_client:
            await self._ws_client.subscribe_trades(coin)

    async def _subscribe_bars(self, command: SubscribeBars) -> None:
        self._log.error("Bar subscriptions are not yet supported")

    async def _unsubscribe_instrument(self, command: UnsubscribeInstrument) -> None:
        pass

    async def _unsubscribe_instruments(self, command: UnsubscribeInstruments) -> None:
        pass

    async def _unsubscribe_order_book_deltas(self, command: UnsubscribeOrderBook) -> None:
        self._subscribed_instruments.discard(command.instrument_id)
        self._log.info(f"📚 Unsubscribed from order book for {command.instrument_id}")

    async def _unsubscribe_quote_ticks(self, command: UnsubscribeQuoteTicks) -> None:
        self._subscribed_instruments.discard(command.instrument_id)
        self._log.info(f"📊 Unsubscribed from quotes for {command.instrument_id}")

    async def _unsubscribe_trade_ticks(self, command: UnsubscribeTradeTicks) -> None:
        self._subscribed_instruments.discard(command.instrument_id)
        self._log.info(f"📈 Unsubscribed from trades for {command.instrument_id}")

    async def _unsubscribe_bars(self, command: UnsubscribeBars) -> None:
        pass

    # -- REQUESTS ---------------------------------------------------------------------------------

    async def _request_instrument(self, request: DataRequest) -> None:
        # Instruments are pre-loaded
        pass

    async def _request_instruments(self, request: DataRequest) -> None:
        # Instruments are pre-loaded
        pass

    async def _request_quote_ticks(self, request: DataRequest) -> None:
        self._log.error("Historical quote tick requests are not supported")

    async def _request_trade_ticks(self, request: DataRequest) -> None:
        self._log.error("Historical trade tick requests are not supported")

    async def _request_bars(self, request: DataRequest) -> None:
        self._log.error("Historical bar requests are not supported")