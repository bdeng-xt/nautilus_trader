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

use std::collections::HashMap;
use std::fmt;

use anyhow::Result;
use futures_util::stream::SplitSink;
use futures_util::{SinkExt, StreamExt};
use tokio::net::TcpStream;
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message, MaybeTlsStream, WebSocketStream};
use tracing::{debug, error, info, warn};

use crate::websocket::error::HyperliquidWebSocketError;
use crate::websocket::messages::*;

/// Hyperliquid WebSocket client for real-time data
pub struct HyperliquidWebSocketClient {
    base_url: String,
    sender: Option<SplitSink<WebSocketStream<MaybeTlsStream<TcpStream>>, Message>>,
    subscriptions: HashMap<String, String>,
    message_handler: Option<mpsc::UnboundedSender<HyperliquidWebSocketMessage>>,
}

impl HyperliquidWebSocketClient {
    /// Create a new Hyperliquid WebSocket client
    pub fn new(base_url: String) -> Self {
        Self {
            base_url,
            sender: None,
            subscriptions: HashMap::new(),
            message_handler: None,
        }
    }

    /// Connect to the Hyperliquid WebSocket
    pub async fn connect(&mut self) -> Result<(), HyperliquidWebSocketError> {
        let ws_url = self.base_url.replace("http", "ws") + "/ws";
        info!("Connecting to Hyperliquid WebSocket: {}", ws_url);

        match connect_async(&ws_url).await {
            Ok((ws_stream, _)) => {
                let (sender, mut receiver) = ws_stream.split();
                self.sender = Some(sender);

                // Set up message handling
                let (tx, _rx) = mpsc::unbounded_channel();
                self.message_handler = Some(tx);

                // Create message handler channel
                let message_handler = self.message_handler.clone();
                
                // Spawn message receiver task
                tokio::spawn(async move {
                    while let Some(message) = receiver.next().await {
                        match message {
                            Ok(Message::Text(text)) => {
                                if let Ok(ws_msg) = serde_json::from_str::<HyperliquidWebSocketMessage>(&text) {
                                    if let Some(ref handler) = message_handler {
                                        if let Err(e) = handler.send(ws_msg) {
                                            error!("Failed to send WebSocket message: {}", e);
                                        }
                                    }
                                } else {
                                    warn!("Failed to parse WebSocket message: {}", text);
                                }
                            }
                            Ok(Message::Binary(data)) => {
                                debug!("Received binary WebSocket message: {} bytes", data.len());
                            }
                            Ok(Message::Ping(data)) => {
                                debug!("Received ping: {:?}", data);
                                // Pong will be sent automatically
                            }
                            Ok(Message::Pong(data)) => {
                                debug!("Received pong: {:?}", data);
                            }
                            Ok(Message::Close(frame)) => {
                                info!("WebSocket connection closed: {:?}", frame);
                                break;
                            }
                            Ok(Message::Frame(_)) => {
                                debug!("Received raw frame");
                            }
                            Err(e) => {
                                error!("WebSocket error: {}", e);
                                break;
                            }
                        }
                    }
                });

                info!("Successfully connected to Hyperliquid WebSocket");
                Ok(())
            }
            Err(e) => {
                error!("Failed to connect to Hyperliquid WebSocket: {}", e);
                Err(HyperliquidWebSocketError::ConnectionFailed(e.to_string()))
            }
        }
    }

    /// Subscribe to all mid prices
    pub async fn subscribe_all_mids(&mut self) -> Result<(), HyperliquidWebSocketError> {
        let subscription = HyperliquidSubscription {
            method: "subscribe".to_string(),
            subscription: SubscriptionData {
                subscription_type: "allMids".to_string(),
                coin: None,
                user: None,
            },
        };

        self.send_subscription(&subscription).await?;
        info!("Subscribed to all mid prices");
        Ok(())
    }

    /// Subscribe to trades for a specific coin
    pub async fn subscribe_trades(&mut self, coin: &str) -> Result<(), HyperliquidWebSocketError> {
        let subscription = HyperliquidSubscription {
            method: "subscribe".to_string(),
            subscription: SubscriptionData {
                subscription_type: "trades".to_string(),
                coin: Some(coin.to_string()),
                user: None,
            },
        };

        self.send_subscription(&subscription).await?;
        info!("Subscribed to trades for {}", coin);
        Ok(())
    }

    /// Subscribe to L2 order book for a specific coin
    pub async fn subscribe_l2_book(&mut self, coin: &str) -> Result<(), HyperliquidWebSocketError> {
        let subscription = HyperliquidSubscription {
            method: "subscribe".to_string(),
            subscription: SubscriptionData {
                subscription_type: "l2Book".to_string(),
                coin: Some(coin.to_string()),
                user: None,
            },
        };

        self.send_subscription(&subscription).await?;
        info!("Subscribed to L2 book for {}", coin);
        Ok(())
    }

    /// Subscribe to user events (requires authentication)
    pub async fn subscribe_user_events(&mut self, user: &str) -> Result<(), HyperliquidWebSocketError> {
        let subscription = HyperliquidSubscription {
            method: "subscribe".to_string(),
            subscription: SubscriptionData {
                subscription_type: "userEvents".to_string(),
                coin: None,
                user: Some(user.to_string()),
            },
        };

        self.send_subscription(&subscription).await?;
        info!("Subscribed to user events for {}", user);
        Ok(())
    }

    /// Send a subscription request
    async fn send_subscription(&mut self, subscription: &HyperliquidSubscription) -> Result<(), HyperliquidWebSocketError> {
        if let Some(sender) = &mut self.sender {
            let message = serde_json::to_string(subscription)
                .map_err(|e| HyperliquidWebSocketError::SerializationError(e.to_string()))?;

            sender
                .send(Message::Text(message.into()))
                .await
                .map_err(|e| HyperliquidWebSocketError::SendError(e.to_string()))?;

            debug!("Sent subscription: {:?}", subscription);
            Ok(())
        } else {
            Err(HyperliquidWebSocketError::NotConnected)
        }
    }

    /// Unsubscribe from a specific subscription
    pub async fn unsubscribe(&mut self, subscription_type: &str, coin: Option<&str>) -> Result<(), HyperliquidWebSocketError> {
        let subscription = HyperliquidSubscription {
            method: "unsubscribe".to_string(),
            subscription: SubscriptionData {
                subscription_type: subscription_type.to_string(),
                coin: coin.map(|s| s.to_string()),
                user: None,
            },
        };

        self.send_subscription(&subscription).await?;
        info!("Unsubscribed from {} for {:?}", subscription_type, coin);
        Ok(())
    }

    /// Disconnect from the WebSocket
    pub async fn disconnect(&mut self) -> Result<(), HyperliquidWebSocketError> {
        if let Some(mut sender) = self.sender.take() {
            sender
                .send(Message::Close(None))
                .await
                .map_err(|e| HyperliquidWebSocketError::SendError(e.to_string()))?;
            
            info!("Disconnected from Hyperliquid WebSocket");
            Ok(())
        } else {
            Err(HyperliquidWebSocketError::NotConnected)
        }
    }

    /// Get the message receiver channel
    pub fn get_message_receiver(&self) -> Option<&mpsc::UnboundedSender<HyperliquidWebSocketMessage>> {
        self.message_handler.as_ref()
    }
}

impl fmt::Debug for HyperliquidWebSocketClient {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("HyperliquidWebSocketClient")
            .field("base_url", &self.base_url)
            .field("sender_connected", &self.sender.is_some())
            .field("subscriptions", &self.subscriptions)
            .field("message_handler_connected", &self.message_handler.is_some())
            .finish()
    }
}
