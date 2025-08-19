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
Data client for Hyperliquid decentralized exchange.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import msgspec

from nautilus_trader.adapters.hyperliquid.config import HyperliquidDataClientConfig
from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID_VENUE
from nautilus_trader.adapters.hyperliquid.providers import HyperliquidInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.common.enums import LogColor
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.model.data import Bar, BarSpecification, BarType
from nautilus_trader.model.data import BookOrder, OrderBookDelta, OrderBookDeltas, OrderBookDepth10
from nautilus_trader.model.data import QuoteTick, TradeTick
from nautilus_trader.model.enums import AggregationSource, AggressorSide, BarAggregation, BookAction, BookType, PriceType
from nautilus_trader.model.identifiers import ClientId, InstrumentId, TradeId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Price, Quantity

if TYPE_CHECKING:
    from nautilus_trader.adapters.hyperliquid.http.client import HyperliquidHttpClient
    from nautilus_trader.adapters.hyperliquid.websocket.client import HyperliquidWebSocketClient


class HyperliquidDataClient(LiveMarketDataClient):
    """
    Provides a data client for the Hyperliquid decentralized exchange.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop for the client.
    client : HyperliquidHttpClient
        The Hyperliquid HTTP API client.
    ws_client : HyperliquidWebSocketClient
        The Hyperliquid WebSocket API client.
    msgbus : MessageBus
        The message bus for the client.
    cache : Cache
        The cache for the client.
    clock : LiveClock
        The clock for the client.
    config : HyperliquidDataClientConfig
        The configuration for the client.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: HyperliquidHttpClient,
        ws_client: HyperliquidWebSocketClient,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        config: HyperliquidDataClientConfig,
    ) -> None:
        # Configuration
        self._config = config
        self._log_warnings = True
        
        # Clients
        self._client = client
        self._ws_client = ws_client
        
        # Instrument provider
        provider = HyperliquidInstrumentProvider(
            client=client,
            config=config,
        )

        super().__init__(
            loop=loop,
            client_id=ClientId(HYPERLIQUID_VENUE.value),
            venue=HYPERLIQUID_VENUE,
            instrument_provider=provider,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )

        # Subscriptions
        self._subscribed_instruments: set[InstrumentId] = set()
        self._subscribed_quote_ticks: set[InstrumentId] = set()
        self._subscribed_trade_ticks: set[InstrumentId] = set()
        self._subscribed_bars: set[BarType] = set()
        self._subscribed_order_book_deltas: set[InstrumentId] = set()
        self._subscribed_order_book_snapshots: set[InstrumentId] = set()

        # Tasks
        self._task_connect: asyncio.Task | None = None
        self._task_disconnect: asyncio.Task | None = None
        self._task_ws_handler: asyncio.Task | None = None

    @property
    def subscribed_instruments(self) -> list[InstrumentId]:
        """
        Return the subscribed instruments for the client.

        Returns
        -------
        list[InstrumentId]

        """
        return sorted(list(self._subscribed_instruments))

    @property
    def subscribed_quote_ticks(self) -> list[InstrumentId]:
        """
        Return the subscribed quote tick instruments for the client.

        Returns
        -------
        list[InstrumentId]

        """
        return sorted(list(self._subscribed_quote_ticks))

    @property
    def subscribed_trade_ticks(self) -> list[InstrumentId]:
        """
        Return the subscribed trade tick instruments for the client.

        Returns
        -------
        list[InstrumentId]

        """
        return sorted(list(self._subscribed_trade_ticks))

    @property
    def subscribed_bars(self) -> list[BarType]:
        """
        Return the subscribed bar types for the client.

        Returns
        -------
        list[BarType]

        """
        return sorted(list(self._subscribed_bars))

    @property
    def subscribed_order_book_deltas(self) -> list[InstrumentId]:
        """
        Return the subscribed order book delta instruments for the client.

        Returns
        -------
        list[InstrumentId]

        """
        return sorted(list(self._subscribed_order_book_deltas))

    @property
    def subscribed_order_book_snapshots(self) -> list[InstrumentId]:
        """
        Return the subscribed order book snapshot instruments for the client.

        Returns
        -------
        list[InstrumentId]

        """
        return sorted(list(self._subscribed_order_book_snapshots))

    # -- CONNECTION HANDLERS -------------------------------------------------------------------------

    async def _connect(self) -> None:
        """Connect the client."""
        self._log.info("Connecting...")

        # Initialize WebSocket client
        if self._config.ws_base_url:
            await self._ws_client.connect()
            
            # Start WebSocket message handler
            self._task_ws_handler = self._loop.create_task(self._handle_ws_messages())
            
            self._log.info("WebSocket connected", LogColor.GREEN)

        self._log.info("Connected", LogColor.GREEN)

    async def _disconnect(self) -> None:
        """Disconnect the client."""
        self._log.info("Disconnecting...")

        # Cancel WebSocket message handler
        if self._task_ws_handler and not self._task_ws_handler.done():
            self._task_ws_handler.cancel()
            try:
                await self._task_ws_handler
            except asyncio.CancelledError:
                pass

        # Close WebSocket connection
        await self._ws_client.disconnect()

        self._log.info("Disconnected", LogColor.GREEN)

    # -- SUBSCRIPTIONS -------------------------------------------------------------------------------

    async def _subscribe_instruments(self) -> None:
        """Subscribe to all instruments."""
        await self._instrument_provider.load_all_async()

    async def _subscribe_instrument(self, instrument_id: InstrumentId) -> None:
        """Subscribe to the given instrument."""
        self._subscribed_instruments.add(instrument_id)

    async def _unsubscribe_instrument(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from the given instrument."""
        self._subscribed_instruments.discard(instrument_id)

    async def _subscribe_order_book_deltas(
        self,
        instrument_id: InstrumentId,
        book_type: BookType,
        depth: int | None = None,
    ) -> None:
        """Subscribe to order book deltas for the given instrument."""
        if instrument_id in self._subscribed_order_book_deltas:
            self._log.warning(f"Already subscribed to order book deltas for {instrument_id}")
            return

        symbol = self._get_hyperliquid_symbol(instrument_id)
        await self._ws_client.subscribe_l2_book(symbol)
        
        self._subscribed_order_book_deltas.add(instrument_id)
        self._log.info(f"Subscribed to {instrument_id} order book deltas")

    async def _subscribe_order_book_snapshots(
        self,
        instrument_id: InstrumentId,
        book_type: BookType,
        depth: int | None = None,
        interval_ms: int | None = None,
    ) -> None:
        """Subscribe to order book snapshots for the given instrument."""
        if instrument_id in self._subscribed_order_book_snapshots:
            self._log.warning(f"Already subscribed to order book snapshots for {instrument_id}")
            return

        symbol = self._get_hyperliquid_symbol(instrument_id)
        await self._ws_client.subscribe_l2_book(symbol)
        
        self._subscribed_order_book_snapshots.add(instrument_id)
        self._log.info(f"Subscribed to {instrument_id} order book snapshots")

    async def _subscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        """Subscribe to quote ticks for the given instrument."""
        if instrument_id in self._subscribed_quote_ticks:
            self._log.warning(f"Already subscribed to quote ticks for {instrument_id}")
            return

        # Hyperliquid doesn't have dedicated quote tick feeds
        # We'll use L2 book data to derive quote ticks
        symbol = self._get_hyperliquid_symbol(instrument_id)
        await self._ws_client.subscribe_l2_book(symbol)
        
        self._subscribed_quote_ticks.add(instrument_id)
        self._log.info(f"Subscribed to {instrument_id} quote ticks")

    async def _subscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        """Subscribe to trade ticks for the given instrument."""
        if instrument_id in self._subscribed_trade_ticks:
            self._log.warning(f"Already subscribed to trade ticks for {instrument_id}")
            return

        symbol = self._get_hyperliquid_symbol(instrument_id)
        await self._ws_client.subscribe_trades(symbol)
        
        self._subscribed_trade_ticks.add(instrument_id)
        self._log.info(f"Subscribed to {instrument_id} trade ticks")

    async def _subscribe_bars(self, bar_type: BarType) -> None:
        """Subscribe to bars for the given bar type."""
        if bar_type in self._subscribed_bars:
            self._log.warning(f"Already subscribed to bars for {bar_type}")
            return

        # Hyperliquid doesn't provide live bar feeds
        # Bars would need to be constructed from trade ticks
        self._log.warning(f"Live bar subscriptions not supported for {bar_type}")

    async def _unsubscribe_order_book_deltas(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from order book deltas for the given instrument."""
        if instrument_id not in self._subscribed_order_book_deltas:
            self._log.warning(f"Not subscribed to order book deltas for {instrument_id}")
            return

        symbol = self._get_hyperliquid_symbol(instrument_id)
        await self._ws_client.unsubscribe("l2Book", symbol)
        
        self._subscribed_order_book_deltas.discard(instrument_id)
        self._log.info(f"Unsubscribed from {instrument_id} order book deltas")

    async def _unsubscribe_order_book_snapshots(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from order book snapshots for the given instrument."""
        if instrument_id not in self._subscribed_order_book_snapshots:
            self._log.warning(f"Not subscribed to order book snapshots for {instrument_id}")
            return

        symbol = self._get_hyperliquid_symbol(instrument_id)
        await self._ws_client.unsubscribe("l2Book", symbol)
        
        self._subscribed_order_book_snapshots.discard(instrument_id)
        self._log.info(f"Unsubscribed from {instrument_id} order book snapshots")

    async def _unsubscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from quote ticks for the given instrument."""
        if instrument_id not in self._subscribed_quote_ticks:
            self._log.warning(f"Not subscribed to quote ticks for {instrument_id}")
            return

        symbol = self._get_hyperliquid_symbol(instrument_id)
        await self._ws_client.unsubscribe("l2Book", symbol)
        
        self._subscribed_quote_ticks.discard(instrument_id)
        self._log.info(f"Unsubscribed from {instrument_id} quote ticks")

    async def _unsubscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from trade ticks for the given instrument."""
        if instrument_id not in self._subscribed_trade_ticks:
            self._log.warning(f"Not subscribed to trade ticks for {instrument_id}")
            return

        symbol = self._get_hyperliquid_symbol(instrument_id)
        await self._ws_client.unsubscribe("trades", symbol)
        
        self._subscribed_trade_ticks.discard(instrument_id)
        self._log.info(f"Unsubscribed from {instrument_id} trade ticks")

    async def _unsubscribe_bars(self, bar_type: BarType) -> None:
        """Unsubscribe from bars for the given bar type."""
        if bar_type not in self._subscribed_bars:
            self._log.warning(f"Not subscribed to bars for {bar_type}")
            return

        self._subscribed_bars.discard(bar_type)
        self._log.info(f"Unsubscribed from {bar_type} bars")

    # -- REQUEST HANDLERS ----------------------------------------------------------------------------

    async def _request_instrument(self, instrument_id: InstrumentId, correlation_id: UUID4) -> None:
        """Request the instrument for the given instrument ID."""
        await self._instrument_provider.load_async(instrument_id, correlation_id)

    async def _request_instruments(self, venue: str, correlation_id: UUID4) -> None:
        """Request all instruments for the given venue."""
        await self._instrument_provider.load_all_async(correlation_id)

    async def _request_quote_ticks(
        self,
        instrument_id: InstrumentId,
        limit: int,
        correlation_id: UUID4,
        start: int | None = None,
        end: int | None = None,
    ) -> None:
        """Request historical quote ticks for the given instrument."""
        self._log.warning(f"Quote tick history not available for {instrument_id}")

    async def _request_trade_ticks(
        self,
        instrument_id: InstrumentId,
        limit: int,
        correlation_id: UUID4,
        start: int | None = None,
        end: int | None = None,
    ) -> None:
        """Request historical trade ticks for the given instrument."""
        try:
            symbol = self._get_hyperliquid_symbol(instrument_id)
            trades = await self._client.get_recent_trades(symbol)
            
            trade_ticks = []
            for trade in trades:
                trade_tick = TradeTick(
                    instrument_id=instrument_id,
                    price=Price.from_str(trade["px"]),
                    size=Quantity.from_str(trade["sz"]),
                    aggressor_side=AggressorSide.BUY if trade["side"] == "B" else AggressorSide.SELL,
                    trade_id=TradeId(trade["hash"]),
                    ts_event=trade["time"] * 1_000_000,  # Convert to nanoseconds
                    ts_init=self._clock.timestamp_ns(),
                )
                trade_ticks.append(trade_tick)
            
            self._handle_data(trade_ticks, correlation_id)
            
        except Exception as e:
            self._log.error(f"Failed to request trade ticks for {instrument_id}: {e}")

    async def _request_bars(
        self,
        bar_type: BarType,
        limit: int,
        correlation_id: UUID4,
        start: int | None = None,
        end: int | None = None,
    ) -> None:
        """Request historical bars for the given bar type."""
        try:
            symbol = self._get_hyperliquid_symbol(bar_type.instrument_id)
            interval = self._get_hyperliquid_interval(bar_type.spec)
            
            candles = await self._client.get_candles(
                symbol, 
                interval,
                start_time=start,
                end_time=end,
            )
            
            bars = []
            for candle in candles:
                bar = Bar(
                    bar_type=bar_type,
                    open=Price.from_str(candle["o"]),
                    high=Price.from_str(candle["h"]),
                    low=Price.from_str(candle["l"]),
                    close=Price.from_str(candle["c"]),
                    volume=Quantity.from_str(candle["v"]),
                    ts_event=candle["t"] * 1_000_000,  # Convert to nanoseconds
                    ts_init=self._clock.timestamp_ns(),
                )
                bars.append(bar)
            
            self._handle_data(bars, correlation_id)
            
        except Exception as e:
            self._log.error(f"Failed to request bars for {bar_type}: {e}")

    # -- HELPERS --------------------------------------------------------------------------------------

    def _get_hyperliquid_symbol(self, instrument_id: InstrumentId) -> str:
        """Get the Hyperliquid symbol from an instrument ID."""
        return instrument_id.symbol.value.replace(".HYPERLIQUID", "")

    def _get_hyperliquid_interval(self, spec: BarSpecification) -> str:
        """Get the Hyperliquid interval string from a bar specification."""
        if spec.aggregation == BarAggregation.MINUTE:
            return f"{spec.step}m"
        elif spec.aggregation == BarAggregation.HOUR:
            return f"{spec.step}h"
        elif spec.aggregation == BarAggregation.DAY:
            return f"{spec.step}d"
        else:
            raise ValueError(f"Unsupported bar aggregation: {spec.aggregation}")

    def _handle_data(self, data: Any, correlation_id: UUID4) -> None:
        """Handle incoming data."""
        if isinstance(data, list):
            for item in data:
                self._handle_data_response(item, correlation_id)
        else:
            self._handle_data_response(data, correlation_id)

    # -- WEBSOCKET MESSAGE HANDLING ------------------------------------------------------------------

    async def _handle_ws_messages(self) -> None:
        """Handle incoming WebSocket messages."""
        try:
            message_receiver = self._ws_client.get_message_receiver()
            if not message_receiver:
                self._log.warning("No WebSocket message receiver available")
                return

            while True:
                try:
                    # This is a simplified implementation
                    # The actual implementation would depend on the WebSocket client structure
                    await asyncio.sleep(1)  # Placeholder
                    
                except Exception as e:
                    self._log.error(f"Error processing WebSocket message: {e}")
                    await asyncio.sleep(0.1)  # Brief pause before retrying
                    
        except asyncio.CancelledError:
            self._log.debug("WebSocket message handler cancelled")
        except Exception as e:
            self._log.error(f"WebSocket message handler error: {e}")

    def _handle_trade_message(self, message: dict[str, Any]) -> None:
        """
        Handle a trade message from WebSocket.

        Parameters
        ----------
        message : dict[str, Any]
            The trade message.

        """
        try:
            # Parse trade data
            coin = message.get('coin', '')
            if not coin:
                return

            # Create instrument ID
            instrument_id = InstrumentId.from_str(f"{coin}-USD.{HYPERLIQUID_VENUE.value}")

            # Check if we're subscribed to this instrument
            if instrument_id not in self._subscribed_trade_ticks:
                return

            # Create trade tick
            trade_tick = TradeTick(
                instrument_id=instrument_id,
                price=Price.from_str(str(message.get('px', '0'))),
                size=Quantity.from_str(str(message.get('sz', '0'))),
                aggressor_side=AggressorSide.BUY if message.get('side') == 'B' else AggressorSide.SELL,
                trade_id=TradeId(str(message.get('hash', ''))),
                ts_event=message.get('time', 0) * 1_000_000,  # Convert to nanoseconds
                ts_init=self._clock.timestamp_ns(),
            )

            self._handle_data_response(trade_tick)

        except Exception as e:
            self._log.error(f"Failed to handle trade message: {e}")

    def _handle_book_message(self, message: dict[str, Any]) -> None:
        """
        Handle an order book message from WebSocket.

        Parameters
        ----------
        message : dict[str, Any]
            The order book message.

        """
        try:
            # Parse order book data
            coin = message.get('coin', '')
            if not coin:
                return

            # Create instrument ID
            instrument_id = InstrumentId.from_str(f"{coin}-USD.{HYPERLIQUID_VENUE.value}")

            # Check if we're subscribed to this instrument
            if instrument_id not in self._subscribed_order_book_deltas and \
               instrument_id not in self._subscribed_quote_ticks:
                return

            # Parse order book levels
            levels = message.get('levels', [[]])
            if len(levels) < 2:
                return

            bids = levels[0] if levels[0] else []
            asks = levels[1] if levels[1] else []

            # Generate quote tick from best bid/ask if subscribed
            if instrument_id in self._subscribed_quote_ticks and bids and asks:
                best_bid = bids[0] if bids else None
                best_ask = asks[0] if asks else None

                if best_bid and best_ask:
                    quote_tick = QuoteTick(
                        instrument_id=instrument_id,
                        bid_price=Price.from_str(str(best_bid.get('px', '0'))),
                        ask_price=Price.from_str(str(best_ask.get('px', '0'))),
                        bid_size=Quantity.from_str(str(best_bid.get('sz', '0'))),
                        ask_size=Quantity.from_str(str(best_ask.get('sz', '0'))),
                        ts_event=message.get('time', 0) * 1_000_000,
                        ts_init=self._clock.timestamp_ns(),
                    )

                    self._handle_data_response(quote_tick)

            # Generate order book deltas if subscribed
            if instrument_id in self._subscribed_order_book_deltas:
                deltas = []
                
                # Process bid deltas
                for level in bids:
                    delta = OrderBookDelta(
                        instrument_id=instrument_id,
                        action=BookAction.UPDATE if float(level.get('sz', '0')) > 0 else BookAction.DELETE,
                        order=BookOrder(
                            side=OrderSide.BUY,
                            price=Price.from_str(str(level.get('px', '0'))),
                            size=Quantity.from_str(str(level.get('sz', '0'))),
                            order_id=0,  # Hyperliquid doesn't provide order IDs for L2 data
                        ),
                        flags=0,
                        sequence=0,
                        ts_event=message.get('time', 0) * 1_000_000,
                        ts_init=self._clock.timestamp_ns(),
                    )
                    deltas.append(delta)

                # Process ask deltas
                for level in asks:
                    delta = OrderBookDelta(
                        instrument_id=instrument_id,
                        action=BookAction.UPDATE if float(level.get('sz', '0')) > 0 else BookAction.DELETE,
                        order=BookOrder(
                            side=OrderSide.SELL,
                            price=Price.from_str(str(level.get('px', '0'))),
                            size=Quantity.from_str(str(level.get('sz', '0'))),
                            order_id=0,
                        ),
                        flags=0,
                        sequence=0,
                        ts_event=message.get('time', 0) * 1_000_000,
                        ts_init=self._clock.timestamp_ns(),
                    )
                    deltas.append(delta)

                if deltas:
                    order_book_deltas = OrderBookDeltas(
                        instrument_id=instrument_id,
                        deltas=deltas,
                    )
                    self._handle_data_response(order_book_deltas)

        except Exception as e:
            self._log.error(f"Failed to handle book message: {e}")

    def _handle_all_mids_message(self, message: dict[str, Any]) -> None:
        """
        Handle an all mids message from WebSocket.

        Parameters
        ----------
        message : dict[str, Any]
            The all mids message.

        """
        try:
            mids = message.get('mids', {})
            
            for coin, mid_price in mids.items():
                instrument_id = InstrumentId.from_str(f"{coin}-USD.{HYPERLIQUID_VENUE.value}")
                
                # Create a quote tick with mid price as both bid and ask
                # This is a simplified representation
                if instrument_id in self._subscribed_quote_ticks:
                    mid = Price.from_str(str(mid_price))
                    
                    quote_tick = QuoteTick(
                        instrument_id=instrument_id,
                        bid_price=mid,
                        ask_price=mid,
                        bid_size=Quantity.from_str('0'),  # Size not available in all mids
                        ask_size=Quantity.from_str('0'),
                        ts_event=self._clock.timestamp_ns(),
                        ts_init=self._clock.timestamp_ns(),
                    )

                    self._handle_data_response(quote_tick)

        except Exception as e:
            self._log.error(f"Failed to handle all mids message: {e}")
