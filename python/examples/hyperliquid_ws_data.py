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

"""
Example: Hyperliquid WebSocket client for market data.

This example demonstrates how to use the WebSocket client to subscribe to market data
using the Python bindings of the Rust WebSocket client.
"""

import asyncio
import json
import logging
import signal
import sys
import time
from typing import Optional

# Hyperliquid PyO3 bindings (when available)
try:
    from nautilus_trader.core.nautilus_pyo3.hyperliquid import HyperliquidWebSocketClient
    BINDINGS_AVAILABLE = True
    print("✅ Hyperliquid WebSocket PyO3 bindings found")
except ImportError:
    print("⚠️  Hyperliquid WebSocket PyO3 bindings not yet available")
    print("📝 This example demonstrates the intended usage pattern")
    BINDINGS_AVAILABLE = False


class HyperliquidWebSocketDataExample:
    """WebSocket market data example using Hyperliquid PyO3 bindings."""
    
    def __init__(self):
        self.client: Optional[HyperliquidWebSocketClient] = None
        self.is_running = False
        self.message_count = 0
        self.start_time = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.is_running = False
        
    async def create_client(self, private_key: str = None, wallet_address: str = None) -> bool:
        """Create and initialize the WebSocket client."""
        if not BINDINGS_AVAILABLE:
            print("🔧 Simulating WebSocket client creation...")
            return True
            
        try:
            print("Creating Hyperliquid WebSocket client...")
            self.client = HyperliquidWebSocketClient(
                url=None,  # Use default URL
                private_key=private_key,
                wallet_address=wallet_address,
                testnet=False  # Use mainnet
            )
            
            auth_status = "authenticated" if private_key else "public only"
            print(f"✅ WebSocket client created ({auth_status})")
            return True
            
        except Exception as e:
            print(f"❌ Error creating WebSocket client: {e}")
            return False
            
    async def connect(self) -> bool:
        """Connect to the Hyperliquid WebSocket."""
        if not BINDINGS_AVAILABLE:
            print("🔌 Simulating WebSocket connection...")
            await asyncio.sleep(1)  # Simulate connection time
            return True
            
        if not self.client:
            print("❌ Client not initialized")
            return False
            
        try:
            print("Connecting to WebSocket...")
            await self.client.connect()
            
            if self.client.is_connected():
                print("✅ Connected successfully!")
                return True
            else:
                print("❌ Failed to connect!")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
            
    async def subscribe_to_feeds(self) -> bool:
        """Subscribe to various market data feeds."""
        if not BINDINGS_AVAILABLE:
            print("📊 Simulating subscriptions...")
            print("   • BTC trades")
            print("   • ETH L2 book")
            print("   • All mids (all symbols)")
            return True
            
        if not self.client or not self.client.is_connected():
            print("❌ Client not connected")
            return False
            
        try:
            # Subscribe to BTC trades
            print("📈 Subscribing to BTC trades...")
            await self.client.subscribe_trades("BTC")
            
            # Subscribe to ETH L2 book
            print("📖 Subscribing to ETH L2 book...")
            await self.client.subscribe_l2_book("ETH")
            
            # Subscribe to all mids
            print("💰 Subscribing to all mids...")
            await self.client.subscribe_all_mids()
            
            print("✅ All subscriptions completed!")
            return True
            
        except Exception as e:
            print(f"❌ Subscription error: {e}")
            return False
            
    async def read_messages(self, duration: int = 30) -> int:
        """Read WebSocket messages for specified duration."""
        if not BINDINGS_AVAILABLE:
            print(f"🌊 Simulating message reading for {duration} seconds...")
            for i in range(min(duration, 10)):
                print(f"📨 Simulated message {i+1}: BTC trade @ $45,000")
                await asyncio.sleep(1)
            return 10
            
        if not self.client or not self.client.is_connected():
            print("❌ Client not connected")
            return 0
            
        print(f"🌊 Reading messages for {duration} seconds...")
        print("📊 Press Ctrl+C to stop early")
        
        self.is_running = True
        self.start_time = time.time()
        self.message_count = 0
        
        try:
            # Use asyncio.wait_for for timeout with graceful shutdown
            await asyncio.wait_for(
                self._message_reading_loop(),
                timeout=duration
            )
        except asyncio.TimeoutError:
            print(f"⏰ Timeout reached after {duration} seconds")
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        
        self.is_running = False
        elapsed = time.time() - (self.start_time or 0)
        print(f"\n📊 Message reading completed: {self.message_count} messages in {elapsed:.1f}s")
        
        return self.message_count
        
    async def _message_reading_loop(self):
        """Main message reading loop."""
        while self.is_running:
            try:
                # Read message from WebSocket
                message = await self.client.read_message()
                
                if message:
                    self.message_count += 1
                    await self._process_message(message)
                    
                # Small delay to prevent tight loop
                await asyncio.sleep(0.001)
                
            except Exception as e:
                print(f"⚠️  Message processing error: {e}")
                await asyncio.sleep(0.1)
                
    async def _process_message(self, message_json: str):
        """Process and display incoming WebSocket message."""
        try:
            message = json.loads(message_json)
            channel = message.get("channel", "unknown")
            data = message.get("data", {})
            
            # Show first 10 messages and periodic updates
            if self.message_count <= 10:
                print(f"📨 Message {self.message_count}: {self._format_message(channel, data)}")
            elif self.message_count % 100 == 0:
                print(f"📊 Received {self.message_count} messages so far...")
                print(f"    Latest: {self._format_message(channel, data)}")
                
        except json.JSONDecodeError:
            print(f"⚠️  Invalid JSON in message {self.message_count}")
        except Exception as e:
            print(f"⚠️  Error processing message {self.message_count}: {e}")
            
    def _format_message(self, channel: str, data) -> str:
        """Format message for display based on channel type."""
        if channel == "trades":
            if isinstance(data, list) and data:
                trade = data[0]
                coin = trade.get("coin", "N/A")
                price = trade.get("px", "N/A")
                size = trade.get("sz", "N/A")
                return f"Trade - {coin} @ ${price} size: {size}"
        elif channel == "l2Book":
            coin = data.get("coin", "N/A")
            levels = data.get("levels", [[], []])
            bids = len(levels[0]) if len(levels) > 0 else 0
            asks = len(levels[1]) if len(levels) > 1 else 0
            return f"L2Book - {coin} ({bids} bids, {asks} asks)"
        elif channel == "allMids":
            mids = data.get("mids", {})
            return f"AllMids - {len(mids)} symbols updated"
        else:
            return f"{channel} - {type(data).__name__}"
            
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if not BINDINGS_AVAILABLE:
            print("🔌 Simulating disconnect...")
            return
            
        if self.client:
            try:
                print("🔌 Disconnecting...")
                await self.client.disconnect()
                print("✅ Disconnected successfully")
            except Exception as e:
                print(f"⚠️  Disconnect error: {e}")
                
    async def run_example(self):
        """Run the complete WebSocket data example."""
        print("🚀 HYPERLIQUID WEBSOCKET DATA EXAMPLE")
        print("=" * 50)
        
        # Configuration
        PRIVATE_KEY = None      # Set for authenticated streams
        WALLET_ADDRESS = None   # Set for user event streams  
        DURATION = 30          # Duration to read messages (seconds)
        
        try:
            # Create client
            if not await self.create_client(PRIVATE_KEY, WALLET_ADDRESS):
                return
                
            # Connect
            if not await self.connect():
                return
                
            # Subscribe to feeds
            if not await self.subscribe_to_feeds():
                return
                
            # Read messages
            message_count = await self.read_messages(DURATION)
            
            if message_count > 0:
                rate = message_count / DURATION if DURATION > 0 else 0
                print(f"📈 Average rate: {rate:.1f} messages/second")
                
            print("\n✅ WebSocket data example completed successfully!")
            
        except KeyboardInterrupt:
            print("\n🛑 Example interrupted by user")
        except Exception as e:
            print(f"\n❌ Example failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            self.is_running = False
            await self.disconnect()


async def main():
    """Main function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Hyperliquid WebSocket Data Example")
    print("Demonstrates market data subscription through PyO3 bindings")
    print()
    
    # Initialize crypto provider (would be done in Rust layer)
    if BINDINGS_AVAILABLE:
        print("🔐 Crypto provider initialized by Rust layer")
    else:
        print("🔐 Would initialize rustls crypto provider")
    
    # Create and run example
    example = HyperliquidWebSocketDataExample()
    await example.run_example()


if __name__ == "__main__":
    print("📋 SETUP INSTRUCTIONS:")
    print("1. Build Nautilus Trader with Hyperliquid support:")
    print("   cd /path/to/nautilus_trader")
    print("   make install")
    print()
    print("2. For authenticated requests (optional):")
    print("   - Set PRIVATE_KEY in the script")
    print("   - Set WALLET_ADDRESS in the script")
    print()
    print("3. For public data only:")
    print("   - Leave credentials as None")
    print()
    print("🚦 Starting WebSocket data example...")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Example terminated by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        print("\n🔧 Troubleshooting:")
        print("- Ensure Hyperliquid WebSocket bindings are available")
        print("- Check internet connection and firewall settings")
        print("- Verify Hyperliquid WebSocket endpoint is accessible")
        sys.exit(1)