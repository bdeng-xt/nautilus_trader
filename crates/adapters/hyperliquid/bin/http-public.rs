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

//! Example: Hyperliquid HTTP client public endpoints.
//!
//! This example demonstrates how to use the HTTP client to call public endpoints.

use nautilus_hyperliquid::http::client::HyperliquidHttpClient;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, Layer};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    let stdout_log = tracing_subscriber::fmt::layer()
        .with_target(false)
        .with_filter(tracing_subscriber::filter::filter_fn(|metadata| {
            metadata.target().starts_with("nautilus") || metadata.target().starts_with("hyperliquid")
        }));

    tracing_subscriber::registry().with(stdout_log).init();

    println!("Testing Hyperliquid HTTP client...");

    // Create client without credentials (public endpoints only)
    let client = HyperliquidHttpClient::new(None, None).await?;

    println!("Base URL: {}", client.base_url());
    println!("Is testnet: {}", client.is_testnet());

    // Get instruments
    println!("\nFetching instruments...");
    match client.get_instruments().await {
        Ok(instruments) => {
            println!("Found {} instruments:", instruments.len());
            for (i, instrument) in instruments.iter().take(5).enumerate() {
                println!("  {}. {} (sz_decimals: {})", i + 1, instrument.name, instrument.sz_decimals);
            }
            if instruments.len() > 5 {
                println!("  ... and {} more", instruments.len() - 5);
            }
        }
        Err(e) => {
            println!("Error fetching instruments: {}", e);
        }
    }

    Ok(())
}
