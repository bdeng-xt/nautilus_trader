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
use serde_json::Value;

/// Hyperliquid WebSocket subscription request
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidSubscription {
    pub method: String,
    pub subscription: SubscriptionData,
}

/// Subscription data for Hyperliquid WebSocket
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubscriptionData {
    #[serde(rename = "type")]
    pub subscription_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coin: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user: Option<String>,
}

/// Hyperliquid WebSocket message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidWebSocketMessage {
    pub channel: String,
    pub data: Value,
}

/// All mid prices message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AllMidsMessage {
    pub mids: std::collections::HashMap<String, String>,
}

/// Trade message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeMessage {
    pub coin: String,
    pub side: String,
    pub px: String,
    pub sz: String,
    pub hash: String,
    pub time: u64,
}

/// L2 order book message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct L2BookMessage {
    pub coin: String,
    pub time: u64,
    pub levels: Vec<Vec<BookLevel>>,
}

/// Order book level
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BookLevel {
    pub px: String,
    pub sz: String,
    pub n: u32,
}

/// User event message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserEventMessage {
    pub user: String,
    pub data: UserEventData,
}

/// User event data
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum UserEventData {
    #[serde(rename = "fill")]
    Fill {
        coin: String,
        px: String,
        sz: String,
        side: String,
        time: u64,
        start_position: String,
        dir: String,
        closed_pnl: String,
        hash: String,
        oid: u64,
        crossed: bool,
        fee: String,
    },
    #[serde(rename = "order")]
    Order {
        coin: String,
        limit_px: String,
        sz: String,
        side: String,
        reduce_only: bool,
        order_type: String,
        origin_tif: String,
        tif: String,
        timestamp: u64,
        oid: u64,
    },
    #[serde(rename = "ws_user_events")]
    WsUserEvents {
        fills: Vec<Value>,
        liquidations: Vec<Value>,
        non_user_cancel: Vec<Value>,
    },
}

/// Funding message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FundingMessage {
    pub coin: String,
    pub funding_rate: String,
    pub premium: String,
    pub time: u64,
}

/// Notification message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationMessage {
    pub notification: String,
}

/// Error message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorMessage {
    pub error: String,
    pub id: Option<String>,
}
