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

/// Represents a WebSocket subscription request to Hyperliquid.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidSubscriptionRequest {
    pub method: String,
    pub subscription: HyperliquidSubscription,
}

/// Represents a subscription payload.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidSubscription {
    #[serde(rename = "type")]
    pub subscription_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coin: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub user: Option<String>,
}

/// Represents a WebSocket message from Hyperliquid.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidWsMessage {
    pub channel: String,
    pub data: serde_json::Value,
}

/// Represents trade data from WebSocket.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidTradeData {
    pub coin: String,
    pub side: String,
    pub px: String,
    pub sz: String,
    pub time: u64,
    pub hash: String,
}

/// Represents L2 book data from WebSocket.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidL2BookData {
    pub coin: String,
    pub levels: Vec<[HyperliquidL2Level; 2]>, // [bids, asks]
    pub time: u64,
}

/// Represents a level in the L2 book.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidL2Level {
    pub px: String,
    pub sz: String,
    pub n: u32,
}

/// Represents all mids data from WebSocket.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidAllMidsData {
    pub mids: std::collections::HashMap<String, String>,
}

/// Represents user notification data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidNotificationData {
    pub notification: String,
    pub time: u64,
}

/// Represents user order update data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidOrderUpdateData {
    pub coin: String,
    pub side: String,
    pub px: String,
    pub sz: String,
    pub oid: u64,
    pub timestamp: u64,
    pub status: String,
}

/// Represents user event data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidUserEventData {
    pub user: String,
    pub event: serde_json::Value,
    pub time: u64,
}
