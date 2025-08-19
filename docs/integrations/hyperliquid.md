# Hyperliquid

The Hyperliquid adapter provides connectivity to the [Hyperliquid](https://hyperliquid.xyz) decentralized perpetual exchange.

## Features

### Data Client
- ✅ **Instrument Discovery**: Automatic loading of all available perpetual contracts
- ✅ **Real-time Market Data**: Live trade ticks and order book data via WebSocket
- ✅ **Historical Data**: Trade ticks, order book snapshots, and OHLCV bars
- ✅ **Quote Ticks**: Best bid/ask derived from L2 order book data

### Execution Client  
- ✅ **Order Management**: Support for market and limit orders
- ✅ **Account Reporting**: Order status and trade reports
- ✅ **Portfolio Tracking**: Position and balance monitoring
- ⚠️ **Order Execution**: Requires full SDK integration (in development)

## Supported Instruments

- **Perpetual Futures**: All USD-settled perpetual contracts (BTC-USD, ETH-USD, SOL-USD, etc.)
- **Settlement**: USD settlement currency
- **Leverage**: Up to 50x leverage (varies by instrument)

## Getting Started

### Installation

The Hyperliquid adapter is included with NautilusTrader. Build the project to enable the adapter:

```bash
cd nautilus_trader
make build
```

### Configuration

#### Data Client (Public Data)

```python
from nautilus_trader.adapters.hyperliquid import HYPERLIQUID, HyperliquidDataClientConfig
from nautilus_trader.config import InstrumentProviderConfig, TradingNodeConfig

config = TradingNodeConfig(
    data_clients={
        HYPERLIQUID: HyperliquidDataClientConfig(
            testnet=False,  # Set to True for testnet
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
)
```

#### Execution Client (Trading)

```python
from nautilus_trader.adapters.hyperliquid import HyperliquidExecClientConfig
from pydantic import SecretStr

config = TradingNodeConfig(
    exec_clients={
        HYPERLIQUID: HyperliquidExecClientConfig(
            api_key="your_api_key",
            api_secret=SecretStr("your_api_secret"),
            testnet=False,
        ),
    },
)
```

### Basic Usage

```python
import asyncio
from nautilus_trader.adapters.hyperliquid import (
    HYPERLIQUID,
    HyperliquidDataClientConfig,
    HyperliquidLiveDataClientFactory,
)
from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import TradingNodeConfig

# Configure and start the trading node
config = TradingNodeConfig(
    data_clients={
        HYPERLIQUID: HyperliquidDataClientConfig(),
    },
)

node = TradingNode(config=config)
node.add_data_client_factory(HYPERLIQUID, HyperliquidLiveDataClientFactory)
node.build()

# Subscribe to market data
btc_usd = InstrumentId.from_str("BTC-USD.HYPERLIQUID")
node.data_engine.subscribe_trade_ticks(btc_usd)
node.data_engine.subscribe_quote_ticks(btc_usd)

# Run the node
node.run()
```

## API Reference

### Configuration Classes

- `HyperliquidDataClientConfig`: Configuration for market data client
- `HyperliquidExecClientConfig`: Configuration for execution client

### Client Classes

- `HyperliquidDataClient`: Live market data client
- `HyperliquidExecutionClient`: Live execution client
- `HyperliquidInstrumentProvider`: Instrument discovery and management

### Factory Classes

- `HyperliquidLiveDataClientFactory`: Creates live data clients
- `HyperliquidLiveExecClientFactory`: Creates live execution clients

## Environment Setup

### Testnet

Use the testnet for development and testing:

```python
config = HyperliquidDataClientConfig.testnet()
```

### Production

For live trading, ensure you have:
- Valid API credentials from Hyperliquid
- Sufficient account balance
- Proper risk management controls

## Examples

See the complete examples in:
- `xt_trader/python/examples/hyperliquid_live_data_subscriber.py`
- `xt_trader/python/examples/test_hyperliquid_adapter.py`

## Limitations

- Order execution requires full Hyperliquid SDK integration (in development)
- Position tracking may need manual reconciliation
- Limited to perpetual futures (no spot trading)

## Support

For issues related to the Hyperliquid adapter:
1. Check the [Hyperliquid documentation](https://hyperliquid.gitbook.io/)
2. Review NautilusTrader adapter patterns
3. Test with the provided examples

:::info
The Hyperliquid adapter integrates the official [hyperliquid-rust-sdk](https://github.com/hyperliquid-dex/hyperliquid-rust-sdk) for maximum compatibility and performance.
:::
