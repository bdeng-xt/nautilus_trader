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
Execution client for Hyperliquid decentralized exchange.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from nautilus_trader.adapters.hyperliquid.config import HyperliquidExecClientConfig
from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID_VENUE
from nautilus_trader.adapters.hyperliquid.providers import HyperliquidInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.common.enums import LogColor
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.reports import OrderStatusReport, PositionStatusReport, FillReport
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide, OrderStatus, OrderType, PositionSide, TimeInForce
from nautilus_trader.model.identifiers import AccountId, ClientId, ClientOrderId, InstrumentId, VenueOrderId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import AccountBalance, MarginBalance, Money, Price, Quantity
from nautilus_trader.model.orders import Order
from nautilus_trader.model.position import Position

if TYPE_CHECKING:
    from nautilus_trader.model.orders import LimitOrder, MarketOrder, StopLimitOrder, StopMarketOrder


class HyperliquidExecutionClient(LiveExecutionClient):
    """
    Provides an execution client for the Hyperliquid decentralized exchange.

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
    config : HyperliquidExecClientConfig
        The configuration for the client.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: Any,  # HyperliquidHttpClient
        ws_client: Any,  # HyperliquidWebSocketClient
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        config: HyperliquidExecClientConfig,
    ) -> None:
        # Configuration
        self._config = config
        
        # Clients
        self._client = client
        self._ws_client = ws_client
        
        # Account details
        account_id = AccountId(f"{HYPERLIQUID_VENUE.value}-001")
        
        # Instrument provider
        provider = HyperliquidInstrumentProvider(
            client=client,
            config=config,
        )

        super().__init__(
            loop=loop,
            client_id=ClientId(HYPERLIQUID_VENUE.value),
            venue=HYPERLIQUID_VENUE,
            oms_type=OmsType.NETTING,  # Hyperliquid uses netting
            instrument_provider=provider,
            account_type=AccountType.MARGIN,  # Hyperliquid is a margin exchange
            base_currency=None,  # Multi-currency
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )

        # Order tracking
        self._orders: dict[ClientOrderId, Order] = {}
        self._order_id_map: dict[VenueOrderId, ClientOrderId] = {}

        # Account state
        self._account_id = account_id

    @property
    def account_id(self) -> AccountId:
        """
        Return the account ID for the client.

        Returns
        -------
        AccountId

        """
        return self._account_id

    # -- CONNECTION HANDLERS -------------------------------------------------------------------------

    async def _connect(self) -> None:
        """Connect the client."""
        self._log.info("Connecting...")

        # Initialize WebSocket client for execution updates
        if self._config.ws_base_url:
            await self._ws_client.connect()
            
            # Subscribe to user events for order updates
            if hasattr(self._ws_client, 'subscribe_user_events'):
                await self._ws_client.subscribe_user_events(self._config.api_key)
            
            self._log.info("WebSocket connected", LogColor.GREEN)

        self._log.info("Connected", LogColor.GREEN)

    async def _disconnect(self) -> None:
        """Disconnect the client."""
        self._log.info("Disconnecting...")

        # Close WebSocket connection
        await self._ws_client.disconnect()

        self._log.info("Disconnected", LogColor.GREEN)

    # -- ACCOUNT HANDLERS ----------------------------------------------------------------------------

    async def generate_order_status_report(
        self,
        instrument_id: InstrumentId,
        client_order_id: ClientOrderId | None = None,
        venue_order_id: VenueOrderId | None = None,
    ) -> OrderStatusReport | None:
        """
        Generate an order status report for the given order ID.

        Parameters
        ----------
        instrument_id : InstrumentId
            The instrument ID for the order.
        client_order_id : ClientOrderId, optional
            The client order ID.
        venue_order_id : VenueOrderId, optional
            The venue order ID.

        Returns
        -------
        OrderStatusReport | None
            The order status report, or None if not found.

        """
        try:
            # Get open orders from Hyperliquid
            address = self._config.api_key  # Hyperliquid uses API key as address
            orders = await self._client.get_open_orders(address)
            
            # Find the specific order
            for order_data in orders:
                order_id = order_data.get('oid')
                if venue_order_id and str(order_id) == venue_order_id.value:
                    return self._parse_order_status_report(order_data, instrument_id)
                    
            return None
            
        except Exception as e:
            self._log.error(f"Failed to generate order status report: {e}")
            return None

    async def generate_order_status_reports(
        self,
        instrument_id: InstrumentId | None = None,
        start: int | None = None,
        end: int | None = None,
        open_only: bool = False,
    ) -> list[OrderStatusReport]:
        """
        Generate order status reports.

        Parameters
        ----------
        instrument_id : InstrumentId, optional
            The instrument ID to filter for.
        start : int, optional
            The start timestamp (UNIX nanoseconds) for the report.
        end : int, optional
            The end timestamp (UNIX nanoseconds) for the report.
        open_only : bool, default False
            If only open orders should be returned.

        Returns
        -------
        list[OrderStatusReport]
            The order status reports.

        """
        try:
            reports = []
            address = self._config.api_key
            
            if open_only:
                # Get only open orders
                orders = await self._client.get_open_orders(address)
                for order_data in orders:
                    if instrument_id is None or self._matches_instrument(order_data, instrument_id):
                        report = self._parse_order_status_report(order_data, instrument_id)
                        if report:
                            reports.append(report)
            
            return reports
            
        except Exception as e:
            self._log.error(f"Failed to generate order status reports: {e}")
            return []

    async def generate_trade_reports(
        self,
        instrument_id: InstrumentId | None = None,
        venue_order_id: VenueOrderId | None = None,
        start: int | None = None,
        end: int | None = None,
    ) -> list[FillReport]:
        """
        Generate trade reports.

        Parameters
        ----------
        instrument_id : InstrumentId, optional
            The instrument ID to filter for.
        venue_order_id : VenueOrderId, optional
            The venue order ID to filter for.
        start : int, optional
            The start timestamp (UNIX nanoseconds) for the report.
        end : int, optional
            The end timestamp (UNIX nanoseconds) for the report.

        Returns
        -------
        list[FillReport]
            The trade reports.

        """
        try:
            reports = []
            address = self._config.api_key
            
            # Get user fills (trades)
            fills = await self._client.get_user_fills(address)
            
            for fill_data in fills:
                if instrument_id is None or self._matches_instrument(fill_data, instrument_id):
                    report = self._parse_trade_report(fill_data, instrument_id)
                    if report:
                        reports.append(report)
            
            return reports
            
        except Exception as e:
            self._log.error(f"Failed to generate trade reports: {e}")
            return []

    async def generate_position_status_reports(
        self,
        instrument_id: InstrumentId | None = None,
        start: int | None = None,
        end: int | None = None,
    ) -> list[PositionStatusReport]:
        """
        Generate position status reports.

        Parameters
        ----------
        instrument_id : InstrumentId, optional
            The instrument ID to filter for.
        start : int, optional
            The start timestamp (UNIX nanoseconds) for the report.
        end : int, optional
            The end timestamp (UNIX nanoseconds) for the report.

        Returns
        -------
        list[PositionStatusReport]
            The position status reports.

        """
        try:
            # Hyperliquid doesn't have a direct position endpoint in the public SDK
            # Positions would need to be derived from account state or calculated
            # For now, return empty list
            self._log.warning("Position status reports not yet implemented for Hyperliquid")
            return []
            
        except Exception as e:
            self._log.error(f"Failed to generate position status reports: {e}")
            return []

    # -- ORDER MANAGEMENT ----------------------------------------------------------------------------

    async def _submit_order(self, order: Order) -> None:
        """
        Submit an order to Hyperliquid.

        Parameters
        ----------
        order : Order
            The order to submit.

        """
        try:
            # Convert NautilusTrader order to Hyperliquid format
            hyperliquid_order = self._convert_order_to_hyperliquid(order)
            
            # Submit order via Hyperliquid API
            # Note: This is a placeholder as the actual order submission
            # would require the full Hyperliquid SDK with signing capabilities
            self._log.warning(f"Order submission not yet implemented: {order}")
            
            # For now, simulate order acceptance
            self.generate_order_submitted(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                ts_event=self._clock.timestamp_ns(),
            )
            
        except Exception as e:
            self._log.error(f"Failed to submit order {order.client_order_id}: {e}")
            self.generate_order_rejected(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=str(e),
                ts_event=self._clock.timestamp_ns(),
            )

    async def _modify_order(self, order: Order, quantity: Quantity, price: Price | None = None) -> None:
        """
        Modify an order.

        Parameters
        ----------
        order : Order
            The order to modify.
        quantity : Quantity
            The new quantity.
        price : Price, optional
            The new price.

        """
        self._log.warning(f"Order modification not yet implemented: {order.client_order_id}")

    async def _cancel_order(self, order: Order) -> None:
        """
        Cancel an order.

        Parameters
        ----------
        order : Order
            The order to cancel.

        """
        self._log.warning(f"Order cancellation not yet implemented: {order.client_order_id}")

    async def _cancel_all_orders(self, instrument_id: InstrumentId) -> None:
        """
        Cancel all orders for the given instrument.

        Parameters
        ----------
        instrument_id : InstrumentId
            The instrument ID.

        """
        self._log.warning(f"Cancel all orders not yet implemented for {instrument_id}")

    # -- HELPER METHODS ------------------------------------------------------------------------------

    def _convert_order_to_hyperliquid(self, order: Order) -> dict[str, Any]:
        """
        Convert a NautilusTrader order to Hyperliquid format.

        Parameters
        ----------
        order : Order
            The order to convert.

        Returns
        -------
        dict[str, Any]
            The order in Hyperliquid format.

        """
        # Get the symbol without venue suffix
        symbol = order.instrument_id.symbol.value.replace(f".{HYPERLIQUID_VENUE.value}", "")
        
        hyperliquid_order = {
            "coin": symbol,
            "is_buy": order.side == OrderSide.BUY,
            "sz": float(order.quantity),
            "limit_px": float(order.price) if hasattr(order, 'price') and order.price else None,
            "order_type": self._convert_order_type(order.order_type),
            "reduce_only": getattr(order, 'reduce_only', False),
        }
        
        return hyperliquid_order

    def _convert_order_type(self, order_type: OrderType) -> str:
        """
        Convert NautilusTrader order type to Hyperliquid format.

        Parameters
        ----------
        order_type : OrderType
            The order type to convert.

        Returns
        -------
        str
            The Hyperliquid order type.

        """
        if order_type == OrderType.MARKET:
            return "Market"
        elif order_type == OrderType.LIMIT:
            return "Limit"
        elif order_type in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT):
            return "Stop"
        else:
            return "Limit"  # Default fallback

    def _parse_order_status_report(self, order_data: dict[str, Any], instrument_id: InstrumentId | None) -> OrderStatusReport | None:
        """
        Parse an order status report from Hyperliquid data.

        Parameters
        ----------
        order_data : dict[str, Any]
            The order data from Hyperliquid.
        instrument_id : InstrumentId, optional
            The instrument ID.

        Returns
        -------
        OrderStatusReport | None
            The parsed order status report.

        """
        try:
            # This is a simplified implementation
            # A full implementation would need proper parsing of all Hyperliquid order fields
            
            order_id = str(order_data.get('oid', ''))
            venue_order_id = VenueOrderId(order_id)
            
            return OrderStatusReport(
                account_id=self._account_id,
                instrument_id=instrument_id or InstrumentId.from_str(f"{order_data.get('coin', 'UNKNOWN')}-USD.HYPERLIQUID"),
                venue_order_id=venue_order_id,
                order_side=OrderSide.BUY if order_data.get('side') == 'B' else OrderSide.SELL,
                order_type=OrderType.LIMIT,  # Simplified
                time_in_force=TimeInForce.GTC,  # Simplified
                order_status=OrderStatus.ACCEPTED,  # Simplified
                price=Price.from_str(str(order_data.get('limit_px', '0'))),
                quantity=Quantity.from_str(str(order_data.get('sz', '0'))),
                filled_qty=Quantity.from_str('0'),  # Would need to calculate from fills
                ts_accepted=self._clock.timestamp_ns(),
                ts_last=self._clock.timestamp_ns(),
                report_id=UUID4(),
            )
            
        except Exception as e:
            self._log.error(f"Failed to parse order status report: {e}")
            return None

    def _parse_trade_report(self, fill_data: dict[str, Any], instrument_id: InstrumentId | None) -> FillReport | None:
        """
        Parse a trade report from Hyperliquid fill data.

        Parameters
        ----------
        fill_data : dict[str, Any]
            The fill data from Hyperliquid.
        instrument_id : InstrumentId, optional
            The instrument ID.

        Returns
        -------
        FillReport | None
            The parsed trade report.

        """
        try:
            # Simplified implementation
            return FillReport(
                account_id=self._account_id,
                instrument_id=instrument_id or InstrumentId.from_str(f"{fill_data.get('coin', 'UNKNOWN')}-USD.HYPERLIQUID"),
                venue_order_id=VenueOrderId(str(fill_data.get('oid', ''))),
                trade_id=str(fill_data.get('hash', '')),
                order_side=OrderSide.BUY if fill_data.get('side') == 'B' else OrderSide.SELL,
                last_qty=Quantity.from_str(str(fill_data.get('sz', '0'))),
                last_px=Price.from_str(str(fill_data.get('px', '0'))),
                commission=Money.from_str(str(fill_data.get('fee', '0'))),
                liquidity_side=None,  # Would need additional logic
                ts_event=fill_data.get('time', 0) * 1_000_000,  # Convert to nanoseconds
                report_id=UUID4(),
            )
            
        except Exception as e:
            self._log.error(f"Failed to parse trade report: {e}")
            return None

    def _matches_instrument(self, data: dict[str, Any], instrument_id: InstrumentId) -> bool:
        """
        Check if data matches the given instrument ID.

        Parameters
        ----------
        data : dict[str, Any]
            The data to check.
        instrument_id : InstrumentId
            The instrument ID to match.

        Returns
        -------
        bool
            True if the data matches the instrument.

        """
        symbol = data.get('coin', '')
        expected_symbol = instrument_id.symbol.value.replace(f".{HYPERLIQUID_VENUE.value}", "")
        return symbol == expected_symbol
