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

use thiserror::Error;

/// Represents errors that can occur during Hyperliquid HTTP operations.
#[derive(Error, Debug)]
pub enum HyperliquidHttpError {
    /// Request failed with an error message
    #[error("Request failed: {0}")]
    RequestFailed(String),

    /// Authentication failed
    #[error("Authentication failed: {0}")]
    AuthenticationFailed(String),

    /// Rate limit exceeded
    #[error("Rate limit exceeded: {0}")]
    RateLimitExceeded(String),

    /// Invalid instrument
    #[error("Invalid instrument: {0}")]
    InvalidInstrument(String),

    /// Invalid parameter
    #[error("Invalid parameter: {0}")]
    InvalidParameter(String),

    /// Connection error
    #[error("Connection error: {0}")]
    ConnectionError(String),

    /// Parsing error
    #[error("Parsing error: {0}")]
    ParsingError(String),

    /// Timeout error
    #[error("Request timeout")]
    Timeout,

    /// Unknown error
    #[error("Unknown error: {0}")]
    Unknown(String),
}
