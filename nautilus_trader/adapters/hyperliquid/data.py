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

import asyncio
import json
from decimal import Decimal
from typing import Any

from nautilus_trader.adapters.hyperliquid.config import HyperliquidDataClientConfig
from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID
from nautilus_trader.adapters.hyperliquid.providers import HyperliquidInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.enums import LogColor
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.data.messages import RequestBars
from nautilus_trader.data.messages import RequestInstrument
from nautilus_trader.data.messages import RequestInstruments
from nautilus_trader.data.messages import RequestQuoteTicks
from nautilus_trader.data.messages import RequestTradeTicks
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
from nautilus_trader.model.currencies import Currency
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


class HyperliquidDataClient(LiveMarketDataClient):
    """
    Provides a data client for the Hyperliquid exchange.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    http_client : Any
        The Hyperliquid HTTP client (from Rust).
    ws_client : Any
        The Hyperliquid WebSocket client (from Rust).
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    instrument_provider : HyperliquidInstrumentProvider
        The instrument provider.
    config : HyperliquidDataClientConfig
        The configuration for the client.
    name : str, optional
        The custom client ID.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        http_client: Any,
        ws_client: Any,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: HyperliquidInstrumentProvider,
        config: HyperliquidDataClientConfig,
        name: str | None,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=ClientId(name or HYPERLIQUID),
            venue=None,  # Not applicable
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
        )
        self._instrument_provider: HyperliquidInstrumentProvider = instrument_provider

        # Configuration
        self._config = config
        self._log.info(f"{config.http_timeout_secs=}", LogColor.BLUE)

        # HTTP API
        self._http_client = http_client

        # WebSocket API
        self._ws_client = ws_client
        self._ws_task: asyncio.Task | None = None
        self._subscriptions: set[str] = set()

    @property
    def hyperliquid_instrument_provider(self) -> HyperliquidInstrumentProvider:
        return self._instrument_provider

    async def _connect(self) -> None:
        await self._instrument_provider.initialize()
        self._send_all_instruments_to_data_engine()

        # Connect WebSocket client
        if self._ws_client:
            self._log.info("Connecting to Hyperliquid WebSocket...")
            
            # Start WebSocket connection and message handling
            self._ws_task = asyncio.create_task(self._run_websocket())
            await asyncio.sleep(1.0)  # Give it time to connect
            
            self._log.info("Connected to Hyperliquid WebSocket", LogColor.GREEN)

    async def _disconnect(self) -> None:
        # Cancel WebSocket task
        if self._ws_task:
            self._log.info("Disconnecting WebSocket...")
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None

        # Clear subscriptions
        self._subscriptions.clear()

    def _send_all_instruments_to_data_engine(self) -> None:
        for currency in self._instrument_provider.currencies().values():
            self._cache.add_currency(currency)

        for instrument in self._instrument_provider.get_all().values():
            self._handle_data(instrument)

    async def _run_websocket(self) -> None:
        """
        Run the WebSocket message loop.
        """
        try:
            # Connect to WebSocket using Rust client
            await asyncio.get_event_loop().run_in_executor(None, self._ws_client.connect)
            
            # Message handling loop
            while True:
                # Read message from Rust WebSocket client
                message = await asyncio.get_event_loop().run_in_executor(
                    None, self._ws_client.read_message
                )
                
                if message:
                    await self._handle_ws_message(message)
                else:
                    # No message, small delay to prevent tight loop
                    await asyncio.sleep(0.001)

        except asyncio.CancelledError:
            self._log.info("WebSocket task cancelled")
            # Disconnect WebSocket
            await asyncio.get_event_loop().run_in_executor(None, self._ws_client.disconnect)
        except Exception as e:
            self._log.error(f"WebSocket error: {e}")

    async def _handle_ws_message(self, message_json: str) -> None:
        """
        Handle WebSocket message from Hyperliquid.
        """
        try:
            message = json.loads(message_json)
            channel = message.get("channel", "")
            data = message.get("data", {})

            if channel == "trades":
                await self._handle_trades(data)
            elif channel == "l2Book":
                await self._handle_order_book(data)
            elif channel == "allMids":
                await self._handle_all_mids(data)

        except Exception as e:
            self._log.error(f"Error handling WebSocket message: {e}")

    async def _handle_trades(self, trades_data: list) -> None:
        """
        Handle trade data from WebSocket.
        """
        for trade in trades_data:
            try:
                coin = trade.get("coin", "")
                instrument_id = InstrumentId(Symbol(f"{coin}-PERP"), self._config.venue)
                
                # Parse trade data
                price = Price.from_str(trade.get("px", "0"))
                size = Quantity.from_str(trade.get("sz", "0"))
                trade_id = TradeId(str(trade.get("tid", 0)))
                ts_event = int(trade.get("time", 0)) * 1_000_000  # Convert to nanoseconds

                # Create trade tick
                trade_tick = TradeTick(
                    instrument_id=instrument_id,
                    price=price,
                    size=size,
                    aggressor_side=None,  # Hyperliquid doesn't provide aggressor side directly
                    trade_id=trade_id,
                    ts_event=ts_event,
                    ts_init=self._clock.timestamp_ns(),
                )

                self._handle_data(trade_tick)

            except Exception as e:
                self._log.warning(f"Failed to parse trade: {e}")

    async def _handle_order_book(self, book_data: dict) -> None:
        """
        Handle order book data from WebSocket.
        """
        try:
            coin = book_data.get("coin", "")
            instrument_id = InstrumentId(Symbol(f"{coin}-PERP"), self._config.venue)
            levels = book_data.get("levels", [[], []])
            
            if len(levels) >= 2:
                bids = levels[0] if len(levels) > 0 else []
                asks = levels[1] if len(levels) > 1 else []
                
                # Create order book snapshot
                # Note: This is a simplified implementation
                # In a full implementation, you'd create proper OrderBookDeltas
                
        except Exception as e:
            self._log.warning(f"Failed to parse order book: {e}")

    async def _handle_all_mids(self, mids_data: dict) -> None:
        """
        Handle all mids data from WebSocket.
        """
        try:
            mids = mids_data.get("mids", {})
            
            for symbol, price_str in mids.items():
                try:
                    # Clean symbol name (remove @ prefix for numbered symbols)
                    clean_symbol = symbol
                    if symbol.startswith("@"):
                        continue  # Skip numbered symbols for now
                    
                    instrument_id = InstrumentId(Symbol(f"{clean_symbol}-PERP"), self._config.venue)
                    price = Price.from_str(price_str)
                    ts_event = self._clock.timestamp_ns()

                    # Create quote tick (mid price as both bid and ask)
                    quote_tick = QuoteTick(
                        instrument_id=instrument_id,
                        bid_price=price,
                        ask_price=price,
                        bid_size=Quantity.from_int(0),
                        ask_size=Quantity.from_int(0),
                        ts_event=ts_event,
                        ts_init=ts_event,
                    )

                    self._handle_data(quote_tick)

                except Exception as e:
                    self._log.warning(f"Failed to parse mid price for {symbol}: {e}")

        except Exception as e:
            self._log.warning(f"Failed to parse all mids: {e}")

    # Subscription methods
    async def _subscribe_instruments(self, command: SubscribeInstruments) -> None:
        pass  # Do nothing (handled automatically)

    async def _subscribe_instrument(self, command: SubscribeInstrument) -> None:
        pass  # Do nothing (handled automatically)

    async def _subscribe_order_book_deltas(self, command: SubscribeOrderBook) -> None:
        if command.book_type == BookType.L3_MBO:
            self._log.error("L3_MBO order book data is not supported by Hyperliquid")
            return

        # Subscribe to L2 book for the symbol
        symbol = command.instrument_id.symbol.value.replace("-PERP", "")
        subscription_id = f"l2Book-{symbol}"
        
        if subscription_id not in self._subscriptions:
            await asyncio.get_event_loop().run_in_executor(
                None, self._ws_client.subscribe_l2_book, symbol
            )
            self._subscriptions.add(subscription_id)

    async def _subscribe_trade_ticks(self, command: SubscribeTradeTicks) -> None:
        # Subscribe to trades for the symbol
        symbol = command.instrument_id.symbol.value.replace("-PERP", "")
        subscription_id = f"trades-{symbol}"
        
        if subscription_id not in self._subscriptions:
            await asyncio.get_event_loop().run_in_executor(
                None, self._ws_client.subscribe_trades, symbol
            )
            self._subscriptions.add(subscription_id)

    async def _subscribe_quote_ticks(self, command: SubscribeQuoteTicks) -> None:
        # Subscribe to all mids (closest thing to quote ticks)
        subscription_id = "allMids"
        
        if subscription_id not in self._subscriptions:
            await asyncio.get_event_loop().run_in_executor(
                None, self._ws_client.subscribe_all_mids
            )
            self._subscriptions.add(subscription_id)

    async def _subscribe_bars(self, command: SubscribeBars) -> None:
        self._log.error("Bar subscriptions are not supported by Hyperliquid WebSocket API")

    # Unsubscription methods
    async def _unsubscribe_instruments(self, command: UnsubscribeInstruments) -> None:
        pass

    async def _unsubscribe_instrument(self, command: UnsubscribeInstrument) -> None:
        pass

    async def _unsubscribe_order_book_deltas(self, command: UnsubscribeOrderBook) -> None:
        # Note: Hyperliquid doesn't support unsubscribing individual symbols
        pass

    async def _unsubscribe_trade_ticks(self, command: UnsubscribeTradeTicks) -> None:
        # Note: Hyperliquid doesn't support unsubscribing individual symbols
        pass

    async def _unsubscribe_quote_ticks(self, command: UnsubscribeQuoteTicks) -> None:
        # Note: Hyperliquid doesn't support unsubscribing individual symbols
        pass

    async def _unsubscribe_bars(self, command: UnsubscribeBars) -> None:
        pass

    # Request methods (not supported by Hyperliquid for historical data)
    async def _request_instrument(self, request: RequestInstrument) -> None:
        instrument = self._instrument_provider.find(request.instrument_id)
        if instrument is None:
            self._log.error(f"Cannot find instrument for {request.instrument_id}")
            return

        self._handle_instrument(instrument, request.id, request.start, request.end, request.params)

    async def _request_instruments(self, request: RequestInstruments) -> None:
        instruments = self._instrument_provider.get_all()
        self._handle_instruments(
            request.venue,
            instruments,
            request.id,
            request.start,
            request.end,
            request.params,
        )

    async def _request_quote_ticks(self, request: RequestQuoteTicks) -> None:
        self._log.error(
            f"Cannot request historical quotes for {request.instrument_id}: "
            "not supported by Hyperliquid"
        )

    async def _request_trade_ticks(self, request: RequestTradeTicks) -> None:
        self._log.error(
            f"Cannot request historical trades for {request.instrument_id}: "
            "not supported by Hyperliquid"
        )

    async def _request_bars(self, request: RequestBars) -> None:
        self._log.error(
            f"Cannot request historical bars for {request.bar_type}: "
            "not supported by Hyperliquid"
        )
