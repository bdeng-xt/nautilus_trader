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

/// Represents errors that can occur during Hyperliquid WebSocket operations.
#[derive(Error, Debug)]
pub enum HyperliquidWebSocketError {
    /// Connection failed
    #[error("Connection failed: {0}")]
    ConnectionFailed(String),

    /// Not connected to WebSocket
    #[error("Not connected to WebSocket")]
    NotConnected,

    /// Failed to send message
    #[error("Failed to send message: {0}")]
    SendError(String),

    /// Failed to receive message
    #[error("Failed to receive message: {0}")]
    ReceiveError(String),

    /// Serialization error
    #[error("Serialization error: {0}")]
    SerializationError(String),

    /// Deserialization error
    #[error("Deserialization error: {0}")]
    DeserializationError(String),

    /// Invalid subscription
    #[error("Invalid subscription: {0}")]
    InvalidSubscription(String),

    /// Authentication error
    #[error("Authentication error: {0}")]
    AuthenticationError(String),

    /// Rate limit error
    #[error("Rate limit exceeded")]
    RateLimitExceeded,

    /// Connection timeout
    #[error("Connection timeout")]
    Timeout,

    /// Unknown error
    #[error("Unknown error: {0}")]
    Unknown(String),
}
