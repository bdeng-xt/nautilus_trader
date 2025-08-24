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

use nautilus_core::python::{serialization::to_dict_pyo3, to_pyvalue_err};
use pyo3::{prelude::*, types::PyList};

use crate::{
    http::client::HyperliquidHttpClient,
    common::credentials::HyperliquidCredentials,
};

#[pymethods]
impl HyperliquidHttpClient {
    #[new]
    #[pyo3(signature = (private_key=None, wallet_address=None, testnet=false))]
    fn py_new(
        private_key: Option<String>,
        wallet_address: Option<String>,
        testnet: bool,
    ) -> PyResult<Self> {
        let credentials = if let Some(key) = private_key {
            Some(HyperliquidCredentials::new(key, wallet_address, testnet))
        } else {
            None
        };

        // For now, create a simple sync version
        // In production, this would use tokio::runtime::Handle::current().block_on()
        // or be restructured to be async
        let rt = tokio::runtime::Runtime::new().map_err(to_pyvalue_err)?;
        let client = rt.block_on(async {
            Self::new(credentials, None).await
        }).map_err(to_pyvalue_err)?;
        
        Ok(client)
    }

    #[getter]
    #[pyo3(name = "base_url")]
    #[must_use]
    pub fn py_base_url(&self) -> &str {
        self.base_url()
    }

    #[getter]
    #[pyo3(name = "is_testnet")]
    #[must_use]
    pub fn py_is_testnet(&self) -> bool {
        self.is_testnet()
    }

    /// Get all available instruments.
    #[pyo3(name = "get_instruments")]
    pub fn py_get_instruments(&self) -> PyResult<String> {
        let credentials = self.credentials().clone();
        
        // Use blocking call for simplicity
        let rt = tokio::runtime::Runtime::new().map_err(to_pyvalue_err)?;
        let response = rt.block_on(async {
            let client = Self::new(credentials, None).await?;
            client.get_instruments().await
        }).map_err(to_pyvalue_err)?;

        // Convert to JSON string as expected by the Python provider
        serde_json::to_string(&response).map_err(to_pyvalue_err)
    }

    /// Get user state (balances, positions, etc).
    #[pyo3(name = "get_user_state")]
    pub fn py_get_user_state<'py>(&self, py: Python<'py>, user: &str) -> PyResult<Bound<'py, PyAny>> {
        let credentials = self.credentials().clone();
        
        let rt = tokio::runtime::Runtime::new().map_err(to_pyvalue_err)?;
        let response = rt.block_on(async {
            let client = Self::new(credentials, None).await?;
            client.get_user_state(user).await
        }).map_err(to_pyvalue_err)?;

        to_dict_pyo3(py, &response).map(|dict| dict.into_any().into_bound(py))
    }

    /// Get user's open orders.
    #[pyo3(name = "get_open_orders")]
    pub fn py_get_open_orders<'py>(&self, py: Python<'py>, user: &str) -> PyResult<Bound<'py, PyList>> {
        let credentials = self.credentials().clone();
        
        let rt = tokio::runtime::Runtime::new().map_err(to_pyvalue_err)?;
        let response = rt.block_on(async {
            let client = Self::new(credentials, None).await?;
            client.get_open_orders(user).await
        }).map_err(to_pyvalue_err)?;

        let py_list = PyList::empty(py);
        for order in response {
            let dict = to_dict_pyo3(py, &order)?;
            py_list.append(dict)?;
        }

        Ok(py_list)
    }

    /// Get user's fills (trades).
    #[pyo3(name = "get_user_fills")]
    pub fn py_get_user_fills<'py>(&self, py: Python<'py>, user: &str) -> PyResult<Bound<'py, PyList>> {
        let credentials = self.credentials().clone();
        
        let rt = tokio::runtime::Runtime::new().map_err(to_pyvalue_err)?;
        let response = rt.block_on(async {
            let client = Self::new(credentials, None).await?;
            client.get_user_fills(user).await
        }).map_err(to_pyvalue_err)?;

        let py_list = PyList::empty(py);
        for fill in response {
            let dict = to_dict_pyo3(py, &fill)?;
            py_list.append(dict)?;
        }

        Ok(py_list)
    }

    /// Place an order.
    #[pyo3(name = "place_order")]
    pub fn py_place_order<'py>(
        &self, 
        py: Python<'py>, 
        asset: &str,
        is_buy: bool,
        sz: f64,
        px: f64,
        reduce_only: Option<bool>,
        order_type: Option<&str>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let credentials = self.credentials().clone();
        
        let rt = tokio::runtime::Runtime::new().map_err(to_pyvalue_err)?;
        let response = rt.block_on(async {
            let client = Self::new(credentials, None).await?;
            client.place_order(
                asset, 
                is_buy, 
                sz, 
                px, 
                reduce_only.unwrap_or(false),
                order_type
            ).await
        }).map_err(to_pyvalue_err)?;

        to_dict_pyo3(py, &response).map(|dict| dict.into_any().into_bound(py))
    }

    /// Cancel an order.
    #[pyo3(name = "cancel_order")]
    pub fn py_cancel_order<'py>(
        &self, 
        py: Python<'py>, 
        asset: &str,
        oid: u64,
    ) -> PyResult<Bound<'py, PyAny>> {
        let credentials = self.credentials().clone();
        
        let rt = tokio::runtime::Runtime::new().map_err(to_pyvalue_err)?;
        let response = rt.block_on(async {
            let client = Self::new(credentials, None).await?;
            client.cancel_order(asset, oid).await
        }).map_err(to_pyvalue_err)?;

        to_dict_pyo3(py, &response).map(|dict| dict.into_any().into_bound(py))
    }

    /// Modify an order.
    #[pyo3(name = "modify_order")]
    pub fn py_modify_order<'py>(
        &self, 
        py: Python<'py>, 
        asset: &str,
        oid: u64,
        new_sz: f64,
        new_px: f64,
    ) -> PyResult<Bound<'py, PyAny>> {
        let credentials = self.credentials().clone();
        
        let rt = tokio::runtime::Runtime::new().map_err(to_pyvalue_err)?;
        let response = rt.block_on(async {
            let client = Self::new(credentials, None).await?;
            client.modify_order(asset, oid, new_sz, new_px).await
        }).map_err(to_pyvalue_err)?;

        to_dict_pyo3(py, &response).map(|dict| dict.into_any().into_bound(py))
    }
}
