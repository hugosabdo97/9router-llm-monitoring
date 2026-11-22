# 9router LLM Gateway Prometheus Exporter & Grafana Dashboard

Comprehensive monitoring setup for **9router LLM Gateway**, tracking request rates, token consumption (prompt vs. completion), cost burn rates, provider distribution, model share, and system health in real-time.

## Dashboard Preview

![9router Grafana Dashboard](assets/grafana-dashboard.jpg)

## Components

1. **`exporter.py`**: A custom Python Prometheus exporter running on port `9109` that queries 9router's SQLite database (`/root/.9router/db/data.sqlite`) and local health/version APIs.
2. **`dashboard.json`**: Fully configured Grafana dashboard compatible with Grafana v7/v8/v9/v10+.
3. **`9router-exporter.service`**: Systemd service unit template to run the exporter persistently in the background.

---

## 📊 Exposed Prometheus Metrics

The exporter (`exporter.py`) collects and exposes the following metrics on port `9109` (`/metrics`):

### 1. System & Service Health
| Metric Name | Type | Description | Labels / Notes |
| :--- | :--- | :--- | :--- |
| `router9_up` | Gauge | 9router API health check status | `1` = UP, `0` = DOWN |
| `router9_version_info` | Gauge | 9router version information | Label: `version="vX.X.X"` |
| `router9_combos_total` | Gauge | Total configured model combos | - |

### 2. Global Usage & Cost Totals
| Metric Name | Type | Description |
| :--- | :--- | :--- |
| `router9_usage_total_requests` | Gauge | Total requests logged in the database |
| `router9_usage_prompt_tokens_total` | Gauge | Total prompt tokens consumed |
| `router9_usage_completion_tokens_total` | Gauge | Total completion tokens consumed |
| `router9_usage_cost_usd_total` | Gauge | Total estimated cost in USD ($) |

### 3. Granular Breakdown Metrics
| Metric Name | Type | Description | Labels |
| :--- | :--- | :--- | :--- |
| `router9_provider_requests_total` | Gauge | Requests per AI provider | `provider` (e.g., `gemini`, `codex`, `github`) |
| `router9_provider_tokens_total` | Gauge | Token consumption per provider | `provider`, `token_type` (`prompt` / `completion`) |
| `router9_model_requests_total` | Gauge | Requests per LLM model | `model` (e.g., `gemini-3.5-flash-lite`, `gpt-5.6-luna`) |
| `router9_status_requests_total` | Gauge | Requests by HTTP/response status | `status` (e.g., `ok`, `error`) |
| `router9_active_connections_total` | Gauge | Active provider connections | `provider` |

---

## 🛠️ Complete Installation & Setup Guide

Follow these steps to deploy the exporter and import the dashboard into your monitoring stack.

### Prerequisites
- Python 3.8+ with `prometheus_client` installed (`pip install prometheus-client`)
- Running 9router instance with SQLite database and API endpoints accessible locally.

---

### Step 1: Clone the Repository
Clone this repository to your monitoring server or 9router host:
```bash
git clone https://github.com/hugosabdo97/9router-llm-monitoring.git
cd 9router-llm-monitoring
```

---

### Step 2: Configure Environment Paths (If Needed)
Open `exporter.py` and adjust the configuration parameters at the top to match your actual 9router environment setup:
```python
# Configuration parameters
# Adjust these paths and ports to match your actual 9router environment setup
PORT = 9109
DB_PATH = "/root/.9router/db/data.sqlite"
HEALTH_URL = "http://127.0.0.1:20128/api/health"
VERSION_URL = "http://127.0.0.1:20128/api/version"
```

---

### Step 3: Run the Exporter Manually (Test)
Test the exporter to ensure it successfully reads the SQLite database and responds on port `9109`:
```bash
python3 exporter.py
```
Verify the metrics output in another terminal or via curl:
```bash
curl -s http://127.0.0.1:9109/metrics | grep router9
```

---

### Step 4: Run as a Persistent Systemd Service
To ensure the exporter runs continuously and restarts automatically on reboot or crashes:

1. Copy the systemd service file to systemd directory:
   ```bash
   cp 9router-exporter.service /etc/systemd/system/9router-exporter.service
   ```
2. Reload systemd daemon and enable/start the service:
   ```bash
   systemctl daemon-reload
   systemctl enable --now 9router-exporter
   ```
3. Check service status:
   ```bash
   systemctl status 9router-exporter
   ```

---

### Step 5: Configure Prometheus Scraping
Add the following scrape job to your Prometheus configuration (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: '9router-gateway'
    static_configs:
      - targets: ['127.0.0.1:9109']
```
Reload Prometheus to apply changes:
```bash
curl -X POST http://127.0.0.1:9090/-/reload
```

---

### Step 6: Import Grafana Dashboard
1. Open your Grafana instance.
2. In the left sidebar, click **Dashboards** -> **Import**.
3. Upload the `dashboard.json` file from this repository (or paste its content).
4. Select your Prometheus data source and click **Import**.
