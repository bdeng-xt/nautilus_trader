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

//! Hyperliquid WebSocket client implementation.

use std::collections::HashMap;
use std::fmt;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use serde_json::Value;
use tokio::sync::mpsc;
use tokio::time::{sleep, Instant};
use tokio_tungstenite::{connect_async, tungstenite::Message, WebSocketStream};

use crate::common::{
    consts::{HYPERLIQUID_WS_URL},
    credentials::HyperliquidCredentials,
    enums::HyperliquidWsChannel,
};

/// Message handler type for WebSocket callbacks.
pub type MessageHandler = Arc<dyn Fn(Value) + Send + Sync>;

/// Hyperliquid WebSocket client.
#[derive(Clone)]
#[cfg_attr(
    feature = "python",
    pyo3::pyclass(module = "nautilus_trader.core.nautilus_pyo3.adapters")
)]
pub struct HyperliquidWebSocketClient {
    url: String,
    credentials: Option<HyperliquidCredentials>,
    subscriptions: Arc<Mutex<HashMap<HyperliquidWsChannel, Vec<String>>>>,
    message_handler: Option<MessageHandler>,
    is_connected: Arc<Mutex<bool>>,
    message_sender: Arc<Mutex<Option<mpsc::UnboundedSender<Message>>>>,
    last_heartbeat: Arc<Mutex<Option<Instant>>>,
    reconnect_attempts: Arc<Mutex<u32>>,
}

impl HyperliquidWebSocketClient {
    /// Create a new Hyperliquid WebSocket client.
    pub fn new(
        url: Option<String>,
        credentials: Option<HyperliquidCredentials>,
    ) -> Result<Self> {
        let url = url.unwrap_or_else(|| HYPERLIQUID_WS_URL.to_string());
        
        Ok(Self {
            url,
            credentials,
            subscriptions: Arc::new(Mutex::new(HashMap::new())),
            message_handler: None,
            is_connected: Arc::new(Mutex::new(false)),
            message_sender: Arc::new(Mutex::new(None)),
            last_heartbeat: Arc::new(Mutex::new(None)),
            reconnect_attempts: Arc::new(Mutex::new(0)),
        })
    }

    /// Set message handler for WebSocket messages.
    pub fn set_message_handler(&mut self, handler: MessageHandler) {
        self.message_handler = Some(handler);
    }

    /// Send a message to the WebSocket.
    fn send_message(&self, message: Message) -> Result<()> {
        if let Some(sender) = self.message_sender.lock().unwrap().as_ref() {
            sender.send(message)?;
            Ok(())
        } else {
            anyhow::bail!("WebSocket not connected")
        }
    }

    /// Connect to the WebSocket.
    pub async fn connect(&mut self) -> Result<()> {
        self.connect_with_retry(3).await
    }

    /// Connect to WebSocket with retry logic.
    pub async fn connect_with_retry(&mut self, max_attempts: u32) -> Result<()> {
        let mut attempts = 0;
        
        while attempts < max_attempts {
            match self.try_connect().await {
                Ok(_) => {
                    *self.reconnect_attempts.lock().unwrap() = 0;
                    return Ok(());
                }
                Err(e) => {
                    attempts += 1;
                    *self.reconnect_attempts.lock().unwrap() = attempts;
                    
                    if attempts < max_attempts {
                        let delay = Duration::from_secs(2_u64.pow(attempts.min(5)));
                        eprintln!("Connection attempt {attempts} failed: {e}. Retrying in {delay:?}...");
                        sleep(delay).await;
                    } else {
                        return Err(e);
                    }
                }
            }
        }
        
        anyhow::bail!("Failed to connect after {max_attempts} attempts")
    }

    /// Try to connect once.
    async fn try_connect(&mut self) -> Result<()> {
        let (ws_stream, _) = connect_async(&self.url).await?;
        *self.is_connected.lock().unwrap() = true;
        *self.last_heartbeat.lock().unwrap() = Some(Instant::now());

        // Create message channel
        let (tx, rx) = mpsc::unbounded_channel();
        *self.message_sender.lock().unwrap() = Some(tx);

        // Spawn message handling task
        if let Some(handler) = self.message_handler.clone() {
            let is_connected = self.is_connected.clone();
            let last_heartbeat = self.last_heartbeat.clone();
            
            tokio::spawn(async move {
                Self::handle_messages(ws_stream, handler, is_connected, last_heartbeat, rx).await;
            });
        }

        // Re-subscribe to all active subscriptions
        self.resubscribe_all().await?;
        
        Ok(())
    }

