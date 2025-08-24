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

use std::sync::{Arc, Mutex, OnceLock};
use tokio::runtime::Runtime;
use nautilus_core::python::to_pyvalue_err;
use nautilus_model::python::data::data_to_pycapsule;
use pyo3::prelude::*;

use crate::{
    websocket::client::HyperliquidWebSocketClient,
    common::credentials::HyperliquidCredentials,
};

// Global runtime for all WebSocket operations
static GLOBAL_RUNTIME: OnceLock<Arc<Mutex<Runtime>>> = OnceLock::new();

fn get_runtime() -> PyResult<Arc<Mutex<Runtime>>> {
    let runtime = GLOBAL_RUNTIME
        .get_or_init(|| {
            Runtime::new()
                .map(|rt| Arc::new(Mutex::new(rt)))
                .unwrap_or_else(|_| panic!("Failed to create Tokio runtime"))
        })
        .clone();
    Ok(runtime)
}

#[pymethods]
impl HyperliquidWebSocketClient {
    #[new]
    #[pyo3(signature = (url=None, private_key=None, wallet_address=None, testnet=false))]
    fn py_new(
        url: Option<String>,
        private_key: Option<String>,
        wallet_address: Option<String>,
        testnet: bool,
    ) -> PyResult<Self> {
        let credentials = if let Some(key) = private_key {
            Some(HyperliquidCredentials::new(key, wallet_address, testnet))
        } else {
            None
        };

        Self::new(url, credentials).map_err(to_pyvalue_err)
    }

    #[pyo3(name = "is_connected")]
    #[must_use]
    pub fn py_is_connected(&self) -> bool {
        self.is_connected()
    }

    /// Connect to the WebSocket.
    #[pyo3(name = "connect")]
    pub fn py_connect(&mut self) -> PyResult<()> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        rt.block_on(async {
            self.connect().await
        }).map_err(to_pyvalue_err)?;
        Ok(())
    }

    /// Disconnect from the WebSocket.
    #[pyo3(name = "disconnect")]
    pub fn py_disconnect(&mut self) -> PyResult<()> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        rt.block_on(async {
            self.disconnect().await
        }).map_err(to_pyvalue_err)?;
        Ok(())
    }

    /// Subscribe to trades for a symbol.
    #[pyo3(name = "subscribe_trades")]
    pub fn py_subscribe_trades(&mut self, symbol: &str) -> PyResult<()> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        rt.block_on(async {
            self.subscribe_trades(symbol).await
        }).map_err(to_pyvalue_err)?;
        Ok(())
    }

    /// Subscribe to L2 order book for a symbol.
    #[pyo3(name = "subscribe_l2_book")]
    pub fn py_subscribe_l2_book(&mut self, symbol: &str) -> PyResult<()> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        rt.block_on(async {
            self.subscribe_l2_book(symbol).await
        }).map_err(to_pyvalue_err)?;
        Ok(())
    }

    /// Subscribe to all mids.
    #[pyo3(name = "subscribe_all_mids")]
    pub fn py_subscribe_all_mids(&mut self) -> PyResult<()> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        rt.block_on(async {
            self.subscribe_all_mids().await
        }).map_err(to_pyvalue_err)?;
        Ok(())
    }

    /// Subscribe to user events (requires authentication).
    #[pyo3(name = "subscribe_user_events")]
    pub fn py_subscribe_user_events(&mut self, user: &str) -> PyResult<()> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        rt.block_on(async {
            self.subscribe_user_events(user).await
        }).map_err(to_pyvalue_err)?;
        Ok(())
    }

    /// Subscribe to user order updates (requires authentication).
    #[pyo3(name = "subscribe_order_updates")]
    pub fn py_subscribe_order_updates(&mut self, user: &str) -> PyResult<()> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        rt.block_on(async {
            self.subscribe_order_updates(user).await
        }).map_err(to_pyvalue_err)?;
        Ok(())
    }

    /// Subscribe to user notifications (requires authentication).
    #[pyo3(name = "subscribe_notifications")]
    pub fn py_subscribe_notifications(&mut self, user: &str) -> PyResult<()> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        rt.block_on(async {
            self.subscribe_notifications(user).await
        }).map_err(to_pyvalue_err)?;
        Ok(())
    }

    /// Read the next message from the WebSocket.
    #[pyo3(name = "read_message")]
    pub fn py_read_message(&mut self) -> PyResult<String> {
        let runtime = get_runtime()?;
        let rt = runtime.lock().map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Runtime lock failed"))?;
        let result = rt.block_on(async {
            self.read_message().await
        });
        
        match result {
            Some(Ok(message)) => Ok(serde_json::to_string(&message).unwrap_or_default()),
            Some(Err(e)) => Err(to_pyvalue_err(e)),
            None => Ok("".to_string()),
        }
    }

    /// Parse a message and convert to Nautilus data objects for callback-based handling.
    #[pyo3(name = "parse_message")]
    pub fn py_parse_message(&self, py: Python, message_json: String) -> PyResult<Option<PyObject>> {
        if let Ok(message) = serde_json::from_str::<serde_json::Map<String, serde_json::Value>>(&message_json) {
            Ok(parse_hyperliquid_message(py, message))
        } else {
            Ok(None)
        }
    }
}

// Helper function for backward compatibility with sync runtime
fn get_runtime_sync() -> PyResult<Arc<Mutex<Runtime>>> {
    let runtime = GLOBAL_RUNTIME
        .get_or_init(|| {
            Runtime::new()
                .map(|rt| Arc::new(Mutex::new(rt)))
                .unwrap_or_else(|_| panic!("Failed to create Tokio runtime"))
        })
        .clone();
    Ok(runtime)
}

// Helper function to call Python callback
pub fn call_python(py: Python, callback: &PyObject, py_obj: PyObject) {
    if let Err(e) = callback.call1(py, (py_obj,)) {
        eprintln!("Error calling Python callback: {e}");
    }
}

// Parse Hyperliquid WebSocket message and convert to Nautilus data objects
fn parse_hyperliquid_message(py: Python, message: serde_json::Map<String, serde_json::Value>) -> Option<PyObject> {
    use nautilus_model::data::QuoteTick;
    use nautilus_model::identifiers::{InstrumentId, Symbol, Venue};
    use nautilus_model::types::{Price, Quantity};
    
    let channel = message.get("channel")?.as_str()?;
    
    match channel {
        "allMids" => {
            let data = message.get("data")?.as_object()?;
            let mids = data.get("mids")?.as_object()?;
            
            // Process first symbol for demonstration (BTC)
            if let Some(btc_price) = mids.get("BTC").and_then(|v| v.as_str()) {
                if let Ok(price) = btc_price.parse::<f64>() {
                    // Create QuoteTick
                    let instrument_id = InstrumentId::new(
                        Symbol::new("BTC-PERP"),
                        Venue::new("HYPERLIQUID")
                    );
                    
                    let price_val = Price::new(price, 1);
                    let zero_qty = Quantity::new(0.0, 0);
                    let ts_init = std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_nanos() as u64;
                    
                    let quote_tick = QuoteTick::new(
                        instrument_id,
                        price_val, // bid_price
                        price_val, // ask_price  
                        zero_qty,  // bid_size
                        zero_qty,  // ask_size
                        ts_init.into(),
                        ts_init.into(),
                    );
                    
                    // Convert to PyObject using capsule
                    return Some(data_to_pycapsule(py, quote_tick.into()));
                }
            }
        }
        _ => {
            // Handle other channels later
        }
    }
    
    None
}
