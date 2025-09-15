# config.py
import os

# LINE Notify API settings
# Replace with your actual LINE Channel Access Token and User ID
# It's highly recommended to use environment variables for sensitive data in production
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "yA+08IORXZqnOUL1iD5EnJxUCxMZcr7iXkagGfRJIfi+5uPSvdLNd3ZF8cHxoIfuwmh45LyEtY1ZgEiJHb83yv1FVZwdK93QTO3MS3tFSFQb6rTaziZrOQKf8oVjMEhX+7zBsP0p9I2gGymDELulGQdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = os.getenv("LINE_USER_ID", "Uf646027a3e2f5dec3eef328dbcee96ca")

# Imgur API settings
# Replace with your actual Imgur Client ID
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID", "8c9a867ff9205be")

# Application settings (used by signal_runner_loop and potentially app.py)
SYMBOLS = ["USDJPY", "EURUSD", "GOLD_USD", "BTCUSDT"]
TIMEFRAMES = ["M1", "M5", "M15", "H1"] # D1はチャート生成のみでシグナルループでは使わない想定
MODE = "realtime" # または "backtest" (今は使われていない可能性あり)

# Web UI settings
WEB_UI_HOST = "127.0.0.1" # または "0.0.0.0" で外部からのアクセスを許可
WEB_UI_PORT = 5000

# ロギングレベル
LOG_LEVEL = "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL

# MT5のインストールパス (Windowsの場合の例)
# あなたのMT5ターミナル(terminal64.exe)の正確なパスを設定してください
MT5_PATH = "C:\\Program Files\\BIG Solutions MetaTrader 5\\terminal64.exe" 
# 注意: Pythonの文字列ではバックスラッシュはエスケープが必要です。
# またはスラッシュ(/)を使うのが安全です。例: "C:/Program Files/BIG Solutions MetaTrader 5/terminal64.exe"