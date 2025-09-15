# C:\Users\pc\OneDrive\Desktop\phantom_alert_bot\config.py (修正版)

import os
import logging

# --- 1. ロギング設定 ---
LOG_LEVEL = logging.INFO
LOG_FILE = "app.log"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# --- 2. MT5 接続設定 ---
MT5_PATH = r"C:\Program Files\XMTrading MT5\terminal64.exe"
MT5_LOGIN = 75312449
MT5_PASSWORD = "Kk*qS2Bq" 
MT5_SERVER = "XMTrading-MT5 3"

# --- 3. 時間足ごとの監視間隔（秒） ---
SIGNAL_INTERVALS_SECONDS = {
    "M1": 60, "M5": 300, "M15": 900, "H1": 3600, "D1": 86400
}

# --- 4. シグナル監視設定 ---
CANDLE_COUNT = 300
SIGNAL_COOLDOWN_SECONDS = 300
MONITOR_ALL_SYMBOLS_TIMEFRAMES = True 

# ★★★★★ ここからが修正箇所 ★★★★★
# Web UIのドロップダウンに表示する通貨ペアの順番を定義
SYMBOL_DISPLAY_ORDER = [
    'USDJPY',
    'EURUSD',
    'GBPJPY',
    'GOLD',
    'BTCUSD', # BTUUSDはBTCUSDのタイポと判断したよ
    'ETHUSD',
    'XRPUSD'
]

# 監視対象リスト (このリスト自体は変更なし)
SYMBOLS_TIMEFRAMES_TO_MONITOR = [
    # --- FX & コモディティ & 仮想通貨 ---
    ('USDJPY', 'M1'), ('USDJPY', 'M5'), ('USDJPY', 'M15'), ('USDJPY', 'H1'), ('USDJPY', 'D1'),
    ('EURUSD', 'M1'), ('EURUSD', 'M5'), ('EURUSD', 'M15'), ('EURUSD', 'H1'), ('EURUSD', 'D1'),
    ('GOLD', 'M1'), ('GOLD', 'M5'), ('GOLD', 'M15'), ('GOLD', 'H1'), ('GOLD', 'D1'),
    ('BTCUSD', 'M1'), ('BTCUSD', 'M5'), ('BTCUSD', 'M15'), ('BTCUSD', 'H1'), ('BTCUSD', 'D1'),
    ('GBPJPY', 'M1'), ('GBPJPY', 'M5'), ('GBPJPY', 'M15'), ('GBPJPY', 'H1'), ('GBPJPY', 'D1'),
    ('ETHUSD', 'M1'), ('ETHUSD', 'M5'), ('ETHUSD', 'M15'), ('ETHUSD', 'H1'), ('ETHUSD', 'D1'),
    ('XRPUSD', 'M1'), ('XRPUSD', 'M5'), ('XRPUSD', 'M15'), ('XRPUSD', 'H1'), ('XRPUSD', 'D1'),
]
# ★★★★★ ここまでが修正箇所 ★★★★★

# EMA設定
EMA_SHORT_PERIOD = 9
EMA_MEDIUM_PERIOD = 20
EMA_LONG_PERIOD = 50

# --- 5. 通知サービス設定 ---
# (変更なし)
LINE_ENABLED = True
LINE_MESSAGING_API_CHANNEL_ACCESS_TOKEN = "yA+08IORXZqnOUL1iD5EnJxUCxMZcr7iXkagGfRJIfi+5uPSvdLNd3ZF8cHxoIfuwmh45LyEtY1ZgEiJHb83yv1FVZwdK93QTO3MS3tFSFQb6rTaziZrOQKf8oVjMEhX+7zBsP0p9I2gGymDELulGQdB04t89/1O/w1cDnyilFU="
LINE_MESSAGING_API_TO_IDS = ["Uf646027a3e2f5dec3eef328dbcee96ca"]
IMGUR_CLIENT_ID = "8c9a867ff9205be"
IMGUR_CLIENT_SECRET = "96331aef31e6e255701a2ae5cf84d95e1b61afe4"
GMAIL_ENABLED = True
GMAIL_SENDER_EMAIL = "toshikazu.1976.12.8@gmail.com"
GMAIL_APP_PASSWORD = "kfli itbn fmrz jdfm"
GMAIL_RECIPIENT_EMAILS = ["toshikazu.1976.12.8@gmail.com"]

# --- 6. チャート描画設定 ---
CHART_OUTPUT_DIR = "static/charts"
TIMEZONE = "Asia/Tokyo"

# --- 7. Web UI 設定 ---
WEB_UI_HOST = '0.0.0.0'
WEB_UI_PORT = 5000

# --- 8. 外部API設定 ---
# FINNHUB_API_KEY = 'd1afk1hr01qltin14fggd1afk1hr01qltin14fh0'

# --- 9. 自動売買のデフォルト設定 ---
AUTO_TRADING_ENABLED = False
DEFAULT_LOT_SIZE = 0.01
DEFAULT_STOP_LOSS_PIPS = 20
DEFAULT_TAKE_PROFIT_PIPS = 40

# --- 10. 取引モード別設定 ---
SCALP_SETTINGS = {"stop_loss_pips": 10, "take_profit_pips": 15}
DAYTRADE_SETTINGS = {"stop_loss_pips": 40, "take_profit_pips": 80}