    /// Resubscribe to all active subscriptions after reconnection.
    async fn resubscribe_all(&mut self) -> Result<()> {
        let subscriptions = {
            let subs = self.subscriptions.lock().unwrap();
            subs.clone()
        };

        for (channel, coins) in subscriptions {
            match channel {
                HyperliquidWsChannel::AllMids => {
                    self.subscribe_all_mids().await?;
                }
                HyperliquidWsChannel::L2Book => {
                    for coin in coins {
                        self.subscribe_l2_book(&coin).await?;
                    }
                }
                HyperliquidWsChannel::Trades => {
                    for coin in coins {
                        self.subscribe_trades(&coin).await?;
                    }
                }
                _ => {} // Handle other channels as needed
            }
        }

        Ok(())
    }

    /// Handle incoming and outgoing WebSocket messages.
    async fn handle_messages(
        ws_stream: WebSocketStream<tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>>,
        handler: MessageHandler,
        is_connected: Arc<Mutex<bool>>,
        last_heartbeat: Arc<Mutex<Option<Instant>>>,
        mut message_receiver: mpsc::UnboundedReceiver<Message>,
    ) {
        let (mut write, mut read) = ws_stream.split();

        loop {
            tokio::select! {
                // Handle incoming messages from WebSocket
                msg = read.next() => {
                    match msg {
                        Some(Ok(Message::Text(text))) => {
                            // Update heartbeat timestamp
                            *last_heartbeat.lock().unwrap() = Some(Instant::now());
                            
                            if let Ok(json_value) = serde_json::from_str::<Value>(&text) {
                                handler(json_value);
                            }
                        }
                        Some(Ok(Message::Ping(data))) => {
                            // Update heartbeat and respond to ping with pong
                            *last_heartbeat.lock().unwrap() = Some(Instant::now());
                            
                            if let Err(e) = write.send(Message::Pong(data)).await {
                                eprintln!("Failed to send pong: {e}");
                                break;
                            }
                        }
                        Some(Ok(Message::Pong(_))) => {
                            // Update heartbeat on pong
                            *last_heartbeat.lock().unwrap() = Some(Instant::now());
                        }
                        Some(Ok(Message::Close(_))) => {
                            break;
                        }
                        Some(Err(e)) => {
                            eprintln!("WebSocket error: {e}");
                            break;
                        }
                        None => break,
                        _ => {}
                    }
                }
                // Handle outgoing messages to WebSocket
                msg = message_receiver.recv() => {
                    match msg {
                        Some(message) => {
                            if let Err(e) = write.send(message).await {
                                eprintln!("Failed to send message: {e}");
                                break;
                            }
                        }
                        None => break,
                    }
                }
                // Check connection status and heartbeat
                _ = tokio::time::sleep(Duration::from_secs(30)) => {
                    if !*is_connected.lock().unwrap() {
                        break;
                    }
                    
                    // Check for heartbeat timeout
                    let last_heartbeat_time = *last_heartbeat.lock().unwrap();
                    if let Some(last) = last_heartbeat_time {
                        if last.elapsed() > Duration::from_secs(60) {
                            eprintln!("Heartbeat timeout detected, closing connection");
                            break;
                        }
                        
                        // Send periodic ping to keep connection alive
                        if last.elapsed() > Duration::from_secs(30) {
                            if let Err(e) = write.send(Message::Ping(vec![].into())).await {
                                eprintln!("Failed to send ping: {e}");
                                break;
                            }
                        }
                    }
                }
            }
        }

        *is_connected.lock().unwrap() = false;
    }

    /// Subscribe to all market mid prices.
    pub async fn subscribe_all_mids(&mut self) -> Result<()> {
        let subscription = serde_json::json!({
            "method": "subscribe",
            "subscription": {
                "type": "allMids"
            }
        });

        // Send subscription message
        let message_text = subscription.to_string();
        self.send_message(Message::Text(message_text.into()))?;

        // Store subscription
        let mut subs = self.subscriptions.lock().unwrap();
        subs.entry(HyperliquidWsChannel::AllMids)
            .or_insert_with(Vec::new);

        Ok(())
    }

