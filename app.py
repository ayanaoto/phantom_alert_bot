# app.py
# Phantom Alert - Minimal Flask backend for Render deploy
# - Serves the UI (templates/index.html)
# - Provides dummy API endpoints used by the frontend
# - Includes a /healthz endpoint for Render health checks
# - Optionally serves /sw.js from /static for Service Worker at the site root

from __future__ import annotations

import os
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List

from flask import (
    Flask,
    render_template,
    send_from_directory,
    jsonify,
    request,
    make_response,
)

# ------------------------------------------------------------------------------
# App Factory (simple global app is fine for this project)
# ------------------------------------------------------------------------------

app = Flask(
    __name__,
    static_url_path="/static",
    static_folder="static",
    template_folder="templates",
)

# Configure logging (Render shows stdout/stderr in the dashboard logs)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("phantom-alert")

# ------------------------------------------------------------------------------
# In-memory demo storage (replace with DB/MT5 integration in production)
# ------------------------------------------------------------------------------

SETTINGS: Dict[str, Any] = {
    "mode": "scalp",          # "scalp" or "daytrade"
    "auto_trading": False,    # bool
    "lot_size": 0.01,         # float >= 0.01
}

SYMBOLS: List[str] = ["USDJPY", "EURUSD", "GOLD", "BTCUSD"]

SIGNALS: List[Dict[str, Any]] = [
    {
        "symbol": "USDJPY",
        "timeframe": "H1",
        "price": 150.123,
        "tp": 150.800,
        "sl": 149.700,
        "signal": "buy",
        "desc": "EMA cross + RSI bounce",
        "image_url": "/static/default_chart.png",
        # timezone-aware UTC timestamp, ISO 8601 with 'Z'
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
]

LOGS: Dict[str, List[Dict[str, str]]] = {
    "USDJPY": [
        {"timestamp": "2025-09-15T01:00:00Z", "message": "Signal BUY detected at 150.123"},
        {"timestamp": "2025-09-15T01:05:00Z", "message": "Alert pushed to LINE/Gmail"},
    ],
    "EURUSD": [],
    "GOLD": [],
    "BTCUSD": [],
}

# ------------------------------------------------------------------------------
# Basic Security/Cache headers (no CSP here to avoid blocking inline scripts)
# ------------------------------------------------------------------------------

@app.after_request
def add_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    # Allow browsers/SW to cache static assets effectively
    if request.path.startswith("/static/"):
        # Adjust max-age as you like; SW handles versioning too
        resp.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    return resp

# ------------------------------------------------------------------------------
# Routes - UI
# ------------------------------------------------------------------------------

@app.route("/")
def index():
    # Renders templates/index.html (frontend bundles all client logic)
    return render_template("index.html")

# Optional: serve SW at site root as /sw.js (index.html currently registers /static/sw.js)
# If you want to register at root, switch the registration to navigator.serviceWorker.register('/sw.js')
@app.route("/sw.js")
def sw_root():
    return send_from_directory("static", "sw.js", mimetype="text/javascript")

# ------------------------------------------------------------------------------
# Health check for Render
# ------------------------------------------------------------------------------

@app.route("/healthz")
def healthz():
    return "ok", 200

# ------------------------------------------------------------------------------
# API - Settings
# ------------------------------------------------------------------------------

@app.route("/get_settings", methods=["GET"])
def get_settings():
    # Return current settings (from memory for demo)
    return jsonify(SETTINGS)

@app.route("/update_settings", methods=["POST"])
def update_settings():
    # Persist settings in memory (in production, store to DB)
    try:
        data = request.get_json(force=True, silent=False) or {}
        mode = str(data.get("mode", SETTINGS["mode"])).strip().lower()
        if mode not in {"scalp", "daytrade"}:
            return jsonify({"status": "error", "message": "Invalid mode"}), 400

        auto_trading = bool(data.get("auto_trading", SETTINGS["auto_trading"]))

        lot_size_raw = data.get("lot_size", SETTINGS["lot_size"])
        try:
            lot_size = float(lot_size_raw)
            if lot_size < 0.01:
                raise ValueError("lot_size must be >= 0.01")
        except Exception:
            return jsonify({"status": "error", "message": "Invalid lot_size"}), 400

        SETTINGS["mode"] = mode
        SETTINGS["auto_trading"] = auto_trading
        SETTINGS["lot_size"] = lot_size

        logger.info("Settings updated: %s", SETTINGS)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.exception("update_settings failed")
        return jsonify({"status": "error", "message": str(e)}), 400

# ------------------------------------------------------------------------------
# API - Symbols / Signals / Logs
# ------------------------------------------------------------------------------

@app.route("/api/symbols", methods=["GET"])
def api_symbols():
    return jsonify(SYMBOLS)

@app.route("/api/signals", methods=["GET"])
def api_signals():
    # In production, fetch the latest signals from your source (e.g., MT5 pipeline)
    # Here we just return the in-memory list
    return jsonify(SIGNALS)

@app.route("/api/logs/<symbol>", methods=["GET"])
def api_logs(symbol: str):
    sy = (symbol or "").upper().strip()
    return jsonify(LOGS.get(sy, []))

# ------------------------------------------------------------------------------
# API - Analysis
# ------------------------------------------------------------------------------

@app.route("/api/run_analysis", methods=["POST"])
def api_run_analysis():
    # Simulate analysis and return a dummy result
    try:
        payload = request.get_json(force=True, silent=False) or {}
        symbol = str(payload.get("symbol") or "USDJPY").upper().strip()
        timeframe = str(payload.get("timeframe") or "H1").upper().strip()

        # Fake current price (in real code, fetch from a price feed)
        current_price = 150.321

        # Fake predictions (replace with your analytics output)
        predictions = [
            f"{symbol} {timeframe}: 押し目買いシナリオ",
            f"{symbol} {timeframe}: 直近高値ブレイク待ち",
            f"{symbol} {timeframe}: 149.90 付近での反発に注意",
        ]

        result = {
            "status": "success",
            "current_price": current_price,
            "predictions": predictions,
            "image_url": "/static/default_chart.png",
        }
        return jsonify(result)
    except Exception as e:
        logger.exception("run_analysis failed")
        return jsonify({"status": "error", "message": str(e)}), 400

# ------------------------------------------------------------------------------
# Error handlers (JSON for /api/* paths)
# ------------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "Not found"}), 404
    # For non-API: serve a minimal 404
    return make_response("Not found", 404)

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    return make_response("Internal server error", 500)

# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # For local development. In Render, Gunicorn will run: gunicorn app:app
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
