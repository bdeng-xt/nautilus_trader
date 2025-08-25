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

from nautilus_trader.adapters.hyperliquid import HYPERLIQUID
from nautilus_trader.adapters.hyperliquid import HyperliquidDataClientConfig
from nautilus_trader.adapters.hyperliquid import HyperliquidExecClientConfig
from nautilus_trader.adapters.hyperliquid import HyperliquidLiveDataClientFactory
from nautilus_trader.adapters.hyperliquid import HyperliquidLiveExecClientFactory
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LiveExecEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.test_kit.strategies.tester_execution import ExecutionTester
from nautilus_trader.test_kit.strategies.tester_execution import ExecutionTesterConfig


# *** THIS IS A TEST STRATEGY WITH NO ALPHA ADVANTAGE WHATSOEVER. ***
# *** IT IS NOT INTENDED TO BE USED TO TRADE LIVE WITH REAL MONEY. ***
# *** REQUIRES VALID PRIVATE KEY AND WALLET ADDRESS FOR AUTHENTICATION. ***

# Configuration
# NOTE: This requires valid credentials as it will attempt to connect to trading endpoints
symbol = "BTC-PERP"  # BTC perpetual futures

# Configure the trading node
config_node = TradingNodeConfig(
    trader_id=TraderId("EXEC-TESTER-001"),
    logging=LoggingConfig(log_level="INFO", use_pyo3=True),
    exec_engine=LiveExecEngineConfig(
        reconciliation=True,  # Enable trade reconciliation
        allow_cash_positions=True,  # Allow cash positions
    ),
    data_clients={
        HYPERLIQUID: HyperliquidDataClientConfig(
            private_key=None,  # 'HYPERLIQUID_TESTNET_PRIVATE_KEY' env var
            wallet_address=None,  # 'HYPERLIQUID_TESTNET_WALLET_ADDRESS' env var
            base_url_http=None,  # Default testnet endpoint
            base_url_ws=None,  # Default testnet endpoint
            testnet=True,  # ALWAYS use testnet for testing
            instrument_provider=InstrumentProviderConfig(load_all=True),
            http_timeout_secs=30,
            update_instruments_interval_mins=60,
        ),
    },
    exec_clients={
        HYPERLIQUID: HyperliquidExecClientConfig(
            private_key=None,  # 'HYPERLIQUID_TESTNET_PRIVATE_KEY' env var
            wallet_address=None,  # 'HYPERLIQUID_TESTNET_WALLET_ADDRESS' env var
            base_url_http=None,  # Default testnet endpoint
            base_url_ws=None,  # Default testnet endpoint
            testnet=True,  # ALWAYS use testnet for testing
            http_timeout_secs=30,
        ),
    },
    timeout_connection=30.0,
    timeout_disconnection=10.0,
    timeout_post_stop=2.0,
)

# Instantiate the node with a configuration
node = TradingNode(config=config_node)

# Configure and initialize the execution tester
# NOTE: ExecutionTester is for testing order management and execution workflows
# It does NOT automatically place orders - it provides tools to test execution capabilities
config_tester = ExecutionTesterConfig(
    # Test configuration - customize as needed
)
tester = ExecutionTester(config=config_tester)

node.trader.add_actor(tester)

# Register client factories with the node
node.add_data_client_factory(HYPERLIQUID, HyperliquidLiveDataClientFactory)
node.add_exec_client_factory(HYPERLIQUID, HyperliquidLiveExecClientFactory)
node.build()


# Stop and dispose of the node with SIGINT/CTRL+C
if __name__ == "__main__":
    print("⚡ Starting Hyperliquid Execution Tester")
    print("🔐 This example requires authentication credentials")
    print("⚠️  TESTNET MODE ONLY - Never use mainnet for testing!")
    print("🔑 Required environment variables:")
    print("   HYPERLIQUID_TESTNET_PRIVATE_KEY=your_testnet_private_key")
    print("   HYPERLIQUID_TESTNET_WALLET_ADDRESS=your_testnet_wallet_address")
    print("📊 Testing execution capabilities for Hyperliquid")
    print("💡 Features:")
    print("   🔗 WebSocket execution feed connectivity")
    print("   📋 Order management system integration")
    print("   ⚡ Execution event processing")
    print("   💼 Account state monitoring")
    print("🛑 Press CTRL+C to stop")
    print("⚠️  NOTE: This tester validates execution infrastructure but does not place orders automatically")
    print("-" * 80)
    
    try:
        node.run()
    except KeyboardInterrupt:
        print("\n🛑 Received CTRL+C signal")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Common issues:")
        print("   - Missing or invalid environment variables")
        print("   - Network connectivity problems")
        print("   - Invalid testnet credentials")
    finally:
        print("\n" + "=" * 80)
        print("🛑 Shutting down Hyperliquid Execution Tester")
        print("🧹 Cleaning up resources...")
        node.dispose()
        print("✅ Shutdown complete")