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

use serde::{Deserialize, Serialize};

/// Configuration for Hyperliquid data client
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidDataClientConfig {
    /// Base URL for HTTP API
    pub base_url: String,
    
    /// Base URL for WebSocket API  
    pub ws_base_url: String,
    
    /// Whether to use testnet
    pub testnet: bool,
    
    /// API key (optional for public data)
    pub api_key: Option<String>,
    
    /// API secret (optional for public data)
    pub api_secret: Option<String>,
    
    /// Request timeout in milliseconds
    pub timeout_ms: u64,
    
    /// Rate limit per second
    pub rate_limit_per_second: u32,
    
    /// Heartbeat interval in seconds
    pub heartbeat_interval_secs: u64,
    
    /// Whether to use compression
    pub use_compression: bool,
    
    /// Max retries for failed requests
    pub max_retries: u32,
    
    /// Initial retry delay in milliseconds
    pub retry_delay_ms: u64,
}

impl Default for HyperliquidDataClientConfig {
    fn default() -> Self {
        Self {
            base_url: "https://api.hyperliquid.xyz".to_string(),
            ws_base_url: "wss://api.hyperliquid.xyz/ws".to_string(),
            testnet: false,
            api_key: None,
            api_secret: None,
            timeout_ms: 30_000,
            rate_limit_per_second: 10,
            heartbeat_interval_secs: 30,
            use_compression: false,
            max_retries: 3,
            retry_delay_ms: 1000,
        }
    }
}

/// Configuration for Hyperliquid execution client
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidExecClientConfig {
    /// Base URL for HTTP API
    pub base_url: String,
    
    /// Base URL for WebSocket API
    pub ws_base_url: String,
    
    /// Whether to use testnet
    pub testnet: bool,
    
    /// API key (required for trading)
    pub api_key: String,
    
    /// API secret (required for trading)
    pub api_secret: String,
    
    /// Private key for signing transactions
    pub private_key: Option<String>,
    
    /// Request timeout in milliseconds
    pub timeout_ms: u64,
    
    /// Rate limit per second
    pub rate_limit_per_second: u32,
    
    /// Heartbeat interval in seconds
    pub heartbeat_interval_secs: u64,
    
    /// Whether to use compression
    pub use_compression: bool,
    
    /// Max retries for failed requests
    pub max_retries: u32,
    
    /// Initial retry delay in milliseconds
    pub retry_delay_ms: u64,
    
    /// Maximum retry delay in milliseconds
    pub max_retry_delay_ms: u64,
    
    /// Whether to enable order reconciliation
    pub reconciliation: bool,
    
    /// Reconciliation lookback period in minutes
    pub reconciliation_lookback_mins: u32,
}

impl Default for HyperliquidExecClientConfig {
    fn default() -> Self {
        Self {
            base_url: "https://api.hyperliquid.xyz".to_string(),
            ws_base_url: "wss://api.hyperliquid.xyz/ws".to_string(),
            testnet: false,
            api_key: String::new(),
            api_secret: String::new(),
            private_key: None,
            timeout_ms: 30_000,
            rate_limit_per_second: 5,
            heartbeat_interval_secs: 30,
            use_compression: false,
            max_retries: 3,
            retry_delay_ms: 1000,
            max_retry_delay_ms: 10_000,
            reconciliation: true,
            reconciliation_lookback_mins: 1440, // 24 hours
        }
    }
}

impl HyperliquidDataClientConfig {
    /// Create testnet configuration
    pub fn testnet() -> Self {
        Self {
            base_url: "https://api.hyperliquid-testnet.xyz".to_string(),
            ws_base_url: "wss://api.hyperliquid-testnet.xyz/ws".to_string(),
            testnet: true,
            ..Default::default()
        }
    }
    
    /// Get timeout as Duration
    pub fn timeout(&self) -> Duration {
        Duration::from_millis(self.timeout_ms)
    }
    
    /// Get heartbeat interval as Duration
    pub fn heartbeat_interval(&self) -> Duration {
        Duration::from_secs(self.heartbeat_interval_secs)
    }
}

impl HyperliquidExecClientConfig {
    /// Create testnet configuration
    pub fn testnet() -> Self {
        Self {
            base_url: "https://api.hyperliquid-testnet.xyz".to_string(),
            ws_base_url: "wss://api.hyperliquid-testnet.xyz/ws".to_string(),
            testnet: true,
            ..Default::default()
        }
    }
    
    /// Get timeout as Duration
    pub fn timeout(&self) -> Duration {
        Duration::from_millis(self.timeout_ms)
    }
    
    /// Get heartbeat interval as Duration
    pub fn heartbeat_interval(&self) -> Duration {
        Duration::from_secs(self.heartbeat_interval_secs)
    }
    
    /// Get retry delay as Duration
    pub fn retry_delay(&self) -> Duration {
        Duration::from_millis(self.retry_delay_ms)
    }
    
    /// Get max retry delay as Duration
    pub fn max_retry_delay(&self) -> Duration {
        Duration::from_millis(self.max_retry_delay_ms)
    }
}
