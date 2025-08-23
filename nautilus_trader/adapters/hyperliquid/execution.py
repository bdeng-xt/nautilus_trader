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

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Any

from nautilus_trader.adapters.hyperliquid.config import HyperliquidExecClientConfig
from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID
from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID_VENUE
from nautilus_trader.adapters.hyperliquid.providers import HyperliquidInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.enums import LogColor
from nautilus_trader.common.enums import LogLevel
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.execution.messages import CancelAllOrders
from nautilus_trader.execution.messages import CancelOrder
from nautilus_trader.execution.messages import GenerateFillReports
from nautilus_trader.execution.messages import GenerateOrderStatusReport
from nautilus_trader.execution.messages import GenerateOrderStatusReports
from nautilus_trader.execution.messages import GeneratePositionStatusReports
from nautilus_trader.execution.messages import ModifyOrder
from nautilus_trader.execution.messages import QueryAccount
from nautilus_trader.execution.messages import SubmitOrder
from nautilus_trader.execution.reports import FillReport
from nautilus_trader.execution.reports import OrderStatusReport
from nautilus_trader.execution.reports import PositionStatusReport
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.currencies import Currency
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.enums import OrderType
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.events import AccountState
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.objects import AccountBalance
from nautilus_trader.model.objects import MarginBalance
from nautilus_trader.model.objects import Money
from nautilus_trader.model.orders import LimitOrder
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.model.orders import Order
from nautilus_trader.model.orders import StopMarketOrder


