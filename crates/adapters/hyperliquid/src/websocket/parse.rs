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

use super::messages::{
    HyperliquidWsMessage, HyperliquidL2BookData, 
    HyperliquidTradeData, HyperliquidUserEventData
};

/// Parse L2 book WebSocket message.
pub fn parse_l2book_msg(message: &HyperliquidWsMessage) -> Option<String> {
    if let Ok(book_data) = serde_json::from_value::<HyperliquidL2BookData>(message.data.clone()) {
        tracing::debug!("Received L2 book data for {}", book_data.coin);
        return Some(format!("L2Book: {} levels", book_data.levels.len()));
    }
    None
}

/// Parse trades WebSocket message.
pub fn parse_trades_msg(message: &HyperliquidWsMessage) -> Option<String> {
    if let Ok(trades_data) = serde_json::from_value::<Vec<HyperliquidTradeData>>(message.data.clone()) {
        tracing::debug!("Received {} trades", trades_data.len());
        return Some(format!("Trades: {} items", trades_data.len()));
    }
    None
}

/// Parse user events WebSocket message.
pub fn parse_user_events_msg(message: &HyperliquidWsMessage) -> Option<String> {
    if let Ok(user_events) = serde_json::from_value::<Vec<HyperliquidUserEventData>>(message.data.clone()) {
        tracing::debug!("Received {} user events", user_events.len());
        return Some(format!("UserEvents: {} items", user_events.len()));
    }
    None
}
