# web_server.py (API修正版)

from flask import Flask, render_template, request, jsonify
import json
import os
import logging
import threading
import time
import config
import MetaTrader5 as mt5_api
# analysis_logic は手動分析パネルで使われるのでそのまま
import analysis_logic

logger = logging.getLogger(__name__)

# --- グローバル変数 ---
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'), template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
SETTINGS_FILE = 'settings.json'
settings_lock = threading.Lock()
settings_data = {}
mt5_connector = None

# --- 初期化 ---
def init_app(connector):
    global mt5_connector
    mt5_connector = connector
    logger.info("WebサーバーがMT5コネクタを受け取りました。")

def load_settings():
    global settings_data
    with settings_lock:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                set_default_settings()
        else:
            set_default_settings()
    return settings_data

def set_default_settings():
    global settings_data
    settings_data = {"auto_trading": False, "lot_size": 0.01, "mode": "daytrade"}
    save_settings(settings_data)

def save_settings(data):
    global settings_data
    with settings_lock:
        settings_data.update(data)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)
        return True
load_settings()

# --- APIエンドポイント ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_settings')
def get_settings_api():
    return jsonify(settings_data)

@app.route('/update_settings', methods=['POST'])
def update_settings_api():
    if save_settings(request.get_json()):
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 500

# ★★★★★ ここからが修正箇所 ★★★★★
@app.route('/api/signals')
def get_signals():
    if os.path.exists('signals.json'):
        try:
            with open('signals.json', 'r', encoding='utf-8') as f:
                signals = json.load(f)
                # タイムスタンプの新しい順に並び替える
                sorted_signals = sorted(signals, key=lambda x: x.get('timestamp', ''), reverse=True)
                return jsonify(sorted_signals)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"signals.jsonの読み込みに失敗: {e}")
            return jsonify([])
    return jsonify([])
# ★★★★★ ここまでが修正箇所 ★★★★★

@app.route('/api/logs/<currency_pair>')
def get_logs(currency_pair):
    log_file = os.path.join('logs', f"{currency_pair}_logs.json")
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route('/api/symbols')
def get_symbols():
    # config.pyで定義した順番で返す
    return jsonify(config.SYMBOL_DISPLAY_ORDER)

@app.route('/api/run_analysis', methods=['POST'])
def run_analysis_api():
    if not mt5_connector:
        return jsonify({"status": "error", "message": "MT5 connector not initialized"}), 503

    data = request.get_json()
    symbol = data.get('symbol')
    timeframe_str = data.get('timeframe')

    if not symbol or not timeframe_str:
        return jsonify({"status": "error", "message": "Symbol and timeframe are required"}), 400

    try:
        timeframe_obj = getattr(mt5_api, f'TIMEFRAME_{timeframe_str.upper()}')
        df = mt5_connector.get_candlestick_data(symbol, timeframe_obj, config.CANDLE_COUNT)
        if df.empty:
            return jsonify({"status": "error", "message": "Failed to get candlestick data"}), 500

        sr_levels = analysis_logic.find_support_resistance(df, analysis_logic.DEFAULT_PEAK_DISTANCE)
        trend_lines = analysis_logic.find_trend_lines(df, analysis_logic.DEFAULT_PEAK_DISTANCE)
        fibo_levels = analysis_logic.find_fibonacci_levels(df, analysis_logic.DEFAULT_FIBO_RANGE)
        current_price = df['Close'].iloc[-1]
        predictions = analysis_logic.generate_predictions(current_price, sr_levels, trend_lines, fibo_levels, df)
        
        chart_filepath = analysis_logic.plot_analysis_chart(df, symbol, timeframe_str, sr_levels, trend_lines, fibo_levels, config.CHART_OUTPUT_DIR)
        
        return jsonify({
            "status": "success",
            "current_price": f"{current_price:.3f}",
            "predictions": predictions,
            "image_url": chart_filepath.replace(os.path.sep, '/') + '?t=' + str(time.time())
        })
    except Exception as e:
        logger.error(f"Manual analysis failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

def run_web_ui():
    host = getattr(config, 'WEB_UI_HOST', '0.0.0.0')
    port = getattr(config, 'WEB_UI_PORT', 5000)
    logger.info(f"Web UIを開始しています。アクセス先: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)
