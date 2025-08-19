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
Factory classes for creating live Hyperliquid clients.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from nautilus_trader.adapters.hyperliquid.config import HyperliquidDataClientConfig, HyperliquidExecClientConfig
from nautilus_trader.adapters.hyperliquid.data import HyperliquidDataClient
from nautilus_trader.adapters.hyperliquid.execution import HyperliquidExecutionClient
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.live.factories import LiveDataClientFactory, LiveExecClientFactory

if TYPE_CHECKING:
    from nautilus_trader.live.data_client import LiveMarketDataClient
    from nautilus_trader.live.execution_client import LiveExecutionClient


class HyperliquidLiveDataClientFactory(LiveDataClientFactory):
    """
    Provides a `HyperliquidDataClient` factory.
    """

    @staticmethod
    def create(
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: HyperliquidDataClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> LiveMarketDataClient:
        """
        Create a new Hyperliquid data client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : HyperliquidDataClientConfig
            The configuration for the client.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        LiveMarketDataClient
            The Hyperliquid data client.

        """
        # Import here to avoid circular imports during startup
        try:
            from nautilus_trader.core.nautilus_pyo3 import HyperliquidHttpClient
            from nautilus_trader.core.nautilus_pyo3 import HyperliquidWebSocketClient
        except ImportError:
            # Fallback for development - create dummy clients
            class DummyHttpClient:
                def __init__(self, *args, **kwargs):
                    pass
                    
                async def get_meta(self):
                    return type('Meta', (), {'universe': []})()
                    
                async def get_recent_trades(self, symbol):
                    return []
                    
                async def get_candles(self, symbol, interval, start_time=None, end_time=None):
                    return []
                    
            class DummyWebSocketClient:
                def __init__(self, *args, **kwargs):
                    pass
                    
                async def connect(self):
                    pass
                    
                async def disconnect(self):
                    pass
                    
                async def subscribe_trades(self, symbol):
                    pass
                    
                async def subscribe_l2_book(self, symbol):
                    pass
                    
                async def unsubscribe(self, subscription_type, symbol):
                    pass
                    
            HyperliquidHttpClient = DummyHttpClient
            HyperliquidWebSocketClient = DummyWebSocketClient

        # Determine base URLs
        if config.testnet:
            base_url = config.base_url or "https://api.hyperliquid-testnet.xyz"
            ws_base_url = config.ws_base_url or "wss://api.hyperliquid-testnet.xyz/ws"
        else:
            base_url = config.base_url or "https://api.hyperliquid.xyz"
            ws_base_url = config.ws_base_url or "wss://api.hyperliquid.xyz/ws"

        # Create HTTP client
        http_client = HyperliquidHttpClient(
            base_url=base_url,
            timeout=config.timeout_connection * 1000,  # Convert to milliseconds
        )

        # Create WebSocket client
        ws_client = HyperliquidWebSocketClient(base_url=ws_base_url)

        # Create and return the data client
        return HyperliquidDataClient(
            loop=loop,
            client=http_client,
            ws_client=ws_client,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            config=config,
        )


class HyperliquidLiveExecClientFactory(LiveExecClientFactory):
    """
    Provides a `HyperliquidExecutionClient` factory.
    """

    @staticmethod
    def create(
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: HyperliquidExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> LiveExecutionClient:
        """
        Create a new Hyperliquid execution client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : HyperliquidExecClientConfig
            The configuration for the client.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        LiveExecutionClient
            The Hyperliquid execution client.

        """
        # Import here to avoid circular imports during startup
        try:
            from nautilus_trader.core.nautilus_pyo3 import HyperliquidHttpClient
            from nautilus_trader.core.nautilus_pyo3 import HyperliquidWebSocketClient
        except ImportError:
            # Fallback for development - create dummy clients
            class DummyHttpClient:
                def __init__(self, *args, **kwargs):
                    pass
                    
            class DummyWebSocketClient:
                def __init__(self, *args, **kwargs):
                    pass
                    
            HyperliquidHttpClient = DummyHttpClient
            HyperliquidWebSocketClient = DummyWebSocketClient

        # Determine base URLs
        if config.testnet:
            base_url = config.base_url or "https://api.hyperliquid-testnet.xyz"
            ws_base_url = config.ws_base_url or "wss://api.hyperliquid-testnet.xyz/ws"
        else:
            base_url = config.base_url or "https://api.hyperliquid.xyz"
            ws_base_url = config.ws_base_url or "wss://api.hyperliquid.xyz/ws"

        # Create HTTP client with authentication
        http_client = HyperliquidHttpClient(
            base_url=base_url,
            timeout=config.timeout_connection * 1000,  # Convert to milliseconds
            api_key=config.api_key,
            api_secret=config.api_secret.get_secret_value() if config.api_secret else None,
        )

        # Create WebSocket client with authentication
        ws_client = HyperliquidWebSocketClient(
            base_url=ws_base_url,
            api_key=config.api_key,
            api_secret=config.api_secret.get_secret_value() if config.api_secret else None,
        )

        # Create and return the execution client
        return HyperliquidExecutionClient(
            loop=loop,
            client=http_client,
            ws_client=ws_client,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            config=config,
        )
