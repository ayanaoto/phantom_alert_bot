# trade_manager.py (通知メッセージ強化版)

import MetaTrader5 as mt5
import logging
import json
import os
import config
from typing import Optional, Dict

from line_notifier import LineNotifier
from gmail_notifier import GmailNotifier

logger = logging.getLogger(__name__)
SETTINGS_FILE = 'settings.json'

class TradeManager:
    def __init__(self, mt5_connector, line_notifier: Optional[LineNotifier], gmail_notifier: Optional[GmailNotifier]):
        self.mt5 = mt5_connector
        self.line_notifier = line_notifier
        self.gmail_notifier = gmail_notifier
        self.magic_number = 20240621
        self.settings = self.get_trade_settings()

    def get_trade_settings(self) -> dict:
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    mode = settings.get('mode', 'daytrade')
                    trade_params = config.DAYTRADE_SETTINGS if mode == 'daytrade' else config.SCALP_SETTINGS
                    return {
                        "auto_trading": settings.get('auto_trading', False),
                        "lot_size": float(settings.get('lot_size', config.DEFAULT_LOT_SIZE)),
                        "sl_pips": int(trade_params.get('stop_loss_pips')),
                        "tp_pips": int(trade_params.get('take_profit_pips')),
                        "mode": mode
                    }
        except Exception as e:
            logger.error(f"設定ファイル({SETTINGS_FILE})の読み込み/解析に失敗しました: {e}")
        return {
            "auto_trading": False, "lot_size": 0.01,
            "sl_pips": config.DAYTRADE_SETTINGS['stop_loss_pips'],
            "tp_pips": config.DAYTRADE_SETTINGS['take_profit_pips'], "mode": "daytrade"
        }

    def get_current_mode(self) -> str:
        settings = self.get_trade_settings()
        return settings.get('mode', 'daytrade')

    def calculate_tp_sl(self, signal_type: str, entry_price: float, symbol: str) -> Dict[str, float]:
        settings = self.get_trade_settings()
        point = self.mt5.get_symbol_point(symbol)
        if point is None or point == 0:
            return {"tp": 0.0, "sl": 0.0}
        sl_distance = settings["sl_pips"] * 10 * point
        tp_distance = settings["tp_pips"] * 10 * point
        if signal_type.upper() == 'BUY':
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        return {"tp": take_profit, "sl": stop_loss}

    def execute_action(self, signal_info: dict, chart_filepath: Optional[str]):
        settings = self.get_trade_settings()
        if settings["auto_trading"]:
            self._send_trade_order(signal_info, settings)
        self._send_notifications(signal_info, chart_filepath)

    def _send_trade_order(self, signal_info: dict, settings: dict):
        try:
            symbol, signal_type = signal_info.get('symbol'), signal_info.get('signal', '').upper()
            if not symbol or not signal_type in ['BUY', 'SELL']: return
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                logger.error(f"{symbol}の現在価格が取得できませんでした。")
                return
            price = tick.ask if signal_type == 'BUY' else tick.bid
            tp_sl = self.calculate_tp_sl(signal_type, price, symbol)
            stop_loss, take_profit = tp_sl['sl'], tp_sl['tp']
            if take_profit == 0 or stop_loss == 0:
                logger.error(f"TP/SLの計算に失敗したため、発注をキャンセルしました。")
                return
            request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": settings["lot_size"], "type": mt5.ORDER_TYPE_BUY if signal_type == 'BUY' else mt5.ORDER_TYPE_SELL, "price": price, "sl": stop_loss, "tp": take_profit, "magic": self.magic_number, "comment": f"Phantom-{settings['mode']}", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_FOK}
            log_message = (f"【自動売買】{symbol} に {signal_type} 注文 (mode: {settings['mode']}, lot: {settings['lot_size']}, sl: {settings['sl_pips']}pips, tp: {settings['tp_pips']}pips)")
            logger.warning(log_message)
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE: 
                logger.error(f"注文送信失敗: retcode={result.retcode}, comment={result.comment}")
            else: 
                logger.info(f"注文送信成功: PositionID={result.order}, comment={result.comment}")
        except Exception as e:
            logger.error(f"注文実行中に予期せぬエラー: {e}", exc_info=True)

    # ★★★★★ ここからが通知メッセージの変更箇所 ★★★★★
    def _send_notifications(self, signal_info: dict, chart_filepath: Optional[str]):
        timeframe = signal_info.get('timeframe')
        
        # M1スキャルピングシグナルなど、頻繁すぎる通知を抑制したい場合はここで制御できる
        if timeframe == 'M1' and self.get_current_mode() == 'scalp':
            logger.info(f"[{signal_info.get('symbol')}-{timeframe}] はスキャルピングM1のため、通知をスキップしました。")
            return
            
        # 理由(desc)を取得し、メッセージに含める
        reasons = signal_info.get('desc', '理由不明')
        
        # LINE通知用のメッセージを作成
        message_text = (
            f"【Phantom Alert】\n"
            f"{signal_info.get('symbol')} {timeframe} {signal_info.get('signal', '').upper()} シグナル発生！\n"
            f"価格: {signal_info.get('price')}\n"
            f"理由: {reasons}" # ★★★ 理由を追加 ★★★
        )
        
        # Gmail通知用の件名と本文を作成
        subject = f"【Phantom Alert】{signal_info.get('symbol')} {timeframe} {signal_info.get('signal', '').upper()} シグナル"
        body = (
            f"価格: {signal_info.get('price')}\n"
            f"理由: {reasons}\n\n" # ★★★ 理由を追加 ★★★
            f"TP: {signal_info.get('tp', 'N/A')}\n"
            f"SL: {signal_info.get('sl', 'N/A')}"
        )
        
        if self.line_notifier: self.line_notifier.send_line_notification(message=message_text, image_path=chart_filepath)
        if self.gmail_notifier: self.gmail_notifier.send_email_notification(subject, body, chart_filepath)