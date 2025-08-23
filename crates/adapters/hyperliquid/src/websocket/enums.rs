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
use strum::{Display, EnumString};

/// Represents the WebSocket channels available on Hyperliquid.
#[derive(Clone, Debug, Display, EnumString, Hash, PartialEq, Eq, Serialize, Deserialize)]
pub enum HyperliquidWsChannel {
    /// Level 2 order book data
    #[serde(rename = "l2Book")]
    #[strum(serialize = "l2Book")]
    L2Book,
    /// Trade data
    #[serde(rename = "trades")]
    #[strum(serialize = "trades")]
    Trades,
    /// All mids (mid prices)
    #[serde(rename = "allMids")]
    #[strum(serialize = "allMids")]
    AllMids,
    /// User notifications
    #[serde(rename = "notification")]
    #[strum(serialize = "notification")]
    Notification,
    /// User order updates
    #[serde(rename = "orderUpdates")]
    #[strum(serialize = "orderUpdates")]
    OrderUpdates,
    /// User-specific events
    #[serde(rename = "userEvents")]
    #[strum(serialize = "userEvents")]
    UserEvents,
}

/// Represents WebSocket operations.
#[derive(Clone, Debug, Display, EnumString, PartialEq, Eq, Serialize, Deserialize)]
#[strum(serialize_all = "lowercase")]
#[serde(rename_all = "lowercase")]
pub enum WsOperation {
    Subscribe,
    Unsubscribe,
}
