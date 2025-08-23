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

from nautilus_trader.adapters.hyperliquid.constants import HYPERLIQUID_VENUE
from nautilus_trader.config import LiveDataClientConfig
from nautilus_trader.config import LiveExecClientConfig
from nautilus_trader.config import PositiveInt
from nautilus_trader.model.identifiers import Venue


class HyperliquidDataClientConfig(LiveDataClientConfig, frozen=True):
    """
    Configuration for ``HyperliquidDataClient`` instances.

    Parameters
    ----------
    venue : Venue, default HYPERLIQUID_VENUE
        The venue for the client.
    api_key : str, optional
        The Hyperliquid API key (for private endpoints).
        If ``None`` then will source the `HYPERLIQUID_API_KEY` or
        `HYPERLIQUID_TESTNET_API_KEY` environment variables.
    private_key : str, optional  
        The Hyperliquid private key for signing requests.
        If ``None`` then will source the `HYPERLIQUID_PRIVATE_KEY` or
        `HYPERLIQUID_TESTNET_PRIVATE_KEY` environment variables.
    wallet_address : str, optional
        The wallet address for the account.
        If ``None`` then will source the `HYPERLIQUID_WALLET_ADDRESS` or
        `HYPERLIQUID_TESTNET_WALLET_ADDRESS` environment variables.
    testnet : bool, default False
        If the client should connect to the Hyperliquid testnet.
    base_url_http : str, optional
        The HTTP client custom endpoint override.
    base_url_ws : str, optional
        The WebSocket client custom endpoint override.
    http_timeout_secs : PositiveInt or None, default 60
        The default timeout (seconds) for HTTP requests.

    """

    venue: Venue = HYPERLIQUID_VENUE
    api_key: str | None = None
    private_key: str | None = None
    wallet_address: str | None = None
    testnet: bool = False
    base_url_http: str | None = None
    base_url_ws: str | None = None
    http_timeout_secs: PositiveInt | None = 60


class HyperliquidExecClientConfig(LiveExecClientConfig, frozen=True):
    """
    Configuration for ``HyperliquidExecClient`` instances.

    Parameters
    ----------
    venue : Venue, default HYPERLIQUID_VENUE
        The venue for the client.
    api_key : str, optional
        The Hyperliquid API key (for private endpoints).
        If ``None`` then will source the `HYPERLIQUID_API_KEY` or
        `HYPERLIQUID_TESTNET_API_KEY` environment variables.
    private_key : str, optional  
        The Hyperliquid private key for signing requests.
        If ``None`` then will source the `HYPERLIQUID_PRIVATE_KEY` or
        `HYPERLIQUID_TESTNET_PRIVATE_KEY` environment variables.
    wallet_address : str, optional
        The wallet address for the account.
        If ``None`` then will source the `HYPERLIQUID_WALLET_ADDRESS` or
        `HYPERLIQUID_TESTNET_WALLET_ADDRESS` environment variables.
    testnet : bool, default False
        If the client should connect to the Hyperliquid testnet.
    base_url_http : str, optional
        The HTTP client custom endpoint override.
    base_url_ws : str, optional
        The WebSocket client custom endpoint override.
    http_timeout_secs : PositiveInt or None, default 60
        The default timeout (seconds) for HTTP requests.

    """

    venue: Venue = HYPERLIQUID_VENUE
    api_key: str | None = None
    private_key: str | None = None
    wallet_address: str | None = None
    testnet: bool = False
    base_url_http: str | None = None
    base_url_ws: str | None = None
    http_timeout_secs: PositiveInt | None = 60
