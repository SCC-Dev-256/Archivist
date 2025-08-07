"""
# PURPOSE: Provide a lightweight monitoring dashboard API used by tests and simple setups
# DEPENDENCIES: Flask, core.monitoring.metrics, core.monitoring.health_checks
# MODIFICATION NOTES: v1.0 - New adapter exposing /, /api/metrics, /api/health endpoints
"""

from __future__ import annotations

from typing import Any, Dict

from flask import Flask, jsonify, render_template_string

from core.monitoring.metrics import get_metrics_collector
from core.monitoring.health_checks import get_health_manager


class MonitoringDashboard:
    """
    # PURPOSE: Minimal dashboard wrapper compatible with existing tests
    # DEPENDENCIES: Flask app, metrics collector, health manager
    # MODIFICATION NOTES: v1.0 - Initial implementation
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8081) -> None:
        self.host = host
        self.port = port

        # Create minimal Flask app with required endpoints
        self.app = Flask(__name__)

        metrics = get_metrics_collector()
        health_manager = get_health_manager()

        @self.app.route("/")
        def index():  # noqa: D401
            """
            # PURPOSE: Simple landing page for sanity checks
            # DEPENDENCIES: None
            # MODIFICATION NOTES: v1.0 - Render inline HTML
            """
            return render_template_string(
                """
<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><title>Monitoring Dashboard</title></head>
  <body>
    <h1>Monitoring Dashboard</h1>
    <ul>
      <li><a href="/api/metrics">/api/metrics</a></li>
      <li><a href="/api/health">/api/health</a></li>
    </ul>
  </body>
</html>
                """
            )

        @self.app.route("/api/metrics")
        def api_metrics():  # noqa: D401
            """
            # PURPOSE: Return summarized metrics for quick inspection
            # DEPENDENCIES: core.monitoring.metrics
            # MODIFICATION NOTES: v1.0 - 1-hour window by default
            """
            summary: Dict[str, Any] = metrics.get_metrics_summary(time_window=3600)
            return jsonify(summary)

        @self.app.route("/api/health")
        def api_health():  # noqa: D401
            """
            # PURPOSE: Return overall health report
            # DEPENDENCIES: core.monitoring.health_checks
            # MODIFICATION NOTES: v1.0 - Pass-through of manager status
            """
            status: Dict[str, Any] = health_manager.get_health_status()
            return jsonify(status)

    def run(self) -> None:
        """
        # PURPOSE: Start the Flask development server (for local use/tests)
        # DEPENDENCIES: Flask
        # MODIFICATION NOTES: v1.0 - Non-debug, threaded
        """
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)


__all__ = ["MonitoringDashboard"]


