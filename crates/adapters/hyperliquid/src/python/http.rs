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

//! Python bindings for Hyperliquid HTTP client.

use pyo3::prelude::*;
use pyo3_async_runtimes::tokio::future_into_py;

use crate::common::credentials::HyperliquidCredentials;
use crate::http::client::HyperliquidHttpClient;

#[pymethods]
impl HyperliquidHttpClient {
    /// Create a new Hyperliquid HTTP client.
    #[new]
    #[pyo3(signature = (base_url=None, private_key=None, wallet_address=None, testnet=false))]
    fn py_new(
        base_url: Option<String>,
        private_key: Option<String>,
        wallet_address: Option<String>,
        testnet: bool,
    ) -> PyResult<Self> {
        let credentials = if let Some(key) = private_key {
            Some(HyperliquidCredentials::new(key, wallet_address, testnet))
        } else {
            None
        };

        Self::new(base_url, credentials)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    /// Get market universe (list of available assets).
    #[pyo3(name = "get_universe")]
    fn py_get_universe<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let result = client.get_universe().await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            // Convert to JSON string for Python
            serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Get all market mid prices.
    #[pyo3(name = "get_all_mids")]
    fn py_get_all_mids<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let result = client.get_all_mids().await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Get L2 order book for a specific asset.
    #[pyo3(name = "get_l2_book")]
    fn py_get_l2_book<'py>(&self, py: Python<'py>, coin: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let result = client.get_l2_book(&coin).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Get recent trades for a specific asset.
    #[pyo3(name = "get_recent_trades")]
    fn py_get_recent_trades<'py>(&self, py: Python<'py>, coin: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let result = client.get_recent_trades(&coin).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Place a new order.
    #[pyo3(name = "place_order")]
    fn py_place_order<'py>(&self, py: Python<'py>, order_json: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let order_request: crate::common::models::HyperliquidOrderRequest = 
                serde_json::from_str(&order_json)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            
            let result = client.place_order(&order_request).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
                
            serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Cancel an order.
    #[pyo3(name = "cancel_order")]
    fn py_cancel_order<'py>(&self, py: Python<'py>, cancel_json: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let cancel_request: crate::common::models::HyperliquidCancelOrderRequest = 
                serde_json::from_str(&cancel_json)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            
            let result = client.cancel_order(&cancel_request).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
                
            serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Modify an order.
    #[pyo3(name = "modify_order")]
    fn py_modify_order<'py>(&self, py: Python<'py>, modify_json: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let modify_request: crate::common::models::HyperliquidModifyOrderRequest = 
                serde_json::from_str(&modify_json)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            
            let result = client.modify_order(&modify_request).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
                
            serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Update leverage.
    #[pyo3(name = "update_leverage")]
    fn py_update_leverage<'py>(&self, py: Python<'py>, leverage_json: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let leverage_request: crate::common::models::HyperliquidUpdateLeverageRequest = 
                serde_json::from_str(&leverage_json)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
            
            let result = client.update_leverage(&leverage_request).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
                
            serde_json::to_string(&result)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Get user state (positions, margin).
    #[pyo3(name = "get_user_state")]
    fn py_get_user_state<'py>(&self, py: Python<'py>, user_address: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let user_state = client.get_user_state(&user_address).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            // Convert to JSON string for Python
            serde_json::to_string(&user_state)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Get user portfolio.
    #[pyo3(name = "get_portfolio")]
    fn py_get_portfolio<'py>(&self, py: Python<'py>, user_address: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let portfolio = client.get_portfolio(&user_address).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            serde_json::to_string(&portfolio)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Get user fills.
    #[pyo3(name = "get_user_fills")]
    fn py_get_user_fills<'py>(&self, py: Python<'py>, user_address: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let fills = client.get_user_fills(&user_address).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            serde_json::to_string(&fills)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Get user open orders.
    #[pyo3(name = "get_open_orders")]
    fn py_get_open_orders<'py>(&self, py: Python<'py>, user_address: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let orders = client.get_open_orders(&user_address).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            serde_json::to_string(&orders)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }

    /// Get historical orders.
    #[pyo3(name = "get_historical_orders")]
    fn py_get_historical_orders<'py>(&self, py: Python<'py>, user_address: String) -> PyResult<Bound<'py, PyAny>> {
        let client = self.clone();
        future_into_py(py, async move {
            let orders = client.get_historical_orders(&user_address).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            
            serde_json::to_string(&orders)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        })
    }
}
