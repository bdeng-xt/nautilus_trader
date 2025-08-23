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
Simple asynchronous example: Hyperliquid WebSocket client for market data.

This is an async version of the simple synchronous example, showing how to use
the synchronous PyO3 bindings in an async context with proper concurrency.
"""

import asyncio
import json
import time
import concurrent.futures

# Hyperliquid PyO3 bindings
try:
    from nautilus_trader.core.nautilus_pyo3.hyperliquid import HyperliquidWebSocketClient
    BINDINGS_AVAILABLE = True
except ImportError:
    print("⚠️  Hyperliquid WebSocket PyO3 bindings not yet available")
    print("📝 This example shows the intended usage pattern")
    BINDINGS_AVAILABLE = False


async def main():
    """Main async function - async version of simple sync example."""
    print("Testing Hyperliquid WebSocket client (async)...")
    
    if not BINDINGS_AVAILABLE:
        print("🔧 Simulating WebSocket client operations...")
        
        # Simulate the same flow as the Rust version
        print("Connecting to WebSocket...")
        await asyncio.sleep(1)  # Simulate connection time
        print("Connected successfully!")
        
        print("Subscribing to BTC trades...")
        await asyncio.sleep(0.1)
        
        print("Subscribing to ETH L2 book...")
        await asyncio.sleep(0.1)
        
        print("Subscribing to all mids...")
        await asyncio.sleep(0.1)
        
        print("Reading messages for 30 seconds...")
        for i in range(10):
            count = i + 1
            if count <= 10:
                message_data = f'{{"channel":"trades","data":[{{"coin":"BTC","px":"45000","sz":"0.1"}}]}}'
                print(f"Message {count}: {message_data}")
            await asyncio.sleep(1)
        
        print("Timeout reached after 30 seconds")
        print("Disconnecting...")
        print("Example completed!")
        return
    
    # Create executor for running sync operations
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    
    try:
        # Create client without credentials (public endpoints only)
        print("Creating client...")
        client = await asyncio.get_event_loop().run_in_executor(
            executor,
            lambda: HyperliquidWebSocketClient(
                url=None,  # Use default URL
                private_key=None,
                wallet_address=None,
                testnet=False
            )
        )
        
        print("Connecting to WebSocket...")
        await asyncio.get_event_loop().run_in_executor(
            executor, client.connect
        )
        
        if client.is_connected():
            print("Connected successfully!")
            
            # Subscribe to BTC trades
            print("Subscribing to BTC trades...")
            await asyncio.get_event_loop().run_in_executor(
                executor, client.subscribe_trades, "BTC"
            )
            
            # Subscribe to ETH L2 book
            print("Subscribing to ETH L2 book...")
            await asyncio.get_event_loop().run_in_executor(
                executor, client.subscribe_l2_book, "ETH"
            )
            
            # Subscribe to all mids
            print("Subscribing to all mids...")
            await asyncio.get_event_loop().run_in_executor(
                executor, client.subscribe_all_mids
            )
            
            # Read messages for 30 seconds
            print("Reading messages for 30 seconds...")
            
            start_time = time.time()
            count = 0
            
            async def read_message_async():
                """Read message in executor."""
                return await asyncio.get_event_loop().run_in_executor(
                    executor, client.read_message
                )
            
            while (time.time() - start_time) < 30:
                try:
                    message = await read_message_async()
                    
                    if message:  # Non-empty message
                        count += 1
                        
                        if count <= 10:
                            # Parse and display first 10 messages
                            try:
                                parsed = json.loads(message)
                                print(f"Message {count}: {parsed}")
                            except json.JSONDecodeError:
                                print(f"Message {count}: {message}")
                        elif count % 100 == 0:
                            print(f"Received {count} messages so far...")
                    else:
                        # No message available, small delay
                        await asyncio.sleep(0.01)
                        
                except Exception as e:
                    print(f"Error reading message: {e}")
                    break
            
            print(f"Timeout reached after 30 seconds")
            print(f"Total messages received: {count}")
            
            print("Disconnecting...")
            await asyncio.get_event_loop().run_in_executor(
                executor, client.disconnect
            )
            
        else:
            print("Failed to connect!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        executor.shutdown(wait=True)


if __name__ == "__main__":
    print("📋 PREREQUISITES:")
    print("1. Build Nautilus Trader with Hyperliquid support:")
    print("   cd /path/to/nautilus_trader")
    print("   make install")
    print()
    print("🚦 Starting simple async WebSocket data example...")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Example terminated by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")