#!/usr/bin/env python3
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

from decimal import Decimal

from nautilus_trader.adapters.hyperliquid import HYPERLIQUID
from nautilus_trader.adapters.hyperliquid import HyperliquidDataClientConfig
from nautilus_trader.adapters.hyperliquid import HyperliquidLiveDataClientFactory
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LiveExecEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.test_kit.strategies.tester_data import DataTester
from nautilus_trader.test_kit.strategies.tester_data import DataTesterConfig


# *** THIS IS A TEST STRATEGY WITH NO ALPHA ADVANTAGE WHATSOEVER. ***
# *** IT IS NOT INTENDED TO BE USED TO TRADE LIVE WITH REAL MONEY. ***

# Configuration
# Hyperliquid currently supports perpetual futures (crypto derivatives)
symbol = "BTC-PERP"  # BTC perpetual futures
trade_size = Decimal("0.001")  # Small size for testing

# Configure the trading node
config_node = TradingNodeConfig(
    trader_id=TraderId("TESTER-001"),
    logging=LoggingConfig(log_level="INFO", use_pyo3=True),
    exec_engine=LiveExecEngineConfig(
        reconciliation=False,  # Not applicable for data testing
    ),
    data_clients={
        HYPERLIQUID: HyperliquidDataClientConfig(
            private_key=None,  # 'HYPERLIQUID_PRIVATE_KEY' env var (optional for public data)
            wallet_address=None,  # 'HYPERLIQUID_WALLET_ADDRESS' env var (optional for public data)
            base_url_http=None,  # Override with custom endpoint
            base_url_ws=None,  # Override with custom WebSocket endpoint
            testnet=True,  # Use testnet for safety (set to False for mainnet)
            instrument_provider=InstrumentProviderConfig(load_all=True),
            http_timeout_secs=30,  # Set to reasonable duration for DEX
            update_instruments_interval_mins=60,  # Update instruments every hour
        ),
    },
    timeout_connection=30.0,  # Longer timeout for DEX
    timeout_disconnection=10.0,
    timeout_post_stop=0.0,  # No stop delay needed for data testing
)

# Instantiate the node with a configuration
node = TradingNode(config=config_node)

# Configure and initialize the tester
config_tester = DataTesterConfig(
    instrument_ids=[InstrumentId.from_str(f"{symbol}.HYPERLIQUID")],
    bar_types=[BarType.from_str(f"{symbol}.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL")],
    
    # Real-time data subscriptions
    subscribe_book_deltas=True,  # L2 order book deltas
    subscribe_book_at_interval=True,  # Periodic book snapshots
    subscribe_quotes=True,  # Quote ticks (mid prices)
    subscribe_trades=True,  # Trade ticks
    
    # Historical data requests (not yet supported by Hyperliquid adapter)
    # subscribe_bars=False,  # Historical bars
    # request_bars=False,  # Request historical bars
    
    # Book management settings
    book_interval_ms=100,  # Book snapshot interval (100ms)
    book_levels_to_print=10,  # Number of levels to display
    manage_book=True,  # Enable book management
    use_pyo3_book=True,  # Use optimized PyO3 order book
    
    # Additional settings
    # subscribe_instrument_status=False,  # Instrument status updates
    # subscribe_instrument_close=False,  # Instrument close updates
)
tester = DataTester(config=config_tester)

node.trader.add_actor(tester)

# Register your client factories with the node
node.add_data_client_factory(HYPERLIQUID, HyperliquidLiveDataClientFactory)
node.build()


# Stop and dispose of the node with SIGINT/CTRL+C
if __name__ == "__main__":
    print("🚀 Starting Hyperliquid Data Tester")
    print("⚠️  Using testnet mode for safety")
    print(f"📊 Testing instrument: {symbol}.HYPERLIQUID") 
    print("💡 Available data feeds:")
    print("   📚 L2 Order Book (real-time deltas and snapshots)")
    print("   💰 Quote Ticks (mid prices from allMids feed)")
    print("   📈 Trade Ticks (individual trades)")
    print("🛑 Press CTRL+C to stop")
    print("-" * 60)
    
    try:
        node.run()
    finally:
        print("\n" + "=" * 60)
        print("🛑 Shutting down Hyperliquid Data Tester")
        print("🧹 Cleaning up resources...")
        node.dispose()
        print("✅ Shutdown complete")