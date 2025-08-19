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
Configuration for Hyperliquid adapter.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, PositiveInt, SecretStr

from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.live.config import LiveDataClientConfig, LiveExecClientConfig


class HyperliquidDataClientConfig(LiveDataClientConfig, frozen=True, kw_only=True):
    """
    Configuration for ``HyperliquidDataClient`` instances.

    Parameters
    ----------
    api_key : str, optional
        The Hyperliquid API key for the client.
    api_secret : str, optional
        The Hyperliquid API secret for the client.
    base_url : str, optional
        The base URL for the HTTP API.
    ws_base_url : str, optional
        The base URL for the WebSocket API.
    testnet : bool, default False
        If the client is connecting to the testnet.
    timeout_connection : PositiveInt, default 30
        The timeout (seconds) for all connection operations.
    timeout_reconciliation : PositiveInt, default 5
        The timeout (seconds) for all reconciliation operations.
    timeout_portfolio : PositiveInt, default 10
        The timeout (seconds) for all portfolio operations.
    timeout_disconnection : PositiveInt, default 10
        The timeout (seconds) for all disconnection operations.
    timeout_post_stop : PositiveInt, default 5
        The timeout (seconds) after stopping to ensure graceful shutdown.
    heartbeat_interval : PositiveInt, default 30
        The heartbeat interval (seconds) for WebSocket connections.
    instrument_provider : InstrumentProviderConfig, optional
        The instrument provider configuration.

    """

    api_key: str | None = None
    api_secret: SecretStr | None = None
    base_url: str | None = None
    ws_base_url: str | None = None
    testnet: bool = False
    timeout_connection: PositiveInt = 30
    timeout_reconciliation: PositiveInt = 5
    timeout_portfolio: PositiveInt = 10
    timeout_disconnection: PositiveInt = 10
    timeout_post_stop: PositiveInt = 5
    heartbeat_interval: PositiveInt = 30
    instrument_provider: InstrumentProviderConfig = Field(
        default_factory=lambda: InstrumentProviderConfig(load_all=True),
    )

    @classmethod
    def create_testnet(cls, **kwargs: Any) -> HyperliquidDataClientConfig:
        """
        Create a testnet configuration.

        Returns
        -------
        HyperliquidDataClientConfig

        """
        return cls(
            testnet=True,
            base_url="https://api.hyperliquid-testnet.xyz",
            ws_base_url="wss://api.hyperliquid-testnet.xyz/ws",
            **kwargs,
        )


class HyperliquidExecClientConfig(LiveExecClientConfig, frozen=True, kw_only=True):
    """
    Configuration for ``HyperliquidExecClient`` instances.

    Parameters
    ----------
    api_key : str
        The Hyperliquid API key for the client.
    api_secret : str
        The Hyperliquid API secret for the client.
    private_key : str, optional
        The private key for signing transactions.
    base_url : str, optional
        The base URL for the HTTP API.
    ws_base_url : str, optional
        The base URL for the WebSocket API.
    testnet : bool, default False
        If the client is connecting to the testnet.
    timeout_connection : PositiveInt, default 30
        The timeout (seconds) for all connection operations.
    timeout_reconciliation : PositiveInt, default 5
        The timeout (seconds) for all reconciliation operations.
    timeout_portfolio : PositiveInt, default 10
        The timeout (seconds) for all portfolio operations.
    timeout_disconnection : PositiveInt, default 10
        The timeout (seconds) for all disconnection operations.
    timeout_post_stop : PositiveInt, default 5
        The timeout (seconds) after stopping to ensure graceful shutdown.
    heartbeat_interval : PositiveInt, default 30
        The heartbeat interval (seconds) for WebSocket connections.
    max_retries : PositiveInt, default 3
        The maximum number of retries for failed requests.
    retry_delay : PositiveInt, default 1
        The initial retry delay (seconds).
    max_retry_delay : PositiveInt, default 10
        The maximum retry delay (seconds).
    reconciliation : bool, default True
        Whether to enable order reconciliation on startup.
    reconciliation_lookback_mins : PositiveInt, default 1440
        The reconciliation lookback period (minutes).
    instrument_provider : InstrumentProviderConfig, optional
        The instrument provider configuration.

    """

    api_key: str
    api_secret: SecretStr
    private_key: str | None = None
    base_url: str | None = None
    ws_base_url: str | None = None
    testnet: bool = False
    timeout_connection: PositiveInt = 30
    timeout_reconciliation: PositiveInt = 5
    timeout_portfolio: PositiveInt = 10
    timeout_disconnection: PositiveInt = 10
    timeout_post_stop: PositiveInt = 5
    heartbeat_interval: PositiveInt = 30
    max_retries: PositiveInt = 3
    retry_delay: PositiveInt = 1
    max_retry_delay: PositiveInt = 10
    reconciliation: bool = True
    reconciliation_lookback_mins: PositiveInt = 1440  # 24 hours
    instrument_provider: InstrumentProviderConfig = Field(
        default_factory=lambda: InstrumentProviderConfig(load_all=True),
    )

    @classmethod
    def create_testnet(cls, **kwargs: Any) -> HyperliquidExecClientConfig:
        """
        Create a testnet configuration.

        Returns
        -------
        HyperliquidExecClientConfig

        """
        # Ensure required fields are provided
        api_key = kwargs.pop("api_key", "")
        api_secret = kwargs.pop("api_secret", "")
        
        return cls(
            api_key=api_key,
            api_secret=SecretStr(api_secret) if isinstance(api_secret, str) else api_secret,
            testnet=True,
            base_url="https://api.hyperliquid-testnet.xyz",
            ws_base_url="wss://api.hyperliquid-testnet.xyz/ws",
            **kwargs,
        )
