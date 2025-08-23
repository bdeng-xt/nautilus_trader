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
use thiserror::Error;

/// Represents errors that can occur with Hyperliquid HTTP requests.
#[derive(Error, Debug, Clone)]
pub enum HyperliquidHttpError {
    #[error("Authentication required for this operation")]
    AuthenticationRequired,
    
    #[error("Request failed: {0}")]
    RequestFailed(String),
    
    #[error("Invalid response format: {0}")]
    InvalidResponse(String),
    
    #[error("Rate limit exceeded")]
    RateLimitExceeded,
    
    #[error("Network error: {0}")]
    NetworkError(String),
    
    #[error("Parsing error: {0}")]
    ParsingError(String),
    
    #[error("Server error: {0}")]
    ServerError(String),
    
    #[error("Client error: {0}")]
    ClientError(String),
}

/// Represents an error response body from Hyperliquid API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperliquidErrorBody {
    pub error: String,
    pub message: Option<String>,
}
