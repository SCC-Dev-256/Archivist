# Flask metrics example

## Run
```
python3 -m venv .venv && source .venv/bin/activate
pip install flask prometheus-client
python app.py
```
- Health: http://localhost:5085/healthz
- Metrics: http://localhost:5085/metrics

## Add to Prometheus
```yaml
- job_name: app_metrics
  static_configs:
    - targets: ['127.0.0.1:5085']
```
