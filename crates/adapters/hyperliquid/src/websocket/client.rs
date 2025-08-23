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

use std::{
    collections::HashMap,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
};

use futures_util::{SinkExt, StreamExt};
use serde_json::json;
use tokio::sync::{Mutex, mpsc};
use tokio_tungstenite::{connect_async, tungstenite::Message, WebSocketStream, MaybeTlsStream};

use nautilus_cryptography::providers::install_cryptographic_provider;

use super::{
    enums::HyperliquidWsChannel,
    error::HyperliquidWsError,
    messages::HyperliquidWsMessage,
};
use crate::{
    common::credentials::HyperliquidCredentials,
};

const HYPERLIQUID_WS_MAINNET_URL: &str = "wss://api.hyperliquid.xyz/ws";
const HYPERLIQUID_WS_TESTNET_URL: &str = "wss://api.hyperliquid-testnet.xyz/ws";

/// Provides a WebSocket client for connecting to Hyperliquid.
#[derive(Debug)]
#[cfg_attr(
    feature = "python",
    pyo3::pyclass(module = "nautilus_trader.core.nautilus_pyo3.adapters")
)]
pub struct HyperliquidWebSocketClient {
    url: String,
    credentials: Option<HyperliquidCredentials>,
    ws_stream: Option<WebSocketStream<MaybeTlsStream<tokio::net::TcpStream>>>,
    message_tx: Option<mpsc::UnboundedSender<HyperliquidWsMessage>>,
    message_rx: Option<mpsc::UnboundedReceiver<HyperliquidWsMessage>>,
    subscriptions: Arc<Mutex<HashMap<HyperliquidWsChannel, Vec<String>>>>,
    is_connected: Arc<AtomicBool>,
    shutdown_signal: Arc<AtomicBool>,
}

impl HyperliquidWebSocketClient {
    /// Creates a new [`HyperliquidWebSocketClient`] instance.
    pub fn new(
        url: Option<String>,
        credentials: Option<HyperliquidCredentials>,
    ) -> anyhow::Result<Self> {
        let testnet = credentials.as_ref().map_or(false, |c| c.testnet);
        let url = url.unwrap_or_else(|| {
            if testnet {
                HYPERLIQUID_WS_TESTNET_URL.to_string()
            } else {
                HYPERLIQUID_WS_MAINNET_URL.to_string()
            }
        });

        let (message_tx, message_rx) = mpsc::unbounded_channel();
        let subscriptions = Arc::new(Mutex::new(HashMap::new()));
        let is_connected = Arc::new(AtomicBool::new(false));
        let shutdown_signal = Arc::new(AtomicBool::new(false));

        Ok(Self {
            url,
            credentials,
            ws_stream: None,
            message_tx: Some(message_tx),
            message_rx: Some(message_rx),
            subscriptions,
            is_connected,
            shutdown_signal,
        })
    }

    /// Check if the client is connected.
    pub fn is_connected(&self) -> bool {
        self.is_connected.load(Ordering::Relaxed)
    }

    /// Get the WebSocket URL.
    pub fn url(&self) -> &str {
        &self.url
    }

    /// Get the credentials.
    pub fn credentials(&self) -> &Option<HyperliquidCredentials> {
        &self.credentials
    }

    /// Connect to the WebSocket.
    pub async fn connect(&mut self) -> Result<(), HyperliquidWsError> {
        // Install crypto provider for TLS connections
        install_cryptographic_provider();
        
        let (ws_stream, _) = connect_async(&self.url).await
            .map_err(|e| HyperliquidWsError::ConnectionFailed(e.to_string()))?;

        self.ws_stream = Some(ws_stream);
        self.is_connected.store(true, Ordering::Relaxed);
        
        tracing::info!("Connected to Hyperliquid WebSocket at {}", self.url);
        Ok(())
    }

    /// Disconnect from the WebSocket.
    pub async fn disconnect(&mut self) -> Result<(), HyperliquidWsError> {
        self.shutdown_signal.store(true, Ordering::Relaxed);
        self.is_connected.store(false, Ordering::Relaxed);
        
        if let Some(mut ws_stream) = self.ws_stream.take() {
            let _ = ws_stream.close(None).await;
        }
        
        tracing::info!("Disconnected from Hyperliquid WebSocket");
        Ok(())
    }

