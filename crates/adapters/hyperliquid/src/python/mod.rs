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

//! Python bindings from `pyo3`.

use pyo3::prelude::*;

use crate::config::{HyperliquidDataClientConfig, HyperliquidExecClientConfig};

/// Configuration for Hyperliquid data client
#[pyclass]
#[derive(Clone, Debug)]
pub struct PyHyperliquidDataClientConfig {
    pub inner: HyperliquidDataClientConfig,
}

#[pymethods]
impl PyHyperliquidDataClientConfig {
    #[new]
    #[pyo3(signature = (
        base_url = None,
        ws_base_url = None,
        testnet = false,
        api_key = None,
        api_secret = None,
        timeout_ms = 30000,
        rate_limit_per_second = 10,
        heartbeat_interval_secs = 30,
        use_compression = false,
        max_retries = 3,
        retry_delay_ms = 1000,
    ))]
    pub fn new(
        base_url: Option<String>,
        ws_base_url: Option<String>,
        testnet: bool,
        api_key: Option<String>,
        api_secret: Option<String>,
        timeout_ms: u64,
        rate_limit_per_second: u32,
        heartbeat_interval_secs: u64,
        use_compression: bool,
        max_retries: u32,
        retry_delay_ms: u64,
    ) -> Self {
        let mut config = if testnet {
            HyperliquidDataClientConfig::testnet()
        } else {
            HyperliquidDataClientConfig::default()
        };

        if let Some(url) = base_url {
            config.base_url = url;
        }
        if let Some(ws_url) = ws_base_url {
            config.ws_base_url = ws_url;
        }
        config.api_key = api_key;
        config.api_secret = api_secret;
        config.timeout_ms = timeout_ms;
        config.rate_limit_per_second = rate_limit_per_second;
        config.heartbeat_interval_secs = heartbeat_interval_secs;
        config.use_compression = use_compression;
        config.max_retries = max_retries;
        config.retry_delay_ms = retry_delay_ms;

        Self { inner: config }
    }

    #[staticmethod]
    pub fn testnet() -> Self {
        Self {
            inner: HyperliquidDataClientConfig::testnet(),
        }
    }

    #[getter]
    pub fn base_url(&self) -> String {
        self.inner.base_url.clone()
    }

    #[getter]
    pub fn is_testnet(&self) -> bool {
        self.inner.testnet
    }
}

/// Configuration for Hyperliquid execution client
#[pyclass]
#[derive(Clone, Debug)]
pub struct PyHyperliquidExecClientConfig {
    pub inner: HyperliquidExecClientConfig,
}

#[pymethods]
impl PyHyperliquidExecClientConfig {
    #[new]
    #[pyo3(signature = (
        api_key,
        api_secret,
        base_url = None,
        ws_base_url = None,
        testnet = false,
        private_key = None,
        timeout_ms = 30000,
        rate_limit_per_second = 5,
        heartbeat_interval_secs = 30,
        use_compression = false,
        max_retries = 3,
        retry_delay_ms = 1000,
        max_retry_delay_ms = 10000,
        reconciliation = true,
        reconciliation_lookback_mins = 1440,
    ))]
    pub fn new(
        api_key: String,
        api_secret: String,
        base_url: Option<String>,
        ws_base_url: Option<String>,
        testnet: bool,
        private_key: Option<String>,
        timeout_ms: u64,
        rate_limit_per_second: u32,
        heartbeat_interval_secs: u64,
        use_compression: bool,
        max_retries: u32,
        retry_delay_ms: u64,
        max_retry_delay_ms: u64,
        reconciliation: bool,
        reconciliation_lookback_mins: u32,
    ) -> Self {
        let mut config = if testnet {
            HyperliquidExecClientConfig::testnet()
        } else {
            HyperliquidExecClientConfig::default()
        };

        config.api_key = api_key;
        config.api_secret = api_secret;
        if let Some(url) = base_url {
            config.base_url = url;
        }
        if let Some(ws_url) = ws_base_url {
            config.ws_base_url = ws_url;
        }
        config.private_key = private_key;
        config.timeout_ms = timeout_ms;
        config.rate_limit_per_second = rate_limit_per_second;
        config.heartbeat_interval_secs = heartbeat_interval_secs;
        config.use_compression = use_compression;
        config.max_retries = max_retries;
        config.retry_delay_ms = retry_delay_ms;
        config.max_retry_delay_ms = max_retry_delay_ms;
        config.reconciliation = reconciliation;
        config.reconciliation_lookback_mins = reconciliation_lookback_mins;

        Self { inner: config }
    }

    #[staticmethod]
    pub fn testnet() -> Self {
        Self {
            inner: HyperliquidExecClientConfig::testnet(),
        }
    }

    #[getter]
    pub fn base_url(&self) -> String {
        self.inner.base_url.clone()
    }

    #[getter]
    pub fn is_testnet(&self) -> bool {
        self.inner.testnet
    }
}

/// Loaded as `nautilus_pyo3.hyperliquid`.
#[pymodule]
pub fn hyperliquid(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyHyperliquidDataClientConfig>()?;
    m.add_class::<PyHyperliquidExecClientConfig>()?;
    Ok(())
}
