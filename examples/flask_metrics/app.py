from flask import Flask, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUESTS = Counter('app_requests_total', 'Total HTTP requests', ['endpoint'])
LATENCY = Histogram('app_request_latency_seconds', 'Request latency', ['endpoint'])

@app.route('/healthz')
def healthz():
    return jsonify(status='ok'), 200

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/demo')
@LATENCY.labels('/demo').time()
def demo():
    REQUESTS.labels('/demo').inc()
    return 'demo ok' , 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5085)
