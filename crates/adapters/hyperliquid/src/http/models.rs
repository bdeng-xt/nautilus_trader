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

use serde::{Deserialize, Serialize};

// Define our own types based on Hyperliquid API responses

/// Hyperliquid instrument information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidInstrument {
    pub name: String,
    pub sz_decimals: i32,
    pub max_leverage: Option<u32>,
    pub only_isolated: Option<bool>,
}

/// Hyperliquid market data subscription request
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubscriptionRequest {
    pub method: String,
    pub subscription: SubscriptionData,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubscriptionData {
    #[serde(rename = "type")]
    pub subscription_type: String,
    pub coin: Option<String>,
    pub user: Option<String>,
}

/// Hyperliquid WebSocket message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidWsMessage {
    pub channel: String,
    pub data: serde_json::Value,
}

/// Hyperliquid trade data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidTrade {
    pub coin: String,
    pub px: String,
    pub sz: String,
    pub side: String,
    pub time: u64,
    pub hash: String,
}

/// Hyperliquid level 2 order book entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidBookLevel {
    pub px: String,
    pub sz: String,
    pub n: u32,
}

/// Hyperliquid order book data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidOrderBook {
    pub coin: String,
    pub levels: Vec<Vec<HyperliquidBookLevel>>,
    pub time: u64,
}

/// Hyperliquid candle data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidCandle {
    #[serde(rename = "T")]
    pub timestamp: u64,
    #[serde(rename = "c")]
    pub close: String,
    #[serde(rename = "h")]
    pub high: String,
    #[serde(rename = "l")]
    pub low: String,
    #[serde(rename = "n")]
    pub trades: u32,
    #[serde(rename = "o")]
    pub open: String,
    #[serde(rename = "t")]
    pub start_time: u64,
    #[serde(rename = "v")]
    pub volume: String,
}

/// Hyperliquid user fill data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidFill {
    pub coin: String,
    pub px: String,
    pub sz: String,
    pub side: String,
    pub time: u64,
    pub start_position: String,
    pub dir: String,
    pub closed_pnl: String,
    pub hash: String,
    pub oid: u64,
    pub crossed: bool,
    pub fee: String,
    pub liquidation_markup: Option<String>,
}

/// Hyperliquid open order data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidOpenOrder {
    pub coin: String,
    pub limit_px: String,
    pub sz: String,
    pub side: String,
    pub reduce_only: bool,
    pub order_type: String,
    pub origin_tif: String,
    pub tif: String,
    pub timestamp: u64,
    pub oid: u64,
}

/// Hyperliquid position data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidPosition {
    pub coin: String,
    pub entry_px: Option<String>,
    pub leverage: HyperliquidLeverage,
    pub liquidation_px: Option<String>,
    pub margin_used: String,
    pub mark_px: String,
    pub max_leverage: u32,
    pub position_value: String,
    pub return_on_equity: String,
    pub szi: String,
    pub unrealized_pnl: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidLeverage {
    #[serde(rename = "type")]
    pub leverage_type: String,
    pub value: u32,
    pub raw_usd: Option<String>,
}

/// Configuration for Hyperliquid client
#[derive(Debug, Clone)]
pub struct HyperliquidClientConfig {
    pub base_url: String,
    pub testnet: bool,
    pub timeout_ms: u64,
    pub rate_limit_per_second: u32,
}
