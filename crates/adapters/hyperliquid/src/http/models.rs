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

/// Represents a Hyperliquid instrument.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidInstrument {
    pub name: String,
    pub sz_decimals: u32,
    pub max_leverage: Option<u32>,
    pub only_isolate: Option<bool>,
}

/// Represents a Hyperliquid order.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidOrder {
    pub coin: String,
    pub side: String,
    pub sz: String,
    pub px: String,
    pub oid: u64,
    pub timestamp: u64,
    pub orig_sz: String,
}

/// Represents a Hyperliquid fill (trade execution).
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
}

/// Represents user account state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidUserState {
    pub balances: Vec<HyperliquidBalance>,
    pub margin_summary: HyperliquidMarginSummary,
    pub cross_margin_summary: HyperliquidCrossMarginSummary,
    pub cross_maintenance_margin_used: String,
    pub withdrawable: String,
    pub time: u64,
}

/// Represents a balance for an asset.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidBalance {
    pub coin: String,
    pub hold: String,
    pub total: String,
}

/// Represents margin summary information.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidMarginSummary {
    pub account_value: String,
    pub total_ntl_pos: String,
    pub total_raw_usd: String,
}

/// Represents cross margin summary information.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidCrossMarginSummary {
    pub account_value: String,
    pub total_margin_used: String,
}

/// Represents a position.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidPosition {
    pub coin: String,
    pub entry_px: Option<String>,
    pub leverage: HyperliquidLeverage,
    pub liquidation_px: Option<String>,
    pub margin_used: String,
    pub max_leverage: u32,
    pub position_value: String,
    pub return_on_equity: String,
    pub szi: String,
    pub unrealized_pnl: String,
}

/// Represents leverage information.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidLeverage {
    #[serde(rename = "type")]
    pub leverage_type: String,
    pub value: u32,
}

/// Represents order book data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidL2Book {
    pub coin: String,
    pub levels: Vec<[HyperliquidL2Level; 2]>,
    pub time: u64,
}

/// Represents a level in the order book.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidL2Level {
    pub px: String,
    pub sz: String,
    pub n: u32,
}

/// Represents recent trades data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidRecentTrades {
    pub coin: String,
    pub trades: Vec<HyperliquidTrade>,
}

/// Represents a single trade.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidTrade {
    pub px: String,
    pub sz: String,
    pub side: String,
    pub time: u64,
    pub hash: String,
}
