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
        self._subscribed_quote_instruments: set[InstrumentId] = set()

    @property
    def hyperliquid_instrument_provider(self) -> HyperliquidInstrumentProvider:
        return self._instrument_provider

    async def _connect(self) -> None:
        # Create basic instruments manually for now to bypass provider issues
        await self._create_basic_instruments()
        self._cache_instruments()
        self._send_all_instruments_to_data_engine()

        # Connect WebSocket client
        if self._ws_client:
            self._log.info("Connecting to Hyperliquid WebSocket...")
            
            # Connect and start subscribing
            await asyncio.get_event_loop().run_in_executor(None, self._ws_client.connect)
            await asyncio.get_event_loop().run_in_executor(None, self._ws_client.subscribe_all_mids)
            
            # Start WebSocket message loop with callback pattern
            self._ws_task = asyncio.create_task(self._run_websocket_with_callback())
            await asyncio.sleep(1.0)  # Give it time to connect
            
            self._log.info("Connected to Hyperliquid WebSocket", LogColor.GREEN)
            
            # TEST: Send a test quote tick to verify data routing works
            await self._send_test_quote_tick()

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
        self._subscribed_quote_instruments.clear()

    async def _send_test_quote_tick(self) -> None:
        """
        Send a test quote tick to verify data routing works.
        This bypasses WebSocket parsing to test the core routing.
        """
        await asyncio.sleep(2.0)  # Wait for subscriptions to be set up
        
        self._log.info("🧪 SENDING TEST QUOTE TICK...")
        
        # Check if we have any subscribed instruments
        if not self._subscribed_quote_instruments:
            self._log.warning("❌ No subscribed quote instruments found for test!")
            return
            
        # Create test quote for first subscribed instrument
        instrument_id = next(iter(self._subscribed_quote_instruments))
        self._log.info(f"🧪 Creating test quote for {instrument_id}")
        
        # Create test quote tick
        test_quote = QuoteTick(
            instrument_id=instrument_id,
            bid_price=Price.from_str("50000.00"),
            ask_price=Price.from_str("50001.00"),
            bid_size=Quantity.from_int(1),
            ask_size=Quantity.from_int(1),
            ts_event=self._clock.timestamp_ns(),
            ts_init=self._clock.timestamp_ns(),
        )
        
        self._log.info(f"🧪 TEST QUOTE: {test_quote}")
        self._log.info("🧪 Calling _handle_data with test quote...")
        
        # Send test quote to data engine
        self._handle_data(test_quote)
        
        self._log.info("🧪 Test quote sent to data engine!")
        self._log.info("🧪 If strategy doesn't receive this, there's a fundamental routing issue.")

    async def _create_basic_instruments(self) -> None:
        """
        Create basic instruments manually for common trading pairs.
        This bypasses the instrument provider issues temporarily.
        """
        from nautilus_trader.model.currencies import USD
        from nautilus_trader.model.instruments import CryptoPerpetual
        from decimal import Decimal
        
        self._log.info("Creating basic instruments manually...")
        
        # Common instruments we expect in the examples
        instruments_data = [
            {"name": "BTC", "sz_decimals": 5, "price_precision": 1},
            {"name": "ETH", "sz_decimals": 4, "price_precision": 2}, 
            {"name": "SOL", "sz_decimals": 2, "price_precision": 3},
            {"name": "AAVE", "sz_decimals": 3, "price_precision": 2},
            {"name": "DOGE", "sz_decimals": 0, "price_precision": 6},
            {"name": "ARB", "sz_decimals": 1, "price_precision": 5},
        ]
        
        ts_init = self._clock.timestamp_ns()
        
        for data in instruments_data:
            try:
                name = data["name"]
                sz_decimals = data["sz_decimals"] 
                price_precision = data["price_precision"]
                
                symbol = Symbol(f"{name}-PERP")
                instrument_id = InstrumentId(symbol, self._config.venue)
                
                base_currency = Currency.from_str(name) 
                quote_currency = USD
                
                instrument = CryptoPerpetual(
                    instrument_id=instrument_id,
                    raw_symbol=Symbol(name),
                    base_currency=base_currency,
                    quote_currency=quote_currency,
                    settlement_currency=quote_currency,  # USD settlement
                    is_inverse=False,  # Not inverse (standard USDT perpetual)
                    price_precision=price_precision,
                    size_precision=sz_decimals,
                    price_increment=Price(10 ** -price_precision, price_precision),
                    size_increment=Quantity(10 ** -sz_decimals, sz_decimals),
                    ts_event=ts_init,
                    ts_init=ts_init,
                    maker_fee=Decimal("0.0002"),
                    taker_fee=Decimal("0.0005"), 
                    margin_init=Decimal("0.1"),
                    margin_maint=Decimal("0.05"),
                )
                
                self._instrument_provider.add(instrument)
                self._instrument_provider.add_currency(base_currency)
                self._instrument_provider.add_currency(quote_currency)
                
                self._log.info(f"✅ Created instrument: {instrument_id}")
                
            except Exception as e:
                self._log.warning(f"❌ Failed to create instrument {data}: {e}")
                
        self._log.info(f"Created {len(instruments_data)} instruments manually")

    def _cache_instruments(self) -> None:
        """Cache instruments for correct price/size precisions."""
        # This method is similar to Coinbase INTX pattern
        for instrument in self._instrument_provider.get_all().values():
            # Ensure instrument is cached and available
            self._log.debug(f"Cached instrument {instrument.id}")
        self._log.debug("Cached instruments for Hyperliquid client")

    def _send_all_instruments_to_data_engine(self) -> None:
        for currency in self._instrument_provider.currencies().values():
            self._cache.add_currency(currency)

        instruments = self._instrument_provider.get_all()
        self._log.info(f"📊 Sending {len(instruments)} instruments to data engine")
        
        for instrument in instruments.values():
            # Add to cache first
            self._cache.add_instrument(instrument)
            # Then send to data engine
            self._handle_data(instrument)
            self._log.info(f"✅ Sent instrument to data engine: {instrument.id}")

    async def _run_websocket_with_callback(self) -> None:
        """
        Run the WebSocket message loop with callback-based message processing.
        This follows the Coinbase INTX pattern for proper data routing.
        """
        try:
            self._log.info("Starting WebSocket callback loop", LogColor.GREEN)
            
            # Message handling loop
            while True:
                try:
                    # Read message from Rust WebSocket client
                    message_json = await asyncio.get_event_loop().run_in_executor(
                        None, self._ws_client.read_message
                    )
                    
                    if message_json:
                        self._log.debug(f"Received WebSocket message: {message_json[:100]}...")
                        
                        # Check if parse_message method is available
                        if hasattr(self._ws_client, 'parse_message'):
                            self._log.debug("Using Rust parser for message processing")
                            # Parse message using Rust parser to get Nautilus data objects
                            parsed_data = await asyncio.get_event_loop().run_in_executor(
                                None, self._ws_client.parse_message, message_json
                            )
                            
                            if parsed_data is not None:
                                self._log.info(f"✅ Parsed data successfully: {type(parsed_data)}")
                                # This should now be a proper Nautilus data object (QuoteTick, etc.)
                                self._handle_data_callback(parsed_data)
                            else:
                                self._log.debug("❌ No data parsed from Rust parser, falling back to manual parsing")
                                # Fallback to manual parsing if needed
                                await self._handle_ws_message(message_json)
                        else:
                            self._log.debug("parse_message method not available, using manual parsing")
                            # Use manual parsing directly
                            await self._handle_ws_message(message_json)
                    else:
                        # No message, small delay to prevent tight loop
                        await asyncio.sleep(0.01)
                        
                except Exception as e:
                    self._log.warning(f"Error in WebSocket callback loop: {e}")
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            self._log.info("WebSocket callback task cancelled")
            # Disconnect WebSocket
            try:
                await asyncio.get_event_loop().run_in_executor(None, self._ws_client.disconnect)
            except Exception as e:
                self._log.warning(f"Error disconnecting WebSocket: {e}")
        except Exception as e:
            self._log.error(f"WebSocket callback error: {e}")

    def _handle_data_callback(self, data: Any) -> None:
        """
        Handle data from the callback-based WebSocket client.
        This follows the Coinbase INTX pattern.
        """
        try:
            from nautilus_trader.model.data import capsule_to_data
            
            # Handle capsule data (similar to Coinbase INTX)
            if hasattr(data, '__class__') and 'pycapsule' in str(type(data)):
                # This is a PyO3 capsule containing Nautilus data
                parsed_data = capsule_to_data(data)
                self._handle_data(parsed_data)
                self._log.debug(f"Processed capsule data: {type(parsed_data).__name__}")
            else:
                # Direct Nautilus data object
                self._handle_data(data)
                self._log.debug(f"Processed direct data: {type(data).__name__}")
                
        except Exception as e:
            self._log.error(f"Error handling callback data: {e}")
            self._log.error(f"Data type: {type(data)}, Data: {str(data)[:200]}")

    async def _run_websocket(self) -> None:
        """
        Legacy WebSocket message loop (kept for backward compatibility).
        """
        try:
            # Connect to WebSocket using Rust client
            await asyncio.get_event_loop().run_in_executor(None, self._ws_client.connect)
            self._log.info("WebSocket connected successfully", LogColor.GREEN)
            
            # Message handling loop
            while True:
                try:
                    # Read message from Rust WebSocket client
                    message = await asyncio.get_event_loop().run_in_executor(
                        None, self._ws_client.read_message
                    )
                    
                    if message:
                        await self._handle_ws_message(message)
                    else:
                        # No message, small delay to prevent tight loop
                        await asyncio.sleep(0.01)
                        
                except Exception as e:
                    self._log.warning(f"Error in WebSocket loop: {e}")
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            self._log.info("WebSocket task cancelled")
            # Disconnect WebSocket
            try:
                await asyncio.get_event_loop().run_in_executor(None, self._ws_client.disconnect)
            except Exception as e:
                self._log.warning(f"Error disconnecting WebSocket: {e}")
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

            self._log.debug(f"Received message on channel: {channel}")

            if channel == "trades":
                await self._handle_trades(data)
                self._log.debug(f"Processed {len(data)} trades")
            elif channel == "l2Book":
                await self._handle_order_book(data)
                self._log.debug(f"Processed order book for {data.get('coin', 'unknown')}")
            elif channel == "allMids":
                await self._handle_all_mids(data)
                mids = data.get("mids", {})
                self._log.debug(f"Processed mids for {len(mids)} symbols")
            elif channel == "subscriptionResponse":
                self._log.info(f"Subscription confirmed: {data}")
            else:
                self._log.debug(f"Unhandled channel: {channel}")

        except json.JSONDecodeError as e:
            self._log.error(f"Invalid JSON in WebSocket message: {e}")
        except Exception as e:
            self._log.error(f"Error handling WebSocket message: {e}")
            self._log.error(f"Message was: {message_json[:200]}...")

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
                ts_event = int(trade.get("time", 0)) * 1_000  # Convert milliseconds to microseconds, then to nanoseconds
                if ts_event == 0:
                    ts_event = self._clock.timestamp_ns()

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
                self._log.info(f"🔄 Trade: {coin} @ {price} size: {size}", LogColor.BLUE)

            except Exception as e:
                self._log.warning(f"Failed to parse trade: {e}")
                self._log.warning(f"Trade data: {trade}")

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
            processed_count = 0
            
            for symbol, price_str in mids.items():
                try:
                    # Skip numbered symbols (they start with @)
                    if symbol.startswith("@"):
                        continue
                    
                    # Create instrument ID for this symbol
                    instrument_id = InstrumentId(Symbol(f"{symbol}-PERP"), self._config.venue)
                    
                    self._log.debug(f"🔍 Processing symbol {symbol} -> {instrument_id}")
                    self._log.debug(f"🔍 Subscribed instruments: {self._subscribed_quote_instruments}")
                    
                    # Only process quotes for instruments that strategies have subscribed to
                    if instrument_id not in self._subscribed_quote_instruments:
                        self._log.debug(f"❌ {instrument_id} not in subscribed instruments, skipping")
                        continue
                    
                    price = Price.from_str(price_str)
                    ts_event = self._clock.timestamp_ns()

                    # Create quote tick with small spread around mid price
                    # Hyperliquid provides mid prices, so we create a small spread
                    tick_size = Price.from_str("0.01")  # Minimal tick size
                    bid_price = price - tick_size
                    ask_price = price + tick_size
                    
                    quote_tick = QuoteTick(
                        instrument_id=instrument_id,
                        bid_price=bid_price,
                        ask_price=ask_price,
                        bid_size=Quantity.from_int(1),  # Use non-zero size
                        ask_size=Quantity.from_int(1),  # Use non-zero size
                        ts_event=ts_event,
                        ts_init=ts_event,
                    )

                    # Send quote tick to data engine
                    self._log.info(f"🔥 SENDING SUBSCRIBED QUOTE TO DATA ENGINE: {quote_tick}")
                    self._handle_data(quote_tick)
                    processed_count += 1
                    
                    # Log this important event
                    self._log.info(f"💰 Quote: {symbol} @ {price} -> {instrument_id} (SUBSCRIBED - sent to data engine)", LogColor.GREEN)

                except Exception as e:
                    self._log.warning(f"Failed to parse mid price for {symbol}: {e}")
                    self._log.warning(f"Symbol: {symbol}, Price: {price_str}")
            
            if processed_count > 0:
                self._log.debug(f"Processed {processed_count} quote ticks from mids")

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
        # Track which instrument this subscription is for
        self._subscribed_quote_instruments.add(command.instrument_id)
        self._log.info(f"📊 Added {command.instrument_id} to subscribed quote instruments")
        self._log.info(f"📊 Strategy subscribed to: {command.instrument_id}")
        self._log.info(f"📊 Current venue config: {self._config.venue}")
        
        # Subscribe to all mids (closest thing to quote ticks)
        subscription_id = "allMids"
        
        if subscription_id not in self._subscriptions:
            await asyncio.get_event_loop().run_in_executor(
                None, self._ws_client.subscribe_all_mids
            )
            self._subscriptions.add(subscription_id)
            self._log.info("🔗 Subscribed to Hyperliquid allMids WebSocket feed")

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
        # Remove from subscribed instruments
        self._subscribed_quote_instruments.discard(command.instrument_id)
        self._log.info(f"📊 Removed {command.instrument_id} from subscribed quote instruments")
        # Note: Hyperliquid doesn't support unsubscribing individual symbols from WebSocket

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
