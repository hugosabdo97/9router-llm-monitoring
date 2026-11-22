import http.server
import urllib.request
import json
import sqlite3
import time
import threading
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Gauge

# Configuration parameters
# Adjust these paths and ports to match your actual 9router environment setup
PORT = 9109
DB_PATH = "/root/.9router/db/data.sqlite"
HEALTH_URL = "http://127.0.0.1:20128/api/health"
VERSION_URL = "http://127.0.0.1:20128/api/version"

# Prometheus Metrics
g_up = Gauge('router9_up', 'Is 9router service up (health check)')
g_version = Gauge('router9_version_info', '9router version info', ['version'])

# Usage Metrics from DB
g_total_requests = Gauge('router9_usage_total_requests', 'Total requests logged in database')
g_total_prompt_tokens = Gauge('router9_usage_prompt_tokens_total', 'Total prompt tokens consumed')
g_total_completion_tokens = Gauge('router9_usage_completion_tokens_total', 'Total completion tokens consumed')
g_total_cost = Gauge('router9_usage_cost_usd_total', 'Total estimated cost in USD')

g_provider_requests = Gauge('router9_provider_requests_total', 'Requests per provider', ['provider'])
g_provider_tokens = Gauge('router9_provider_tokens_total', 'Tokens per provider', ['provider', 'token_type'])
g_model_requests = Gauge('router9_model_requests_total', 'Requests per model', ['model'])
g_status_requests = Gauge('router9_status_requests_total', 'Requests by status (success/error/etc)', ['status'])
g_active_connections = Gauge('router9_active_connections_total', 'Active provider connections', ['provider'])
g_combos_count = Gauge('router9_combos_total', 'Total configured model combos')

def collect_metrics():
    while True:
        try:
            # 1. Check HTTP Health
            req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "9router-exporter"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                g_up.set(1 if data.get("ok") else 0)
        except Exception:
            g_up.set(0)

        try:
            # 2. Check Version
            req = urllib.request.Request(VERSION_URL, headers={"User-Agent": "9router-exporter"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                ver = data.get("currentVersion", "unknown")
                g_version.clear()
                g_version.labels(version=ver).set(1)
        except Exception:
            pass

        try:
            # 3. Query SQLite DB for granular metrics
            conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Overall totals
            cursor.execute("SELECT count(*), sum(promptTokens), sum(completionTokens), sum(cost) FROM usageHistory;")
            row = cursor.fetchone()
            if row:
                g_total_requests.set(row[0] or 0)
                g_total_prompt_tokens.set(row[1] or 0)
                g_total_completion_tokens.set(row[2] or 0)
                g_total_cost.set(row[3] or 0.0)

            # Per provider stats
            cursor.execute("SELECT provider, count(*), sum(promptTokens), sum(completionTokens) FROM usageHistory GROUP BY provider;")
            for prov, reqs, prompts, comps in cursor.fetchall():
                p_name = prov or "unknown"
                g_provider_requests.labels(provider=p_name).set(reqs or 0)
                g_provider_tokens.labels(provider=p_name, token_type="prompt").set(prompts or 0)
                g_provider_tokens.labels(provider=p_name, token_type="completion").set(comps or 0)

            # Per model stats
            cursor.execute("SELECT model, count(*) FROM usageHistory GROUP BY model;")
            for model, reqs in cursor.fetchall():
                m_name = model or "unknown"
                g_model_requests.labels(model=m_name).set(reqs or 0)

            # Per status stats
            cursor.execute("SELECT status, count(*) FROM usageHistory GROUP BY status;")
            for status, reqs in cursor.fetchall():
                s_name = status or "unknown"
                g_status_requests.labels(status=s_name).set(reqs or 0)

            # Active provider connections
            cursor.execute("SELECT provider, sum(isActive) FROM providerConnections GROUP BY provider;")
            for prov, active in cursor.fetchall():
                p_name = prov or "unknown"
                g_active_connections.labels(provider=p_name).set(active or 0)

            # Combos count
            cursor.execute("SELECT count(*) FROM combos;")
            c_row = cursor.fetchone()
            if c_row:
                g_combos_count.set(c_row[0] or 0)

            conn.close()
        except Exception as e:
            print(f"DB collection error: {e}")

        time.sleep(15)

class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            output = generate_latest()
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.send_header('Content-Length', str(len(output)))
            self.end_headers()
            self.wfile.write(output)
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>9router Prometheus Exporter</h1><p><a href="/metrics">Metrics</a></p></body></html>')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    t = threading.Thread(target=collect_metrics, daemon=True)
    t.start()
    
    server = http.server.HTTPServer(('0.0.0.0', PORT), MetricsHandler)
    print(f"Starting 9router Prometheus exporter on port {PORT}...")
    server.serve_forever()
