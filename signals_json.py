import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SIGNALS_FILE_PATH = os.path.join("data", "signals.json")

def load_signals_json():
    if not os.path.exists(SIGNALS_FILE_PATH):
        logger.info(f"'{SIGNALS_FILE_PATH}' が見つかりません。新規作成します。")
        os.makedirs(os.path.dirname(SIGNALS_FILE_PATH), exist_ok=True)
        with open(SIGNALS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}
    
    try:
        with open(SIGNALS_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"❌ '{SIGNALS_FILE_PATH}' のJSON解析エラー: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ '{SIGNALS_FILE_PATH}' の読み込みエラー: {e}")
        return {}

def save_signals_json(data):
    try:
        os.makedirs(os.path.dirname(SIGNALS_FILE_PATH), exist_ok=True)
        with open(SIGNALS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"✅ '{SIGNALS_FILE_PATH}' を保存しました。")
        return True
    except Exception as e:
        logger.error(f"❌ '{SIGNALS_FILE_PATH}' の保存エラー: {e}")
        return False

def update_signals_json(symbol: str, timeframe: str, desc: str, desc_en: str, 
                        image_filename: str = None, signal: str = None, 
                        entry: float = None, tp: float = None, sl: float = None, 
                        image_url: str = None, price: float = None):
    """
    signals.json を更新します。
    """
    signals_data = load_signals_json()
    
    key = f"{symbol}_{timeframe}"
    
    new_signal_entry = {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signal": signal, # "buy", "sell", or None
        "description": desc,
        "description_en": desc_en,
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "current_price": price,
        "chart_filename": image_filename, # "/static/charts/..." 形式
        "chart_url": image_url # ImgurのURLなど
    }
    
    signals_data[key] = new_signal_entry
    
    if save_signals_json(signals_data):
        logger.info(f"'{key}' のシグナル情報を更新しました。シグナル: {signal if signal else 'なし'}")
        return True
    else:
        logger.error(f"'{key}' のシグナル情報の更新に失敗しました。")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print("--- signals_json.py テスト ---")

    test_symbol = "USDJPY"
    test_timeframe = "M5"

    # テストデータを削除して初期化
    if os.path.exists(SIGNALS_FILE_PATH):
        os.remove(SIGNALS_FILE_PATH)
        print(f"既存の '{SIGNALS_FILE_PATH}' を削除しました。")
    
    # 新規シグナルを更新 (買い)
    print("\n--- 買いシグナルを更新 (USDJPY M5) ---")
    test_signal_type_buy = "buy"
    test_entry_buy = 155.000
    test_tp_buy = 155.100
    test_sl_buy = 154.900
    test_image_filename = "/static/charts/USDJPY_M5_20230601_100000_BUY.png"
    test_image_url_buy = "https://i.imgur.com/buy_signal_chart.png"
    test_price_buy = 155.005

    update_signals_json(
        symbol=test_symbol,
        timeframe=test_timeframe,
        desc="MACDゴールデンクロスで買いシグナル発生",
        desc_en="Buy signal generated due to MACD golden cross",
        image_filename=test_image_filename,
        signal=test_signal_type_buy,
        entry=test_entry_buy,
        tp=test_tp_buy,
        sl=test_sl_buy,
        image_url=test_image_url_buy,
        price=test_price_buy
    )
    
    # 売りシグナルを更新 (別のシンボル・時間足の例)
    print("\n--- 売りシグナルを更新 (EURUSD H1) ---")
    test_signal_type_sell = "sell"
    test_entry_sell = 1.08000
    test_tp_sell = 1.07900
    test_sl_sell = 1.08100
    test_image_url_sell = "https://i.imgur.com/sell_signal_chart.png"
    test_price_sell = 1.08005

    update_signals_json(
        symbol="EURUSD",
        timeframe="H1",
        desc="MACDデッドクロスで売りシグナル発生",
        desc_en="Sell signal generated due to MACD death cross",
        image_filename="/static/charts/EURUSD_H1_20250609_180000.png",
        signal=test_signal_type_sell,
        entry=test_entry_sell,
        tp=test_tp_sell,
        sl=test_sl_sell,
        image_url=test_image_url_sell,
        price=test_price_sell
    )

    # シグナルなしのケースを更新 (既存のUSDJPY M5を上書き)
    print("\n--- シグナルなしを更新 (USDJPY M5を上書き) ---")
    update_signals_json(
        symbol=test_symbol,
        timeframe=test_timeframe,
        desc="シグナル条件が満たされませんでした",
        desc_en="Signal conditions not met",
        signal=None,
        entry=None,
        tp=None,
        sl=None,
        image_filename=None,
        image_url=None,
        price=155.050 # 現在価格は更新
    )

    print("\n--- signals.json の内容を表示 ---")
    loaded_data = load_signals_json()
    print(json.dumps(loaded_data, indent=2, ensure_ascii=False))

    print("\n--- シグナル取得テスト (get_signals_for_web_ui) ---")
    # web_server.py で使われる関数はload_signals_json()だけなので、ここでは直接呼び出さない。
    # むしろ、web_server.py の /api/signals エンドポイントを叩くテストが必要。
    
    # テスト後、ファイルをクリーンアップ
    if os.path.exists(SIGNALS_FILE_PATH):
        # os.remove(SIGNALS_FILE_PATH)
        print(f"テスト用の '{SIGNALS_FILE_PATH}' は残しています。")