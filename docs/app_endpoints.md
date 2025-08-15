# Application Endpoints for Monitoring

## /healthz (HTTP 200)
Implement a lightweight health endpoint in the web API that returns 200 OK when core dependencies are healthy.

Example (Flask):
```python
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/healthz')
def healthz():
    # Optionally verify Redis/PG/Celery here
    return jsonify(status='ok'), 200
```
Expose internally (e.g., 127.0.0.1:85/healthz) or through your reverse proxy. Prometheus probes it via blackbox_exporter.

## /metrics (Prometheus format)
Expose default and application metrics for Prometheus.

Option A: prometheus_client
```python
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from flask import Response

REQUESTS = Counter('app_requests_total', 'App requests', ['endpoint'])

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
```

Option B: prometheus_flask_exporter
```python
from prometheus_flask_exporter import PrometheusMetrics
metrics = PrometheusMetrics(app)
```

After enabling, add the web app target to Prometheus (`job_name: app_metrics`).
