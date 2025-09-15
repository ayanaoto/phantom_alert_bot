# signal_runner_loop.py

import threading
import time
import logging
import MetaTrader5 as mt5
from datetime import datetime

# 取引ロジックのモジュールを動的にインポート
import daytrade_logic
import scalping_logic

class SignalRunner(threading.Thread):
    def __init__(self, symbol, timeframe_str, mt5_connector, chart_drawer, economic_calendar, trade_manager, interval, add_signal_callback, add_log_callback):
        super().__init__()
        self.daemon = True
        self.name = f"SignalRunner-{symbol}-{timeframe_str}"
        
        self.symbol = symbol
        self.timeframe_str = timeframe_str
        self.timeframe_obj = getattr(mt5, f'TIMEFRAME_{timeframe_str.upper()}')
        self.mt5 = mt5_connector
        self.chart_drawer = chart_drawer
        self.economic_calendar = economic_calendar
        self.trade_manager = trade_manager
        self.interval = interval
        self.add_signal_callback = add_signal_callback
        self.add_log_callback = add_log_callback
        
        self.stop_event = threading.Event()
        self.last_signal_time = 0
        self.cooldown_period = 300 # 5分

        # モードに応じてロジックモジュールを切り替え
        current_mode = self.trade_manager.get_current_mode()
        self.logic_module = daytrade_logic if current_mode == 'daytrade' else scalping_logic

        logging.info(f"[初期化] {symbol}-{timeframe_str} シグナルランナーを初期化しました。モード: {current_mode}")

    def stop(self):
        """スレッドを停止する"""
        self.stop_event.set()
        logging.info(f"[{self.symbol}-{self.timeframe_str}] 停止シグナルを受信しました。")

    def run(self):
        """シグナル監視のメインループ"""
        logging.info(f"[{self.symbol}-{self.timeframe_str}] シグナル監視を開始します。")
        time.sleep(5) # 初期化の安定を待つ

        while not self.stop_event.is_set():
            try:
                # --- 1. データ取得 ---
                df = self.mt5.get_candlestick_data(self.symbol, self.timeframe_obj)
                if df.empty or len(df) < 50:
                    logging.warning(f"[{self.symbol}-{self.timeframe_str}] データが不十分なため、今回のチェックをスキップします。")
                    time.sleep(self.interval)
                    continue
                
                latest_price = df['Close'].iloc[-1]

                # --- 2. ロジック実行 ---
                current_mode = self.trade_manager.get_current_mode()
                self.logic_module = daytrade_logic if current_mode == 'daytrade' else scalping_logic
                
                df_with_indicators = self.logic_module.add_all_indicators(df.copy())
                
                signal_result = None
                if current_mode == 'daytrade':
                    strong_sr = self.logic_module.find_strong_sr_levels(df_with_indicators, self.symbol)
                    signal_result = self.logic_module.generate_signal(df_with_indicators, strong_sr)
                else: # scalp
                    signal_result = self.logic_module.generate_signal(df_with_indicators)

                # --- 3. 結果処理 ---
                is_trade_signal = signal_result and signal_result.get("type") not in ["見送り", "NONE", None] and "罠" not in signal_result.get("type")

                if is_trade_signal:
                    # 【売買シグナルあり】
                    now = time.time()
                    if now - self.last_signal_time < self.cooldown_period:
                        logging.info(f"[{self.symbol}-{self.timeframe_str}] クールダウン中のため、シグナルをスキップします。")
                    else:
                        self.last_signal_time = now
                        tp_sl = self.trade_manager.calculate_tp_sl(signal_result["type"], latest_price, self.symbol)
                        chart_filepath = self.chart_drawer.save_candlestick_chart(df_with_indicators, self.symbol, self.timeframe_str, f"{self.symbol}_{self.timeframe_str}_{signal_result['type']}", logic_name=current_mode)
                        
                        signal_data = {
                            "symbol": self.symbol,
                            "timeframe": self.timeframe_str,
                            "signal": signal_result["type"].upper(),
                            "price": f"{latest_price:.3f}",
                            "tp": f"{tp_sl['tp']:.3f}",
                            "sl": f"{tp_sl['sl']:.3f}",
                            "desc": ", ".join(signal_result.get("reasons", ["-"])),
                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        self.add_signal_callback(signal_data, chart_filepath)
                        self.trade_manager.execute_action(signal_data, chart_filepath)

                else:
                    # 【シグナルなし or 見送り or 罠アラート】
                    desc = "シグナル待機中..."
                    signal_type = "NONE"
                    if signal_result and signal_result.get("reasons"):
                        desc = ", ".join(signal_result.get("reasons"))
                        signal_type = signal_result.get("type") # 「見送り」や「罠アラート」を表示

                    signal_data = {
                        "symbol": self.symbol,
                        "timeframe": self.timeframe_str,
                        "signal": signal_type,
                        "price": f"{latest_price:.3f}",
                        "tp": "N/A",
                        "sl": "N/A",
                        "desc": desc,
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    # チャートは無いので None を渡す
                    self.add_signal_callback(signal_data, None)

            except Exception as e:
                logging.error(f"[{self.symbol}-{self.timeframe_str}] ループ中にエラーが発生: {e}", exc_info=True)
            
            finally:
                # 次のループまでの待機
                self.stop_event.wait(self.interval)
        
        logging.info(f"[{self.symbol}-{self.timeframe_str}] シグナル監視を終了します。")