class HyperliquidExecutionClient(LiveExecutionClient):
    """
    Provides an execution client for the Hyperliquid exchange.

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
    config : HyperliquidExecClientConfig
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
        config: HyperliquidExecClientConfig,
        name: str | None,
    ) -> None:
        # Set account ID based on wallet address
        wallet_address = config.wallet_address or "default"
        account_id = AccountId(f"{HYPERLIQUID}-{wallet_address[:8]}")

        super().__init__(
            loop=loop,
            client_id=ClientId(name or HYPERLIQUID),
            venue=HYPERLIQUID_VENUE,
            oms_type=OmsType.NETTING,
            instrument_provider=instrument_provider,
            account_type=AccountType.MARGIN,
            base_currency=Currency.from_str("USD"),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )
        
        # Set the account ID
        self._set_account_id(account_id)
        
        self._instrument_provider: HyperliquidInstrumentProvider = instrument_provider

        # Configuration
        self._config = config
        self._log.info(f"{config.http_timeout_secs=}", LogColor.BLUE)
        self._log.info(f"account_id={self.account_id.value}", LogColor.BLUE)

        # HTTP API
        self._http_client = http_client
        self._log.info("Hyperliquid HTTP client configured", LogColor.BLUE)

        # WebSocket API for execution updates
        self._ws_client = ws_client
        self._ws_task: asyncio.Task | None = None

        # Order tracking
        self._venue_order_ids: dict[ClientOrderId, VenueOrderId] = {}

    @property
    def hyperliquid_instrument_provider(self) -> HyperliquidInstrumentProvider:
        return self._instrument_provider

    async def _connect(self) -> None:
        await self._cache_instruments()
        await self._update_account_state()

        # Connect WebSocket for execution updates
        if self._ws_client:
            self._log.info("Connecting to Hyperliquid execution WebSocket...")
            self._ws_task = asyncio.create_task(self._run_execution_websocket())
            await asyncio.sleep(1.0)  # Give it time to connect
            self._log.info("Connected to Hyperliquid execution WebSocket", LogColor.GREEN)

    async def _disconnect(self) -> None:
        # Cancel WebSocket task
        if self._ws_task:
            self._log.info("Disconnecting execution WebSocket...")
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None

    async def _cache_instruments(self) -> None:
        """Cache instruments for execution."""
        await self._instrument_provider.initialize()
        self._log.debug("Cached instruments", LogColor.MAGENTA)

    async def _update_account_state(self) -> None:
        """Update account state from Hyperliquid API."""
        try:
            # Get account state from HTTP client
            user_state_response = await asyncio.get_event_loop().run_in_executor(
                None, self._http_client.get_user_state
            )
            
            if not user_state_response:
                self._log.warning("No user state received from Hyperliquid")
                return

            # Parse response (assuming JSON string)
            user_state = json.loads(user_state_response)
            
            # Extract balances
            balances = []
            
            # Parse cross margin summary if available
            cross_margin_summary = user_state.get("crossMarginSummary", {})
            if cross_margin_summary:
                total_usd = cross_margin_summary.get("accountValue", "0")
                usd_currency = Currency.from_str("USD")
                
                balance = AccountBalance(
                    total=Money(Decimal(total_usd), usd_currency),
                    locked=Money(Decimal("0"), usd_currency),
                    free=Money(Decimal(total_usd), usd_currency),
                )
                balances.append(balance)

            # Generate account state
            self.generate_account_state(
                balances=balances,
                margins=[],
                reported=True,
                ts_event=self._clock.timestamp_ns(),
            )
            
            self._log.info("Updated account state", LogColor.GREEN)

        except Exception as e:
            self._log.error(f"Failed to update account state: {e}")

    async def _run_execution_websocket(self) -> None:
        """Run WebSocket for execution updates."""
        try:
            # Connect to WebSocket
            await asyncio.get_event_loop().run_in_executor(None, self._ws_client.connect)
            
            # Subscribe to user events
            user_address = self._config.wallet_address or "default"
            await asyncio.get_event_loop().run_in_executor(
                None, self._ws_client.subscribe_user_events, user_address
            )
            
            # Message handling loop
            while True:
                message = await asyncio.get_event_loop().run_in_executor(
                    None, self._ws_client.read_message
                )
                
                if message:
                    await self._handle_execution_message(message)
                else:
                    await asyncio.sleep(0.001)

        except asyncio.CancelledError:
            self._log.info("Execution WebSocket task cancelled")
            await asyncio.get_event_loop().run_in_executor(None, self._ws_client.disconnect)
        except Exception as e:
            self._log.error(f"Execution WebSocket error: {e}")

    async def _handle_execution_message(self, message_json: str) -> None:
        """Handle execution-related WebSocket messages."""
        try:
            message = json.loads(message_json)
            channel = message.get("channel", "")
            
            if channel == "userEvents":
                # Handle user events (order updates, fills, etc.)
                data = message.get("data", [])
                for event in data:
                    await self._handle_user_event(event)

        except Exception as e:
            self._log.error(f"Error handling execution message: {e}")

    async def _handle_user_event(self, event: dict) -> None:
        """Handle individual user events."""
        try:
            # This would need to be implemented based on Hyperliquid's user event format
            # For now, just log the event
            self._log.debug(f"User event: {event}")
            
        except Exception as e:
            self._log.warning(f"Failed to handle user event: {e}")

    # -- COMMAND HANDLERS -------------------------------------------------------------------------

    async def _submit_order(self, command: SubmitOrder) -> None:
        """Submit an order to Hyperliquid."""
        try:
            order = command.order
            
            # Convert order to Hyperliquid format
            symbol = order.instrument_id.symbol.value.replace("-PERP", "")
            side = "B" if order.side == OrderSide.BUY else "S"
            size = str(order.quantity)
            
            if isinstance(order, LimitOrder):
                order_type = "limit"
                price = str(order.price)
            elif isinstance(order, MarketOrder):
                order_type = "market"
                price = None
            else:
                self._log.error(f"Unsupported order type: {type(order)}")
                return

            # Submit order via HTTP client
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self._submit_order_sync,
                symbol,
                side,
                size,
                order_type,
                price,
            )
            
            if response:
                # Handle successful order submission
                self._log.info(f"Order submitted: {order.client_order_id}")
                # In a full implementation, you'd parse the response and generate order events
            else:
                self._log.error(f"Failed to submit order: {order.client_order_id}")

        except Exception as e:
            self._log.error(f"Error submitting order {command.order.client_order_id}: {e}")

    def _submit_order_sync(self, symbol: str, side: str, size: str, order_type: str, price: str | None) -> str:
        """Synchronous wrapper for order submission."""
        # This would call the Rust HTTP client
        # For now, return empty string (would need actual implementation)
        return ""

    async def _cancel_order(self, command: CancelOrder) -> None:
        """Cancel an order."""
        try:
            # Get venue order ID
            venue_order_id = self._venue_order_ids.get(command.client_order_id)
            if not venue_order_id:
                self._log.warning(f"No venue order ID for {command.client_order_id}")
                return

            # Cancel order via HTTP client
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._cancel_order_sync, str(venue_order_id)
            )
            
            if response:
                self._log.info(f"Order cancelled: {command.client_order_id}")
            else:
                self._log.error(f"Failed to cancel order: {command.client_order_id}")

        except Exception as e:
            self._log.error(f"Error cancelling order {command.client_order_id}: {e}")

    def _cancel_order_sync(self, venue_order_id: str) -> str:
        """Synchronous wrapper for order cancellation."""
        # This would call the Rust HTTP client
        return ""

    async def _cancel_all_orders(self, command: CancelAllOrders) -> None:
        """Cancel all orders."""
        try:
            # Get all open orders from cache
            open_orders = self._cache.orders_open(venue=self.venue)
            
            for order in open_orders:
                cancel_command = CancelOrder(
                    trader_id=command.trader_id,
                    strategy_id=command.strategy_id,
                    instrument_id=order.instrument_id,
                    client_order_id=order.client_order_id,
                    venue_order_id=order.venue_order_id,
                    command_id=command.command_id,
                    ts_init=command.ts_init,
                )
                await self._cancel_order(cancel_command)

        except Exception as e:
            self._log.error(f"Error cancelling all orders: {e}")

    async def _modify_order(self, command: ModifyOrder) -> None:
        """Modify an order (not supported by Hyperliquid - would need cancel/replace)."""
        self._log.error("Order modification not directly supported by Hyperliquid")

    # -- REPORT GENERATORS ------------------------------------------------------------------------

    async def generate_order_status_reports(
        self,
        command: GenerateOrderStatusReports,
    ) -> list[OrderStatusReport]:
        """Generate order status reports."""
        reports: list[OrderStatusReport] = []
        
        try:
            # Get open orders from HTTP client
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._http_client.get_open_orders
            )
            
            if response:
                orders_data = json.loads(response)
                # Parse orders and create reports
                # This would need proper implementation based on Hyperliquid's response format
                
        except Exception as e:
            self._log.error(f"Error generating order status reports: {e}")

        return reports

    async def generate_order_status_report(
        self,
        command: GenerateOrderStatusReport,
    ) -> OrderStatusReport | None:
        """Generate a single order status report."""
        # Implementation would query specific order status
        return None

    async def generate_fill_reports(
        self,
        command: GenerateFillReports,
    ) -> list[FillReport]:
        """Generate fill reports."""
        reports: list[FillReport] = []
        
        try:
            # Get fills from HTTP client
            # This would need proper implementation
            pass
            
        except Exception as e:
            self._log.error(f"Error generating fill reports: {e}")

        return reports

    async def generate_position_status_reports(
        self,
        command: GeneratePositionStatusReports,
    ) -> list[PositionStatusReport]:
        """Generate position status reports."""
        reports: list[PositionStatusReport] = []
        
        try:
            # Get positions from HTTP client
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._http_client.get_user_state
            )
            
            if response:
                user_state = json.loads(response)
                # Parse positions and create reports
                # This would need proper implementation
                
        except Exception as e:
            self._log.error(f"Error generating position status reports: {e}")

        return reports

    async def _query_account(self, command: QueryAccount) -> None:
        """Query account information."""
        await self._update_account_state()
