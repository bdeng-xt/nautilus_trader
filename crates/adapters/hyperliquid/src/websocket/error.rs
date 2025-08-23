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

/// Represents errors that can occur with Hyperliquid WebSocket operations.
#[derive(Error, Debug, Clone)]
pub enum HyperliquidWsError {
    #[error("Connection failed: {0}")]
    ConnectionFailed(String),
    
    #[error("Authentication required for this operation")]
    AuthenticationRequired,
    
    #[error("Failed to serialize message: {0}")]
    SerializationError(String),
    
    #[error("Failed to deserialize message: {0}")]
    DeserializationError(String),
    
    #[error("Failed to send message: {0}")]
    SendError(String),
    
    #[error("Channel error: {0}")]
    ChannelError(String),
    
    #[error("Subscription error: {0}")]
    SubscriptionError(String),
    
    #[error("Protocol error: {0}")]
    ProtocolError(String),
    
    #[error("Unexpected message type: {0}")]
    UnexpectedMessageType(String),
}