    /// Subscribe to a channel.
    pub async fn subscribe(
        &mut self,
        subscription_type: &str,
        coin: Option<&str>,
        user: Option<&str>,
    ) -> Result<(), HyperliquidWsError> {
        if !self.is_connected() {
            return Err(HyperliquidWsError::ConnectionFailed("Not connected".to_string()));
        }

        let mut subscription = json!({
            "method": "subscribe",
            "subscription": {
                "type": subscription_type
            }
        });

        // Add optional parameters
        if let Some(coin) = coin {
            subscription["subscription"]["coin"] = json!(coin);
        }
        if let Some(user) = user {
            subscription["subscription"]["user"] = json!(user);
        }

        let message = Message::Text(subscription.to_string().into());
        
        if let Some(ws_stream) = &mut self.ws_stream {
            ws_stream.send(message).await
                .map_err(|e| HyperliquidWsError::SendError(e.to_string()))?;
        }

        tracing::info!("Subscribed to {} channel", subscription_type);
        Ok(())
    }

    /// Subscribe to trades for a symbol.
    pub async fn subscribe_trades(&mut self, symbol: &str) -> Result<(), HyperliquidWsError> {
        self.subscribe("trades", Some(symbol), None).await
    }

    /// Subscribe to L2 order book for a symbol.
    pub async fn subscribe_l2_book(&mut self, symbol: &str) -> Result<(), HyperliquidWsError> {
        self.subscribe("l2Book", Some(symbol), None).await
    }

    /// Subscribe to all mids (mid prices).
    pub async fn subscribe_all_mids(&mut self) -> Result<(), HyperliquidWsError> {
        self.subscribe("allMids", None, None).await
    }

    /// Subscribe to user events (requires authentication).
    pub async fn subscribe_user_events(&mut self, user: &str) -> Result<(), HyperliquidWsError> {
        if self.credentials.is_none() {
            return Err(HyperliquidWsError::AuthenticationRequired);
        }
        self.subscribe("userEvents", None, Some(user)).await
    }

    /// Subscribe to user order updates (requires authentication).
    pub async fn subscribe_order_updates(&mut self, user: &str) -> Result<(), HyperliquidWsError> {
        if self.credentials.is_none() {
            return Err(HyperliquidWsError::AuthenticationRequired);
        }
        self.subscribe("orderUpdates", None, Some(user)).await
    }

    /// Subscribe to user notifications (requires authentication).
    pub async fn subscribe_notifications(&mut self, user: &str) -> Result<(), HyperliquidWsError> {
        if self.credentials.is_none() {
            return Err(HyperliquidWsError::AuthenticationRequired);
        }
        self.subscribe("notification", None, Some(user)).await
    }

    /// Read the next message from the WebSocket.
    pub async fn read_message(&mut self) -> Option<Result<HyperliquidWsMessage, HyperliquidWsError>> {
        if let Some(ws_stream) = &mut self.ws_stream {
            match ws_stream.next().await {
                Some(Ok(Message::Text(text))) => {
                    match serde_json::from_str::<HyperliquidWsMessage>(&text) {
                        Ok(msg) => Some(Ok(msg)),
                        Err(e) => {
                            tracing::warn!("Failed to parse WebSocket message: {} - Raw: {}", e, text);
                            Some(Err(HyperliquidWsError::DeserializationError(e.to_string())))
                        }
                    }
                }
                Some(Ok(Message::Ping(payload))) => {
                    // Respond to ping with pong
                    if let Err(e) = ws_stream.send(Message::Pong(payload)).await {
                        tracing::error!("Failed to send pong: {}", e);
                    }
                    None // Continue reading
                }
                Some(Ok(Message::Close(_))) => {
                    tracing::info!("WebSocket connection closed by server");
                    self.is_connected.store(false, Ordering::Relaxed);
                    None
                }
                Some(Err(e)) => {
                    tracing::error!("WebSocket error: {}", e);
                    Some(Err(HyperliquidWsError::ProtocolError(e.to_string())))
                }
                None => {
                    // Stream ended
                    self.is_connected.store(false, Ordering::Relaxed);
                    None
                }
                _ => None, // Other message types we don't handle
            }
        } else {
            None
        }
    }

    /// Run the WebSocket client message loop.
    pub async fn run(&mut self) -> Result<(), HyperliquidWsError> {
        while self.is_connected() && !self.shutdown_signal.load(Ordering::Relaxed) {
            if let Some(result) = self.read_message().await {
                match result {
                    Ok(message) => {
                        // Process the message
                        tracing::debug!("Received WebSocket message: {:?}", message);
                        
                        // Send to message channel if available
                        if let Some(tx) = &self.message_tx {
                            if tx.send(message).is_err() {
                                tracing::error!("Failed to send message to channel");
                                break;
                            }
                        }
                    }
                    Err(e) => {
                        tracing::error!("WebSocket error: {}", e);
                        return Err(e);
                    }
                }
            }
        }
        
        Ok(())
    }

    /// Get a receiver for WebSocket messages.
    pub fn take_message_receiver(&mut self) -> Option<mpsc::UnboundedReceiver<HyperliquidWsMessage>> {
        self.message_rx.take()
    }
}