    /// Subscribe to L2 book for a specific coin.
    pub async fn subscribe_l2_book(&mut self, coin: &str) -> Result<()> {
        let subscription = serde_json::json!({
            "method": "subscribe",  
            "subscription": {
                "type": "l2Book",
                "coin": coin
            }
        });

        // Send subscription message
        let message_text = subscription.to_string();
        self.send_message(Message::Text(message_text.into()))?;

        // Store subscription
        let mut subs = self.subscriptions.lock().unwrap();
        subs.entry(HyperliquidWsChannel::L2Book)
            .or_insert_with(Vec::new)
            .push(coin.to_string());

        Ok(())
    }

    /// Subscribe to trades for a specific coin.
    pub async fn subscribe_trades(&mut self, coin: &str) -> Result<()> {
        let subscription = serde_json::json!({
            "method": "subscribe",
            "subscription": {
                "type": "trades", 
                "coin": coin
            }
        });

        // Send subscription message
        let message_text = subscription.to_string();
        self.send_message(Message::Text(message_text.into()))?;

        // Store subscription
        let mut subs = self.subscriptions.lock().unwrap();
        subs.entry(HyperliquidWsChannel::Trades)
            .or_insert_with(Vec::new)
            .push(coin.to_string());

        Ok(())
    }

    /// Subscribe to order updates (requires authentication).
    pub async fn subscribe_order_updates(&mut self) -> Result<()> {
        let subscription = serde_json::json!({
            "method": "subscribe",
            "subscription": {
                "type": "orderUpdates"
            }
        });

        // Send subscription message
        let message_text = subscription.to_string();
        self.send_message(Message::Text(message_text.into()))?;

        // Store subscription
        let mut subs = self.subscriptions.lock().unwrap();
        subs.entry(HyperliquidWsChannel::OrderUpdates)
            .or_insert_with(Vec::new);

        Ok(())
    }

    /// Subscribe to user events (fills, liquidations, etc.) (requires authentication).
    pub async fn subscribe_user_events(&mut self) -> Result<()> {
        let subscription = serde_json::json!({
            "method": "subscribe",
            "subscription": {
                "type": "userEvents"
            }
        });

        // Send subscription message
        let message_text = subscription.to_string();
        self.send_message(Message::Text(message_text.into()))?;

        // Store subscription
        let mut subs = self.subscriptions.lock().unwrap();
        subs.entry(HyperliquidWsChannel::UserEvents)
            .or_insert_with(Vec::new);

        Ok(())
    }

    /// Subscribe to notifications (requires authentication).
    pub async fn subscribe_notification(&mut self) -> Result<()> {
        let subscription = serde_json::json!({
            "method": "subscribe",
            "subscription": {
                "type": "notification"
            }
        });

        // Send subscription message
        let message_text = subscription.to_string();
        self.send_message(Message::Text(message_text.into()))?;

        // Store subscription
        let mut subs = self.subscriptions.lock().unwrap();
        subs.entry(HyperliquidWsChannel::Notification)
            .or_insert_with(Vec::new);

        Ok(())
    }

    /// Check if connected.
    pub fn is_connected(&self) -> bool {
        *self.is_connected.lock().unwrap()
    }

    /// Get reconnection attempts count.
    pub fn reconnect_attempts(&self) -> u32 {
        *self.reconnect_attempts.lock().unwrap()
    }

    /// Get time since last heartbeat.
    pub fn time_since_heartbeat(&self) -> Option<Duration> {
        self.last_heartbeat.lock().unwrap().map(|t| t.elapsed())
    }

    /// Disconnect from WebSocket.
    pub async fn disconnect(&mut self) -> Result<()> {
        // Signal disconnect
        *self.is_connected.lock().unwrap() = false;
        
        // Close message sender
        *self.message_sender.lock().unwrap() = None;
        
        // Clear subscriptions
        let mut subs = self.subscriptions.lock().unwrap();
        subs.clear();
        
        Ok(())
    }
}

impl fmt::Debug for HyperliquidWebSocketClient {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("HyperliquidWebSocketClient")
            .field("url", &self.url)
            .field("credentials", &self.credentials)
            .field("subscriptions", &self.subscriptions)
            .field("message_handler", &self.message_handler.is_some())
            .field("is_connected", &self.is_connected)
            .field("has_message_sender", &self.message_sender.lock().unwrap().is_some())
            .field("reconnect_attempts", &self.reconnect_attempts)
            .field("time_since_heartbeat", &self.time_since_heartbeat())
            .finish()
    }
}
