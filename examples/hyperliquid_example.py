#!/usr/bin/env python3
"""
Example script demonstrating how to use the Hyperliquid adapter with Nautilus Trader.

This example shows how to:
1. Configure the Hyperliquid data and execution clients
2. Connect to the Hyperliquid exchange
3. Subscribe to market data feeds
4. Handle instrument and market data updates

NOTE: This is a basic example and uses mock clients for demonstration.
In production, you would need actual Hyperliquid API credentials and
the full Rust integration.
"""

import asyncio
from decimal import Decimal

from nautilus_trader.adapters.hyperliquid import HYPERLIQUID_VENUE
from nautilus_trader.adapters.hyperliquid import HyperliquidDataClientConfig
from nautilus_trader.adapters.hyperliquid import HyperliquidExecClientConfig
from nautilus_trader.adapters.hyperliquid import HyperliquidLiveDataClientFactory
from nautilus_trader.adapters.hyperliquid import HyperliquidLiveExecClientFactory
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.common.enums import LogLevel
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LiveNodeConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol


async def main():
    """
    Main example function.
    """
    print("=== Nautilus Trader - Hyperliquid Adapter Example ===")
    
    # Configure logging
    logging_config = LoggingConfig(
        log_level=LogLevel.INFO,
        log_colors=True,
    )

    # Configure Hyperliquid data client
    data_config = HyperliquidDataClientConfig(
        venue=HYPERLIQUID_VENUE,
        private_key=None,  # Not needed for public data
        wallet_address=None,  # Not needed for public data
        testnet=False,
        instrument_provider=InstrumentProviderConfig(
            load_all=True,
        ),
    )

    # Configure Hyperliquid execution client
    exec_config = HyperliquidExecClientConfig(
        venue=HYPERLIQUID_VENUE,
        private_key="your_private_key_here",  # Replace with actual key for trading
        wallet_address="your_wallet_address_here",  # Replace with actual address
        testnet=False,
        instrument_provider=InstrumentProviderConfig(
            load_all=True,
        ),
    )

    # Create trading node configuration
    config = LiveNodeConfig(
        trader_id="TRADER-001",
        logging=logging_config,
        exec_engine={
            "reports_lookback_hours": 24,
        },
        data_clients={
            "HYPERLIQUID": data_config,
        },
        exec_clients={
            "HYPERLIQUID": exec_config,
        },
    )

    print("Creating trading node...")
    
    # Create the trading node
    node = TradingNode(config=config)

    try:
        print("Starting trading node...")
        await node.start_async()
        
        print("Trading node started successfully!")
        print(f"Connected to Hyperliquid venue: {HYPERLIQUID_VENUE}")
        
        # Get the data client
        data_client = node.data_engine.clients.get("HYPERLIQUID")
        if data_client:
            print("Hyperliquid data client connected")
            
        # Get the execution client
        exec_client = node.exec_engine.clients.get("HYPERLIQUID")
        if exec_client:
            print("Hyperliquid execution client connected")

        # Example: Subscribe to BTC-PERP trade ticks
        btc_perp = InstrumentId(Symbol("BTC-PERP"), HYPERLIQUID_VENUE)
        
        if data_client and data_client.is_connected:
            print(f"Subscribing to {btc_perp} trade ticks...")
            await data_client.subscribe_trade_ticks(btc_perp)
            
            print(f"Subscribing to {btc_perp} quote ticks...")
            await data_client.subscribe_quote_ticks(btc_perp)
            
            print(f"Subscribing to {btc_perp} order book...")
            await data_client.subscribe_order_book_deltas(btc_perp, depth=20)

        print("\n=== Market Data Stream ===")
        print("Listening for market data updates...")
        print("Press Ctrl+C to stop...")

        # Let it run for a while to demonstrate data flow
        await asyncio.sleep(30)

    except KeyboardInterrupt:
        print("\nReceived interrupt signal...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Shutting down trading node...")
        await node.stop_async()
        print("Trading node stopped.")


def example_strategy_config():
    """
    Example of how to configure a trading strategy with Hyperliquid.
    """
    from nautilus_trader.config import StrategyConfig
    
    # This would be a custom strategy configuration
    # that could be used with the Hyperliquid adapter
    strategy_config = {
        "strategy_id": "HyperliquidExample",
        "order_id_tag": "HYPERL",
        "risk_engine": {
            "bypass": False,
            "max_order_size": "100000",
        },
        "instruments": [
            "BTC-PERP.HYPERLIQUID",
            "ETH-PERP.HYPERLIQUID",
        ],
    }
    
    return strategy_config


if __name__ == "__main__":
    print("Starting Hyperliquid adapter example...")
    print("\nNOTE: This example uses mock clients for demonstration.")
    print("For live trading, you would need:")
    print("- Valid Hyperliquid API credentials")
    print("- Proper Rust client integration")
    print("- Risk management configuration")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample terminated by user.")
    except Exception as e:
        print(f"Example failed: {e}")
        raise