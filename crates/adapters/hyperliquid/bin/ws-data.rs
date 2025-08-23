// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

//! Example: Hyperliquid WebSocket client for market data.
//!
//! This example demonstrates how to use the WebSocket client to subscribe to market data.

use std::time::Duration;
use nautilus_hyperliquid::websocket::client::HyperliquidWebSocketClient;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, Layer};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize crypto provider for rustls
    rustls::crypto::aws_lc_rs::default_provider().install_default()
        .map_err(|_| "Failed to install crypto provider")?;

    // Initialize tracing
    let stdout_log = tracing_subscriber::fmt::layer()
        .with_target(false)
        .with_filter(tracing_subscriber::filter::filter_fn(|metadata| {
            metadata.target().starts_with("nautilus") || metadata.target().starts_with("hyperliquid")
        }));

    tracing_subscriber::registry().with(stdout_log).init();

    println!("Testing Hyperliquid WebSocket client...");

    // Create client without credentials (public endpoints only)
    let mut client = HyperliquidWebSocketClient::new(None, None)?;

    println!("Connecting to WebSocket...");
    client.connect().await?;

    if client.is_connected() {
        println!("Connected successfully!");

        // Subscribe to BTC trades
        println!("Subscribing to BTC trades...");
        client.subscribe_trades("BTC").await?;

        // Subscribe to ETH L2 book
        println!("Subscribing to ETH L2 book...");
        client.subscribe_l2_book("ETH").await?;

        // Subscribe to all mids
        println!("Subscribing to all mids...");
        client.subscribe_all_mids().await?;

        // Read messages for 30 seconds
        println!("Reading messages for 30 seconds...");
        let timeout = tokio::time::timeout(Duration::from_secs(30), async {
            let mut count = 0;
            while let Some(result) = client.read_message().await {
                match result {
                    Ok(message) => {
                        count += 1;
                        if count <= 10 {
                            println!("Message {}: {:?}", count, message);
                        } else if count % 100 == 0 {
                            println!("Received {} messages so far...", count);
                        }
                    }
                    Err(e) => {
                        println!("Error: {}", e);
                    }
                }
            }
        }).await;

        match timeout {
            Ok(_) => println!("Message reading completed"),
            Err(_) => println!("Timeout reached after 30 seconds"),
        }

        println!("Disconnecting...");
        client.disconnect().await?;
    } else {
        println!("Failed to connect!");
    }

    Ok(())
}
