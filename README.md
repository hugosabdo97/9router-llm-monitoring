# 9router LLM Gateway Prometheus Exporter & Grafana Dashboard

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/hugosabdo97/9router-prometheus-exporter?style=flat-square)](https://github.com/hugosabdo97/9router-prometheus-exporter/releases)
[![GitHub stars](https://img.shields.io/github/stars/hugosabdo97/9router-prometheus-exporter?style=social)](https://github.com/hugosabdo97/9router-prometheus-exporter/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/hugosabdo97/9router-prometheus-exporter?style=social)](https://github.com/hugosabdo97/9router-prometheus-exporter/network/members)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

Real-time monitoring and observability for the **9router LLM Gateway**. This repository bundles a custom Prometheus exporter, a ready-to-import Grafana dashboard, and a systemd unit to keep the exporter running persistently.

## Dashboard Preview

![9router Grafana Dashboard](assets/grafana-dashboard.jpg)

## Components

| File | Purpose |
| :--- | :--- |
| **`exporter.py`** | Python Prometheus exporter on port `9109`. Reads 9router's SQLite database (`/root/.9router/db/data.sqlite`) and polls the local health/version APIs. |
| **`dashboard.json`** | Grafana dashboard in the classic (portable) schema format, importable into any Grafana instance with a Prometheus data source. |
| **`9router-exporter.service`** | Systemd unit template to run the exporter as a persistent background service. |

---

## 📊 Exposed Prometheus Metrics

The exporter collects metrics on a 15-second loop and serves them at `http://<host>:9109/metrics`.

### 1. System & Service Health
| Metric Name | Type | Description | Labels / Notes |
| :--- | :--- | :--- | :--- |
| `router9_up` | Gauge | 9router API health check status | `1` = UP, `0` = DOWN. Drives the "9router Health" stat panel. |
| `router9_version_info` | Gauge | Running 9router version | Label: `version="vX.X.X"` (value always `1`) |
| `router9_combos_total` | Gauge | Number of configured model combos | Feeds the "Active Combos" panel |

### 2. Global Usage & Cost Totals
These are cumulative counters read directly from the `usageHistory` table.

| Metric Name | Type | Description |
| :--- | :--- | :--- |
| `router9_usage_total_requests` | Gauge | Total requests logged in the database |
| `router9_usage_prompt_tokens_total` | Gauge | Total prompt tokens consumed |
| `router9_usage_completion_tokens_total` | Gauge | Total completion tokens consumed |
| `router9_usage_cost_usd_total` | Gauge | Total estimated cost in USD ($) |

> Because these are monotonically increasing counters, the dashboard derives per-second rates from them with `rate(...[5m])` — that is how the token rate, request rate, and cost burn rate panels are built.

### 3. Granular Breakdown Metrics
| Metric Name | Type | Description | Labels |
| :--- | :--- | :--- | :--- |
| `router9_provider_requests_total` | Gauge | Requests per AI provider | `provider` (e.g., `gemini`, `codex`, `github`) |
| `router9_provider_tokens_total` | Gauge | Token consumption per provider | `provider`, `token_type` (`prompt` / `completion`) |
| `router9_model_requests_total` | Gauge | Requests per LLM model | `model` (e.g., `gemini-3.5-flash-lite`, `gpt-5.6-luna`) |
| `router9_status_requests_total` | Gauge | Requests by response status | `status` (e.g., `ok`, `error`) |
| `router9_active_connections_total` | Gauge | Active provider connections | `provider` |

---

## 🖥️ Dashboard Panels

The dashboard contains 13 panels organised into three sections.

### Row 1 — System Status & Overview
| Panel | Type | PromQL |
| :--- | :--- | :--- |
| 9router Health | Stat | `router9_up` |
| Total Requests (Accumulated) | Time series | `router9_usage_total_requests` |
| Estimated Cost ($) | Time series | `router9_usage_cost_usd_total` |
| Active Combos | Time series | `router9_combos_total` |

### Row 2 — Token Consumption & Cost Burn Rate
| Panel | Type | PromQL |
| :--- | :--- | :--- |
| Token Rate (Prompt vs Completion) | Time series | `rate(router9_usage_prompt_tokens_total[5m])`, `rate(router9_usage_completion_tokens_total[5m])` |
| Gateway Request Rate (QPS) | Time series | `rate(router9_usage_total_requests[5m])` |
| Cost Burn Rate ($ / sec) | Time series | `rate(router9_usage_cost_usd_total[5m])` |

### Row 3 — Request Health, Providers & Models
| Panel | Type | PromQL |
| :--- | :--- | :--- |
| Request Status Breakdown (Success / Error) | Time series | `router9_status_requests_total` |
| Requests per Provider | Time series | `router9_provider_requests_total` |
| Model Distribution Share | Pie chart | `router9_model_requests_total` |

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+ with `prometheus_client` (`pip install prometheus-client`)
- A running 9router instance whose SQLite database and API endpoints are reachable from the host

### Step 1: Clone the Repository
```bash
git clone https://github.com/hugosabdo97/9router-prometheus-exporter.git
cd 9router-prometheus-exporter
```

### Step 2: Install Dependencies
```bash
pip install prometheus-client
```

### Step 2: Configure Environment Paths
Edit `exporter.py` and adjust the configuration block at the top to match your 9router setup:
```python
# Configuration parameters
# Adjust these paths and ports to match your actual 9router environment setup
PORT = 9109
DB_PATH = "/root/.9router/db/data.sqlite"
HEALTH_URL = "http://127.0.0.1:20128/api/health"
VERSION_URL = "http://127.0.0.1:20128/api/version"
```

### Step 3: Test the Exporter
```bash
python3 exporter.py
```
Then verify the metrics are being served:
```bash
curl -s http://127.0.0.1:9109/metrics | grep router9
```

### Step 4: Run as a Persistent Systemd Service
```bash
cp 9router-exporter.service /etc/systemd/system/9router-exporter.service
systemctl daemon-reload
systemctl enable --now 9router-exporter
systemctl status 9router-exporter
```

### Step 5: Configure Prometheus Scraping
Add the scrape job to your Prometheus `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: '9router-gateway'
    static_configs:
      - targets: ['127.0.0.1:9109']
```
Then reload Prometheus:
```bash
curl -X POST http://127.0.0.1:9090/-/reload
```

### Step 6: Import the Grafana Dashboard
1. Open Grafana and go to **Dashboards** -> **Import**.
2. Upload `dashboard.json` from this repository.
3. Select your Prometheus data source, then click **Import**.

---

## 🗺️ Roadmap / TODO

### API Key Metrics (planned)

Expose per-API-key usage metrics so quota consumption per client can be tracked.

**1. API key inventory**
- Total number of registered API keys and how many are active.
- Source table: `apiKeys` (`id`, `key`, `name`, `isActive`, `createdAt`, `accessRestricted`).
- Proposed metric: `router9_apikeys{status="active"}` / `router9_apikeys{status="inactive"}`, so `sum(router9_apikeys)` gives the total.

**2. Token usage per API key (rolling 24 hours)**
- Prompt and completion token totals per API key over the last 24 hours.
- Source: `usageHistory` joined to `apiKeys` on `usageHistory.apiKey = apiKeys.key`.
- `usageHistory.apiKey` stores a **masked** key (e.g. `sk-a1a...137d`), while `apiKeys.name` carries the readable label — use `name` as the Prometheus label.
- Proposed metrics: `router9_apikey_prompt_tokens_24h{api_key=...}` and `router9_apikey_completion_tokens_24h{api_key=...}`.

**Implementation notes**
- Timestamps in `usageHistory` are ISO-8601 with a `T` separator (`2026-11-22T03:20:41.853Z`). The 24-hour window filter must use `strftime('%Y-%m-%dT%H:%M:%S','now','-24 hours')` to match that format.
- Avoid a `hour` label on the exported metric — it grows cardinality in Prometheus over time. Export cumulative per-`api_key` values and let Prometheus do the bucketing with `sum by (hour) (rate(...[1h]))`.
- `usageDaily` already stores daily aggregates but has **no** per-API-key dimension, so per-key totals must come from `usageHistory`.
- Scope: additive only (~30 lines) — the existing collection loop, gauges, and HTTP server stay unchanged.

### Error visibility (planned)
- The `Request Status Breakdown` panel currently reads `usageHistory.status`, which only ever contains `ok`. Failed attempts (HTTP 429 quota exhaustion, 400, 502, 503, etc.) are recorded separately in the `requestDetails` table with `status='success'|'error'` and the upstream status code in `response.status`.
- To surface real errors, the exporter needs to query `requestDetails` and expose the upstream status code as a label, and the panel query should switch from the cumulative counter to `rate(...[5m])`.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/hugosabdo97/9router-prometheus-exporter/issues).

## 📝 License
This project is [MIT](LICENSE) licensed.
