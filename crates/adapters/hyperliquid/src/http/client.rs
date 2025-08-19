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

use std::time::Duration;

use anyhow::Result;
use reqwest::Client;
use serde_json::Value;
use tracing::{debug, error};

use crate::http::error::HyperliquidHttpError;

/// HTTP client for Hyperliquid API
#[derive(Debug)]
pub struct HyperliquidHttpClient {
    client: Client,
    base_url: String,
    _timeout: Duration,
}

impl HyperliquidHttpClient {
    /// Create a new Hyperliquid HTTP client
    pub fn new(
        base_url: String,
        timeout: Option<Duration>,
    ) -> Result<Self> {
        let timeout = timeout.unwrap_or(Duration::from_secs(30));
        
        // Create the reqwest client
        let client = Client::builder()
            .timeout(timeout)
            .build()?;

        Ok(Self {
            client,
            base_url,
            _timeout: timeout,
        })
    }

    /// Get market metadata
    pub async fn get_meta(&self) -> Result<Value, HyperliquidHttpError> {
        debug!("Fetching market metadata");
        
        let request_body = serde_json::json!({
            "type": "meta"
        });
        
        match self.client
            .post(&format!("{}/info", self.base_url))
            .json(&request_body)
            .send()
            .await
        {
            Ok(response) => {
                if response.status().is_success() {
                    match response.json::<Value>().await {
                        Ok(data) => {
                            debug!("Successfully fetched market metadata");
                            Ok(data)
                        }
                        Err(e) => {
                            error!("Failed to parse metadata response: {}", e);
                            Err(HyperliquidHttpError::ParsingError(e.to_string()))
                        }
                    }
                } else {
                    error!("HTTP error fetching metadata: {}", response.status());
                    Err(HyperliquidHttpError::RequestFailed(format!(
                        "HTTP error: {}",
                        response.status()
                    )))
                }
            }
            Err(e) => {
                error!("Failed to fetch market metadata: {}", e);
                Err(HyperliquidHttpError::RequestFailed(e.to_string()))
            }
        }
    }

    /// Get all mid prices
    pub async fn get_all_mids(&self) -> Result<Value, HyperliquidHttpError> {
        debug!("Fetching all mid prices");
        
        let request_body = serde_json::json!({
            "type": "allMids"
        });
        
        self.make_request(request_body).await
    }

    /// Get L2 order book snapshot
    pub async fn get_l2_snapshot(&self, coin: &str) -> Result<Value, HyperliquidHttpError> {
        debug!("Fetching L2 snapshot for {}", coin);
        
        let request_body = serde_json::json!({
            "type": "l2Book",
            "coin": coin
        });
        
        self.make_request(request_body).await
    }

    /// Get recent trades
    pub async fn get_recent_trades(&self, coin: &str) -> Result<Value, HyperliquidHttpError> {
        debug!("Fetching recent trades for {}", coin);
        
        let request_body = serde_json::json!({
            "type": "recentTrades",
            "coin": coin
        });
        
        self.make_request(request_body).await
    }

    /// Get candlestick data
    pub async fn get_candles(
        &self,
        coin: &str,
        interval: &str,
        start_time: Option<u64>,
        end_time: Option<u64>,
    ) -> Result<Value, HyperliquidHttpError> {
        debug!("Fetching candles for {} with interval {}", coin, interval);
        
        let mut request_body = serde_json::json!({
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval
            }
        });
        
        if let Some(start) = start_time {
            request_body["req"]["startTime"] = serde_json::json!(start);
        }
        
        if let Some(end) = end_time {
            request_body["req"]["endTime"] = serde_json::json!(end);
        }
        
        self.make_request(request_body).await
    }

    /// Get user's open orders (requires authentication)
    pub async fn get_open_orders(&self, address: &str) -> Result<Value, HyperliquidHttpError> {
        debug!("Fetching open orders for address {}", address);
        
        let request_body = serde_json::json!({
            "type": "openOrders",
            "user": address
        });
        
        self.make_request(request_body).await
    }

    /// Get user's trade fills (requires authentication)
    pub async fn get_user_fills(&self, address: &str) -> Result<Value, HyperliquidHttpError> {
        debug!("Fetching user fills for address {}", address);
        
        let request_body = serde_json::json!({
            "type": "userFills",
            "user": address
        });
        
        self.make_request(request_body).await
    }

    /// Make a request to the Hyperliquid info API
    async fn make_request(&self, request_body: Value) -> Result<Value, HyperliquidHttpError> {
        match self.client
            .post(&format!("{}/info", self.base_url))
            .json(&request_body)
            .send()
            .await
        {
            Ok(response) => {
                if response.status().is_success() {
                    match response.json::<Value>().await {
                        Ok(data) => Ok(data),
                        Err(e) => {
                            error!("Failed to parse response: {}", e);
                            Err(HyperliquidHttpError::ParsingError(e.to_string()))
                        }
                    }
                } else {
                    error!("HTTP error: {}", response.status());
                    Err(HyperliquidHttpError::RequestFailed(format!(
                        "HTTP error: {}",
                        response.status()
                    )))
                }
            }
            Err(e) => {
                error!("Request failed: {}", e);
                Err(HyperliquidHttpError::RequestFailed(e.to_string()))
            }
        }
    }
}
