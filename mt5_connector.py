# mt5_connector.py (自動再接続機能付き 最終修正版)

import MetaTrader5 as mt5
import pandas as pd
import logging
import time
import pytz
from typing import Optional

logger = logging.getLogger(__name__)

class MT5Connector:
    def __init__(self, path: str, login: int, password: str, server: str):
        self.path = path
        self.login = login
        self.password = password
        self.server = server
        self._is_connected = False
        self._last_connect_attempt = 0

    def connect(self) -> bool:
        """MT5ターミナルに接続または再接続を試みます。"""
        # 頻繁な再接続を防ぐ
        if time.time() - self._last_connect_attempt < 10:
            return self._is_connected

        self._last_connect_attempt = time.time()
        logger.info("MT5への接続を試みています...")
        
        # 既に初期化されている場合はシャットダウン
        if mt5.terminal_info():
            mt5.shutdown()
            time.sleep(1)

        if not mt5.initialize(path=self.path):
            logger.error(f"MT5初期化に失敗しました。エラーコード: {mt5.last_error()}")
            self._is_connected = False
            return False

        if not mt5.login(self.login, self.password, self.server):
            logger.error(f"MT5ログインに失敗しました。アカウント: {self.login}, エラーコード: {mt5.last_error()}")
            mt5.shutdown()
            self._is_connected = False
            return False

        self._is_connected = True
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"MT5に正常にログインしました。アカウント: {account_info.login}, 口座残高: {account_info.balance:.2f} {account_info.currency}")
        else:
            logger.warning(f"MT5アカウント情報の取得に失敗しました。エラーコード: {mt5.last_error()}")
        return True

    def disconnect(self):
        """MT5ターミナルから切断します。"""
        if self._is_connected:
            mt5.shutdown()
            self._is_connected = False
            logger.info("MT5から正常に切断しました。")

    def _check_connection(self) -> bool:
        """接続状態を確認し、切断されている場合は再接続を試みる"""
        terminal_info = mt5.terminal_info()
        if terminal_info is None or terminal_info.connected is False:
            logger.warning("MT5との接続が切断されています。再接続を試みます...")
            self._is_connected = False
            return self.connect()
        return True

    def get_candlestick_data(self, symbol: str, timeframe, count: int = 500) -> pd.DataFrame:
        """指定された通貨ペアと時間足のローソク足データを取得します。"""
        if not self._check_connection():
            logger.error("MT5への接続を確立できませんでした。")
            return pd.DataFrame()

        # 気配値表示にシンボルを追加し、最新価格情報を取得する
        if not mt5.symbol_select(symbol, True):
            logger.warning(f"シンボル '{symbol}' を気配値表示に追加できませんでした。データ取得に失敗する可能性があります。")
            
        time.sleep(0.1) # サーバーからの応答を待つ

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.warning(f"'{symbol}' ({self._get_timeframe_name(timeframe)}) のローソク足データが空です。スキップします。")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['Time'] = pd.to_datetime(df['time'], unit='s', utc=True).dt.tz_convert('Asia/Tokyo')
        df = df.set_index('Time')
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'tick_volume': 'Volume'}, inplace=True)
        
        logger.info(f"'{symbol}' ({self._get_timeframe_name(timeframe)}) のデータを {len(df)} 件取得しました。")
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]

    def get_symbol_point(self, symbol: str) -> Optional[float]:
        if not self._check_connection(): return None
        info = mt5.symbol_info(symbol)
        return info.point if info else None

    def _get_timeframe_name(self, timeframe) -> str:
        timeframe_map = {
            mt5.TIMEFRAME_M1: "M1", mt5.TIMEFRAME_M5: "M5", mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_H1: "H1", mt5.TIMEFRAME_D1: "D1"
        }
        return timeframe_map.get(timeframe, str(timeframe))