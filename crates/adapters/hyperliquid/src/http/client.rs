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

//! Provides the HTTP client integration for the Hyperliquid API.

use std::{
    num::NonZeroU32,
    sync::LazyLock,
};

use hyperliquid_rust_sdk::InfoClient;
use nautilus_network::{http::HttpClient, ratelimiter::quota::Quota};

use super::{
    error::HyperliquidHttpError,
    models::{HyperliquidInstrument, HyperliquidOrder, HyperliquidFill},
};
use crate::{
    common::{
        consts::{HYPERLIQUID_MAINNET_BASE_URL, HYPERLIQUID_TESTNET_BASE_URL},
        credentials::HyperliquidCredentials,
    },
};

// Rate limiting: Hyperliquid allows 1200 requests per minute (20 per second)
pub static HYPERLIQUID_REST_QUOTA: LazyLock<Quota> =
    LazyLock::new(|| Quota::per_second(NonZeroU32::new(20).unwrap()));

/// Provides a lower-level HTTP client for connecting to the Hyperliquid API.
#[derive(Debug)]
#[cfg_attr(
    feature = "python",
    pyo3::pyclass(module = "nautilus_trader.core.nautilus_pyo3.adapters")
)]
pub struct HyperliquidHttpClient {
    base_url: String,
    client: HttpClient,
    credentials: Option<HyperliquidCredentials>,
}

impl HyperliquidHttpClient {
    /// Create a new [`HyperliquidHttpClient`] instance.
    pub async fn new(
        credentials: Option<HyperliquidCredentials>,
        client: Option<HttpClient>,
    ) -> Result<Self, HyperliquidHttpError> {
        let testnet = credentials.as_ref().map_or(false, |c| c.testnet);
        let base_url = if testnet {
            HYPERLIQUID_TESTNET_BASE_URL.to_string()
        } else {
            HYPERLIQUID_MAINNET_BASE_URL.to_string()
        };

        let http_client = client.unwrap_or_else(|| {
            HttpClient::new(
                std::collections::HashMap::new(), // headers
                Vec::new(),                        // keycloak_audiences
                Vec::new(),                        // rate_limiters
                None,                              // default_quota
                None,                              // timeout_secs
            )
        });

        Ok(Self {
            base_url,
            client: http_client,
            credentials,
        })
    }

    /// Get the base URL for the client.
    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    /// Check if the client is using testnet.
    pub fn is_testnet(&self) -> bool {
        self.credentials.as_ref().map_or(false, |c| c.testnet)
    }

    /// Get the credentials.
    pub fn credentials(&self) -> &Option<HyperliquidCredentials> {
        &self.credentials
    }

    /// Get all available instruments.
    pub async fn get_instruments(&self) -> Result<Vec<HyperliquidInstrument>, HyperliquidHttpError> {
        // Create info client for this request
        let info_client = InfoClient::new(None, None).await
            .map_err(|e| HyperliquidHttpError::RequestFailed(e.to_string()))?;
        
        let meta = info_client.meta().await
            .map_err(|e| HyperliquidHttpError::RequestFailed(e.to_string()))?;
        
        // Convert meta universe to our instrument format
        let mut instruments = Vec::new();
        
        for asset in meta.universe {
            let instrument = HyperliquidInstrument {
                name: asset.name,
                sz_decimals: asset.sz_decimals,
                max_leverage: None, // Not available in AssetMeta
                only_isolate: None, // Not available in AssetMeta
            };
            instruments.push(instrument);
        }

        Ok(instruments)
    }

    /// Get user state (balances, positions, etc).
    pub async fn get_user_state(&self, user_address: &str) -> Result<serde_json::Value, HyperliquidHttpError> {
        let info_client = InfoClient::new(None, None).await
            .map_err(|e| HyperliquidHttpError::RequestFailed(e.to_string()))?;
        
        // Parse address string to H160
        let address = user_address.parse()
            .map_err(|e| HyperliquidHttpError::InvalidResponse(format!("Invalid address: {}", e)))?;
        
        let _state = info_client.user_state(address).await
            .map_err(|e| HyperliquidHttpError::RequestFailed(e.to_string()))?;
        
        // Return as JSON string for now since UserStateResponse doesn't implement Serialize
        Ok(serde_json::json!({
            "status": "success",
            "message": "User state retrieved but not serializable with current SDK"
        }))
    }

