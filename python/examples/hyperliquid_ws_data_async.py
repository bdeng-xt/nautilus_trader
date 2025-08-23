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
Asynchronous example: Hyperliquid WebSocket client for market data.

This example shows how to use the synchronous Hyperliquid PyO3 bindings
in an asynchronous Python context using asyncio.run_in_executor().
"""

import asyncio
import json
import time
import signal
import sys
import concurrent.futures
from typing import Optional

# Hyperliquid PyO3 bindings
try:
    from nautilus_trader.core.nautilus_pyo3.hyperliquid import HyperliquidWebSocketClient
    BINDINGS_AVAILABLE = True
except ImportError:
    print("⚠️  Hyperliquid WebSocket PyO3 bindings not yet available")
    print("📝 This example shows the intended usage pattern")
    BINDINGS_AVAILABLE = False


class AsyncHyperliquidWebSocketClient:
    """Async wrapper around the synchronous Hyperliquid WebSocket client."""
    
    def __init__(self, url: Optional[str] = None, private_key: Optional[str] = None, 
                 wallet_address: Optional[str] = None, testnet: bool = False):
        self.client: Optional[HyperliquidWebSocketClient] = None
        self.url = url
        self.private_key = private_key  
        self.wallet_address = wallet_address
        self.testnet = testnet
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.is_running = False
        
    async def create_client(self) -> bool:
        """Create the WebSocket client."""
        if not BINDINGS_AVAILABLE:
            print("🔧 Simulating WebSocket client creation...")
            return True
            
        try:
            # Run the synchronous client creation in a thread
            def _create_client():
                return HyperliquidWebSocketClient(
                    url=self.url,
                    private_key=self.private_key,
                    wallet_address=self.wallet_address,
                    testnet=self.testnet
                )
            
            print("Creating Hyperliquid WebSocket client...")
            self.client = await asyncio.get_event_loop().run_in_executor(
                self.executor, _create_client
            )
            
            auth_status = "authenticated" if self.private_key else "public only"
            print(f"✅ WebSocket client created ({auth_status})")
            return True
            
        except Exception as e:
            print(f"❌ Error creating WebSocket client: {e}")
            return False

    async def connect(self) -> bool:
        """Connect to the WebSocket asynchronously."""
        if not BINDINGS_AVAILABLE:
            print("🔌 Simulating WebSocket connection...")
            await asyncio.sleep(1)  # Simulate connection time
            return True
            
        if not self.client:
            print("❌ Client not initialized")
            return False
            
        try:
            print("Connecting to WebSocket...")
            
            # Run the synchronous connect in a thread
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self.client.connect
            )
            
            if self.client.is_connected():
                print("✅ Connected successfully!")
                return True
            else:
                print("❌ Failed to connect!")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    async def subscribe_trades(self, symbol: str) -> bool:
        """Subscribe to trades for a symbol asynchronously."""
        if not BINDINGS_AVAILABLE:
            print(f"📈 Simulating subscribe to {symbol} trades...")
            await asyncio.sleep(0.1)
            return True
            
        if not self.client or not self.client.is_connected():
            print("❌ Client not connected")
            return False
            
        try:
            print(f"📈 Subscribing to {symbol} trades...")
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self.client.subscribe_trades, symbol
            )
            return True
            
        except Exception as e:
            print(f"❌ Error subscribing to trades: {e}")
            return False

    async def subscribe_l2_book(self, symbol: str) -> bool:
        """Subscribe to L2 order book for a symbol asynchronously."""
        if not BINDINGS_AVAILABLE:
            print(f"📖 Simulating subscribe to {symbol} L2 book...")
            await asyncio.sleep(0.1)
            return True
            
        if not self.client or not self.client.is_connected():
            print("❌ Client not connected")
            return False
            
        try:
            print(f"📖 Subscribing to {symbol} L2 book...")
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self.client.subscribe_l2_book, symbol
            )
            return True
            
        except Exception as e:
            print(f"❌ Error subscribing to L2 book: {e}")
            return False

    async def subscribe_all_mids(self) -> bool:
        """Subscribe to all mids asynchronously."""
        if not BINDINGS_AVAILABLE:
            print("💰 Simulating subscribe to all mids...")
            await asyncio.sleep(0.1)
            return True
            
        if not self.client or not self.client.is_connected():
            print("❌ Client not connected")
            return False
            
        try:
            print("💰 Subscribing to all mids...")
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self.client.subscribe_all_mids
            )
            return True
            
        except Exception as e:
            print(f"❌ Error subscribing to all mids: {e}")
            return False

    async def read_message(self) -> Optional[str]:
        """Read the next message from the WebSocket asynchronously."""
        if not BINDINGS_AVAILABLE:
            # Simulate message reading
            await asyncio.sleep(0.01)
            return None
            
        if not self.client or not self.client.is_connected():
            return None
            
        try:
            # Run the synchronous read in a thread
            message = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.client.read_message
            )
            return message if message else None
            
        except Exception as e:
            print(f"❌ Error reading message: {e}")
            return None

    async def read_messages(self, duration: int = 30) -> int:
        """Read WebSocket messages for specified duration asynchronously."""
        if not BINDINGS_AVAILABLE:
            print(f"🌊 Simulating message reading for {duration} seconds...")
            for i in range(min(duration, 10)):
                print(f"📨 Simulated message {i+1}: BTC trade @ $45,000")
                await asyncio.sleep(1)
            return 10
            
        if not self.client or not self.client.is_connected():
            print("❌ Client not connected")
            return 0
            
        print(f"🌊 Reading messages for {duration} seconds asynchronously...")
        print("📊 Press Ctrl+C to stop early")
        
        self.is_running = True
        start_time = time.time()
        count = 0
        
        try:
            while self.is_running and (time.time() - start_time) < duration:
                # Read message asynchronously
                message = await self.read_message()
                
                if message:  # Non-empty message
                    count += 1
                    
                    if count <= 10:
                        # Parse and display first 10 messages
                        try:
                            parsed = json.loads(message)
                            print(f"📨 Message {count}: {self._format_message(parsed)}")
                        except json.JSONDecodeError:
                            print(f"📨 Message {count}: {message[:100]}...")
                    elif count % 100 == 0:
                        print(f"📊 Received {count} messages so far...")
                else:
                    # No message available, small delay
                    await asyncio.sleep(0.01)
                    
        except asyncio.CancelledError:
            print("\n🛑 Message reading cancelled")
        except KeyboardInterrupt:
            print("\n🛑 Message reading interrupted by user")
        
        self.is_running = False
        elapsed = time.time() - start_time
        print(f"\n📊 Message reading completed: {count} messages in {elapsed:.1f}s")
        
        return count

    def _format_message(self, message: dict) -> str:
        """Format message for display based on channel type."""
        channel = message.get("channel", "unknown")
        data = message.get("data", {})
        
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
        """Disconnect from WebSocket asynchronously."""
        if not BINDINGS_AVAILABLE:
            print("🔌 Simulating disconnect...")
            return
            
        if self.client:
            try:
                print("🔌 Disconnecting...")
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, self.client.disconnect
                )
                print("✅ Disconnected successfully")
            except Exception as e:
                print(f"⚠️  Disconnect error: {e}")

    async def cleanup(self):
        """Cleanup resources."""
        self.is_running = False
        await self.disconnect()
        self.executor.shutdown(wait=True)


async def main():
    """Main async function."""
    print("🚀 HYPERLIQUID WEBSOCKET ASYNC EXAMPLE")
    print("=" * 50)
    
    # Configuration
    PRIVATE_KEY = None      # Set for authenticated streams
    WALLET_ADDRESS = None   # Set for user event streams  
    SYMBOLS = ["BTC", "ETH", "SOL"]  # Symbols to subscribe to
    DURATION = 30          # Duration to read messages (seconds)
    
    # Signal handler for graceful shutdown
    client = None
    
    def signal_handler():
        print("\n🛑 Received shutdown signal...")
        if client:
            client.is_running = False
    
    # Set up signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        # Create async client
        client = AsyncHyperliquidWebSocketClient(
            private_key=PRIVATE_KEY,
            wallet_address=WALLET_ADDRESS,
            testnet=False
        )
        
        # Create client
        if not await client.create_client():
            return
            
        # Connect
        if not await client.connect():
            return
            
        # Subscribe to feeds
        await client.subscribe_trades("BTC")
        await client.subscribe_l2_book("ETH")
        await client.subscribe_all_mids()
        
        # Read messages
        message_count = await client.read_messages(DURATION)
        
        if message_count > 0:
            rate = message_count / DURATION if DURATION > 0 else 0
            print(f"📈 Average rate: {rate:.1f} messages/second")
            
        print("\n✅ Async WebSocket example completed successfully!")
        
    except KeyboardInterrupt:
        print("\n🛑 Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if client:
            await client.cleanup()


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
    print("🚦 Starting asynchronous WebSocket example...")
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