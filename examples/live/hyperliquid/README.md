# Hyperliquid Live Trading Examples

This directory contains examples for live trading with the Hyperliquid decentralized exchange (DEX) adapter.

## Prerequisites

1. **Install Dependencies**: Ensure Nautilus Trader is built with Hyperliquid support
2. **Environment Variables** (optional for public data, required for trading):
   ```bash
   # For testnet (recommended for testing)
   export HYPERLIQUID_TESTNET_PRIVATE_KEY="your_testnet_private_key" 
   export HYPERLIQUID_TESTNET_WALLET_ADDRESS="your_testnet_wallet_address"
   
   # For mainnet (use with caution!)
   export HYPERLIQUID_PRIVATE_KEY="your_mainnet_private_key"
   export HYPERLIQUID_WALLET_ADDRESS="your_mainnet_wallet_address"
   ```

## Examples

### `hyperliquid_data_tester.py`

A comprehensive data testing example that demonstrates:

- **Real-time Market Data**: Live quotes, trades, and order book updates
- **WebSocket Connections**: Direct integration with Hyperliquid's WebSocket API  
- **Instrument Management**: Automatic loading of all available instruments
- **Order Book Management**: L2 book deltas and snapshots with configurable depth
- **Data Validation**: Real-time data feed testing and validation

**Features:**
- 📚 L2 Order Book (real-time deltas and periodic snapshots)
- 💰 Quote Ticks (mid prices from allMids feed) 
- 📈 Trade Ticks (individual trade executions)
- 🔄 Automatic reconnection and error handling
- 📊 Configurable book depth and update intervals

**Usage:**
```bash
cd /path/to/nautilus_trader
python examples/live/hyperliquid/hyperliquid_data_tester.py
```

**Sample Output:**
```
🚀 Starting Hyperliquid Data Tester
⚠️  Using testnet mode for safety  
📊 Testing instrument: BTC-PERP.HYPERLIQUID
💡 Available data feeds:
   📚 L2 Order Book (real-time deltas and snapshots)
   💰 Quote Ticks (mid prices from allMids feed)
   📈 Trade Ticks (individual trades)
🛑 Press CTRL+C to stop
------------------------------------------------------------
2025-01-XX XX:XX:XX.XXX [INFO] Loading Hyperliquid instruments...
2025-01-XX XX:XX:XX.XXX [INFO] 📊 Sending 150 instruments to data engine
2025-01-XX XX:XX:XX.XXX [INFO] Connecting to Hyperliquid WebSocket...
2025-01-XX XX:XX:XX.XXX [INFO] Connected to Hyperliquid WebSocket
2025-01-XX XX:XX:XX.XXX [INFO] 📚 Subscribed to order book for BTC-PERP.HYPERLIQUID
2025-01-XX XX:XX:XX.XXX [INFO] 📊 Subscribed to quotes for BTC-PERP.HYPERLIQUID  
2025-01-XX XX:XX:XX.XXX [INFO] 📈 Subscribed to trades for BTC-PERP.HYPERLIQUID
```

## Configuration Options

### HyperliquidDataClientConfig Parameters

- `private_key`: Wallet private key (optional for public data)
- `wallet_address`: Wallet address (optional for public data)  
- `base_url_http`: Override HTTP API endpoint
- `base_url_ws`: Override WebSocket API endpoint
- `testnet`: Use testnet (True) or mainnet (False)
- `http_timeout_secs`: HTTP request timeout
- `update_instruments_interval_mins`: Instrument refresh interval

### DataTesterConfig Parameters

- `instrument_ids`: List of instruments to test
- `subscribe_book_deltas`: Enable L2 book delta updates
- `subscribe_book_at_interval`: Enable periodic book snapshots
- `subscribe_quotes`: Enable quote tick updates
- `subscribe_trades`: Enable trade tick updates
- `book_interval_ms`: Book snapshot interval in milliseconds
- `book_levels_to_print`: Number of book levels to display
- `manage_book`: Enable order book management
- `use_pyo3_book`: Use optimized PyO3 order book implementation

## Supported Instruments

Hyperliquid currently supports:
- **Perpetual Futures**: BTC-PERP, ETH-PERP, SOL-PERP, etc.
- **Asset Format**: `{SYMBOL}-PERP.HYPERLIQUID`

Common examples:
- `BTC-PERP.HYPERLIQUID` - Bitcoin perpetual futures
- `ETH-PERP.HYPERLIQUID` - Ethereum perpetual futures  
- `SOL-PERP.HYPERLIQUID` - Solana perpetual futures

## Safety Guidelines

1. **Always Test First**: Use testnet mode before mainnet
2. **Start Small**: Begin with minimal position sizes
3. **Monitor Closely**: Watch for connection issues or data anomalies
4. **Environment Variables**: Keep credentials secure and never commit them
5. **Rate Limits**: Respect Hyperliquid's API rate limits

## Troubleshooting

### Common Issues

**Connection Errors:**
```
Failed to connect after retries: connection refused
```
- Check internet connection
- Verify Hyperliquid API status
- Try different WebSocket endpoint

**Authentication Errors:**
```
Invalid credentials or signature
```  
- Verify private key format (64 hex characters)
- Check wallet address format (42 hex characters with 0x prefix)
- Ensure testnet/mainnet mode matches credentials

**No Data Received:**
```
Subscribed but no data coming through
```
- Verify instrument symbol format
- Check WebSocket subscription status
- Ensure proper instrument loading

### Debug Mode

Enable debug logging for more detailed output:
```python
config_node = TradingNodeConfig(
    logging=LoggingConfig(log_level="DEBUG", use_pyo3=True),
    # ... other config
)
```

## Further Development

The data tester serves as a foundation for:
- Strategy development and backtesting preparation
- Market microstructure analysis
- Data feed reliability testing
- Performance benchmarking
- Integration testing

For production trading, extend this example with:
- Risk management rules
- Position sizing logic
- Multi-instrument strategies
- Portfolio management
- Performance monitoring