    /// Get user's open orders.
    pub async fn get_open_orders(&self, user_address: &str) -> Result<Vec<HyperliquidOrder>, HyperliquidHttpError> {
        let info_client = InfoClient::new(None, None).await
            .map_err(|e| HyperliquidHttpError::RequestFailed(e.to_string()))?;
        
        let address = user_address.parse()
            .map_err(|e| HyperliquidHttpError::InvalidResponse(format!("Invalid address: {}", e)))?;
            
        let orders = info_client.open_orders(address).await
            .map_err(|e| HyperliquidHttpError::RequestFailed(e.to_string()))?;
        
        // Convert to our order format (adjust for actual SDK fields)
        let mut hyperliquid_orders = Vec::new();
        for order in orders {
            let hyperliquid_order = HyperliquidOrder {
                coin: order.coin,
                side: order.side,
                sz: order.sz.clone(),
                px: order.limit_px, // The actual field is limit_px
                oid: order.oid,
                timestamp: order.timestamp,
                orig_sz: order.sz, // Move sz here since it's used again
            };
            hyperliquid_orders.push(hyperliquid_order);
        }

        Ok(hyperliquid_orders)
    }

    /// Get user's fills (trades).
    pub async fn get_user_fills(&self, user_address: &str) -> Result<Vec<HyperliquidFill>, HyperliquidHttpError> {
        let info_client = InfoClient::new(None, None).await
            .map_err(|e| HyperliquidHttpError::RequestFailed(e.to_string()))?;
        
        let address = user_address.parse()
            .map_err(|e| HyperliquidHttpError::InvalidResponse(format!("Invalid address: {}", e)))?;
            
        let fills = info_client.user_fills(address).await
            .map_err(|e| HyperliquidHttpError::RequestFailed(e.to_string()))?;
        
        // Convert to our fill format
        let mut hyperliquid_fills = Vec::new();
        for fill in fills {
            let hyperliquid_fill = HyperliquidFill {
                coin: fill.coin,
                px: fill.px,
                sz: fill.sz,
                side: fill.side,
                time: fill.time,
                start_position: fill.start_position,
                dir: fill.dir,
                closed_pnl: fill.closed_pnl,
                hash: fill.hash,
                oid: fill.oid,
                crossed: fill.crossed,
                fee: fill.fee,
            };
            hyperliquid_fills.push(hyperliquid_fill);
        }

        Ok(hyperliquid_fills)
    }

    /// Place an order (requires exchange client).
    pub async fn place_order(
        &self,
        _asset: &str,
        _is_buy: bool,
        _sz: f64,
        _px: f64,
        _reduce_only: bool,
        _order_type: Option<&str>,
    ) -> Result<serde_json::Value, HyperliquidHttpError> {
        if self.credentials.is_none() {
            return Err(HyperliquidHttpError::AuthenticationRequired);
        }
        
        // TODO: Implement actual order placement using ExchangeClient
        // This requires proper wallet setup with ethers-rs
        Err(HyperliquidHttpError::RequestFailed("Order placement not yet implemented".to_string()))
    }

    /// Cancel an order (requires exchange client).
    pub async fn cancel_order(
        &self,
        _asset: &str,
        _oid: u64,
    ) -> Result<serde_json::Value, HyperliquidHttpError> {
        if self.credentials.is_none() {
            return Err(HyperliquidHttpError::AuthenticationRequired);
        }
        
        // TODO: Implement actual order cancellation
        Err(HyperliquidHttpError::RequestFailed("Order cancellation not yet implemented".to_string()))
    }

    /// Modify an order (requires exchange client).
    pub async fn modify_order(
        &self,
        _asset: &str,
        _oid: u64,
        _new_sz: f64,
        _new_px: f64,
    ) -> Result<serde_json::Value, HyperliquidHttpError> {
        if self.credentials.is_none() {
            return Err(HyperliquidHttpError::AuthenticationRequired);
        }
        
        // TODO: Implement actual order modification
        Err(HyperliquidHttpError::RequestFailed("Order modification not yet implemented".to_string()))
    }
}
