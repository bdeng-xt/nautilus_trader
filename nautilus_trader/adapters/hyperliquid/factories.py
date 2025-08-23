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
from functools import lru_cache
from typing import Any

from nautilus_trader.adapters.hyperliquid.config import HyperliquidDataClientConfig
from nautilus_trader.adapters.hyperliquid.config import HyperliquidExecClientConfig
from nautilus_trader.adapters.hyperliquid.data import HyperliquidDataClient
from nautilus_trader.adapters.hyperliquid.execution import HyperliquidExecutionClient
from nautilus_trader.adapters.hyperliquid.providers import HyperliquidInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.live.factories import LiveDataClientFactory
from nautilus_trader.live.factories import LiveExecClientFactory


def get_hyperliquid_http_client(
    private_key: str | None = None,
    wallet_address: str | None = None,
    testnet: bool = False,
    base_url: str | None = None,
    timeout_secs: int = 60,
) -> Any:
    """
    Create a Hyperliquid HTTP client.

    This creates a Rust HTTP client using the Python bindings.

    Parameters
    ----------
    private_key : str, optional
        The Hyperliquid private key for signing requests.
    wallet_address : str, optional
        The wallet address for the account.
    testnet : bool, default False
        Whether to connect to testnet.
    base_url : str, optional
        The base URL for the API endpoints.
    timeout_secs : int, default 60
        The timeout (seconds) for HTTP requests.

    Returns
    -------
    HyperliquidHttpClient
        The Rust HTTP client.

    """
    # For now, return a mock client until we have proper Rust bindings
    # In the future, this would create the actual Rust client
    class MockHttpClient:
        def get_instruments(self) -> str:
            return '[]'
        
        def get_user_state(self) -> str:
            return '{"crossMarginSummary": {"accountValue": "0"}}'
            
        def get_open_orders(self) -> str:
            return '[]'
    
    return MockHttpClient()


def get_hyperliquid_websocket_client(
    private_key: str | None = None,
    wallet_address: str | None = None,
    testnet: bool = False,
    base_url: str | None = None,
) -> Any:
    """
    Create a Hyperliquid WebSocket client.

    This creates a Rust WebSocket client using the Python bindings.

    Parameters
    ----------
    private_key : str, optional
        The Hyperliquid private key for signing requests.
    wallet_address : str, optional
        The wallet address for the account.
    testnet : bool, default False
        Whether to connect to testnet.
    base_url : str, optional
        The base URL for WebSocket.

    Returns
    -------
    HyperliquidWebSocketClient
        The Rust WebSocket client.

    """
    # For now, return a mock client until we have proper Rust bindings
    # In the future, this would create the actual Rust client
    class MockWebSocketClient:
        def connect(self):
            pass
            
        def disconnect(self):
            pass
            
        def subscribe_trades(self, symbol: str):
            pass
            
        def subscribe_l2_book(self, symbol: str):
            pass
            
        def subscribe_all_mids(self):
            pass
            
        def subscribe_user_events(self, user: str):
            pass
            
        def read_message(self) -> str | None:
            return None
    
    return MockWebSocketClient()


@lru_cache(1)
def get_hyperliquid_instrument_provider(
    http_client: Any,
    clock: LiveClock,
    config: InstrumentProviderConfig,
) -> HyperliquidInstrumentProvider:
    """
    Cache and return a Hyperliquid instrument provider.

    If a cached provider already exists, then that provider will be returned.

    Parameters
    ----------
    http_client : Any
        The HTTP client for the instrument provider.
    clock : LiveClock
        The clock for the instrument provider.
    config : InstrumentProviderConfig
        The configuration for the instrument provider.

    Returns
    -------
    HyperliquidInstrumentProvider

    """
    return HyperliquidInstrumentProvider(
        client=http_client,
        clock=clock,
        config=config,
    )


class HyperliquidLiveDataClientFactory(LiveDataClientFactory):
    """
    Provides a Hyperliquid live data client factory.
    """

    @staticmethod
    def create(  # type: ignore
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: HyperliquidDataClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> HyperliquidDataClient:
        """
        Create a new Hyperliquid data client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : HyperliquidDataClientConfig
            The client configuration.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock: LiveClock
            The clock for the client.

        Returns
        -------
        HyperliquidDataClient

        """
        http_client = get_hyperliquid_http_client(
            private_key=config.private_key,
            wallet_address=config.wallet_address,
            testnet=config.testnet,
            base_url=config.base_url_http,
            timeout_secs=config.http_timeout_secs or 60,
        )
        
        ws_client = get_hyperliquid_websocket_client(
            private_key=config.private_key,
            wallet_address=config.wallet_address,
            testnet=config.testnet,
            base_url=config.base_url_ws,
        )
        
        provider = get_hyperliquid_instrument_provider(
            http_client=http_client,
            clock=clock,
            config=config.instrument_provider,
        )

        return HyperliquidDataClient(
            loop=loop,
            http_client=http_client,
            ws_client=ws_client,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=provider,
            config=config,
            name=name,
        )


class HyperliquidLiveExecClientFactory(LiveExecClientFactory):
    """
    Provides a Hyperliquid live execution client factory.
    """

    @staticmethod
    def create(  # type: ignore
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: HyperliquidExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> HyperliquidExecutionClient:
        """
        Create a new Hyperliquid execution client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for the client.
        name : str
            The custom client ID.
        config : HyperliquidExecClientConfig
            The client configuration.
        msgbus : MessageBus
            The message bus for the client.
        cache : Cache
            The cache for the client.
        clock : LiveClock
            The clock for the client.

        Returns
        -------
        HyperliquidExecutionClient

        """
        http_client = get_hyperliquid_http_client(
            private_key=config.private_key,
            wallet_address=config.wallet_address,
            testnet=config.testnet,
            base_url=config.base_url_http,
            timeout_secs=config.http_timeout_secs or 60,
        )
        
        ws_client = get_hyperliquid_websocket_client(
            private_key=config.private_key,
            wallet_address=config.wallet_address,
            testnet=config.testnet,
            base_url=config.base_url_ws,
        )
        
        provider = get_hyperliquid_instrument_provider(
            http_client=http_client,
            clock=clock,
            config=config.instrument_provider,
        )

        return HyperliquidExecutionClient(
            loop=loop,
            http_client=http_client,
            ws_client=ws_client,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=provider,
            config=config,
            name=name,
        )
