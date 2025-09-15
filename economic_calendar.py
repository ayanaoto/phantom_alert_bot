# economic_calendar.py (APIアクセス制御・最終確定版)

import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
import pytz
import config 
import threading # ★★★ スレッドのロック機能を追加 ★★★

logger = logging.getLogger(__name__)

class EconomicCalendar:
    def __init__(self):
        self.api_key = getattr(config, 'FINNHUB_API_KEY', None)
        self.base_url = "https://finnhub.io/api/v1/calendar/economic"
        self.timezone = pytz.timezone("Asia/Tokyo")
        self.last_fetch_time = None
        self.events_df = pd.DataFrame()
        
        self.is_enabled = bool(self.api_key)
        
        # ★★★ スレッド間の競合を防ぐためのロックを作成 ★★★
        self.lock = threading.Lock()

        if self.is_enabled:
            logger.info("EconomicCalendar (Finnhub API) を初期化しました。")
        else:
            logger.warning("Finnhub APIキーが設定されていないため、EconomicCalendarは無効です。")

    def _fetch_events(self):
        # このメソッドが複数のスレッドから同時に呼び出されても、
        # with self.lock: のブロック内は一度に一つのスレッドしか実行できない。
        with self.lock:
            if not self.is_enabled:
                return

            # キャッシュが有効なら、ロックをすぐに解放して終了
            if self.last_fetch_time and (datetime.now() - self.last_fetch_time).total_seconds() < 3600:
                return

            # 以下、実際にAPIにアクセスする処理
            try:
                today = datetime.now(self.timezone).date()
                params = {
                    'token': self.api_key,
                    'from': today.strftime('%Y-%m-%d'),
                    'to': (today + timedelta(days=1)).strftime('%Y-%m-%d')
                }
                
                logger.info("Finnhub APIへのアクセスを実行します...") # 実際にアクセスする時だけログを出す
                response = requests.get(self.base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if not data or 'economicCalendar' not in data:
                    logger.warning("Finnhubから経済指標データが返されませんでした。")
                    self.events_df = pd.DataFrame()
                    return

                self.events_df = pd.DataFrame(data['economicCalendar'])
                
                if not self.events_df.empty:
                    self.events_df['utc_time'] = pd.to_datetime(self.events_df['time'], unit='s', utc=True)

                self.last_fetch_time = datetime.now() # 最終取得時刻を更新
                if not self.events_df.empty:
                    logger.info(f"Finnhubから {len(self.events_df)} 件の経済指標データを取得・キャッシュしました。")

            except requests.exceptions.HTTPError as http_err:
                 # 429や403エラーを個別捕捉して分かりやすくログに出す
                if http_err.response.status_code == 429:
                    logger.error("Finnhub APIのレート制限を超えました。次の更新まで待機します。")
                elif http_err.response.status_code == 403:
                    logger.error("Finnhub APIへのアクセスが禁止されました。APIキーが正しいか確認してください。")
                else:
                    logger.error(f"FinnhubへのHTTPエラーが発生しました: {http_err}")
                self.events_df = pd.DataFrame() # エラー時は空にする
            except Exception as e:
                logger.error(f"Finnhubからのデータ取得または解析中に予期せぬエラーが発生しました: {e}", exc_info=False)
                self.events_df = pd.DataFrame()

    def is_major_event_soon(self, symbol: str, minutes_ahead: int = 30) -> bool:
        self._fetch_events() # まずデータを取得（またはキャッシュを利用）

        if not self.is_enabled or self.events_df.empty or 'impact' not in self.events_df.columns:
            return False
            
        # Finnhub APIでは通貨ペアではなく国コード(JP, US, EUなど)で判断する必要がある
        # シンボル名から国コードを推測する簡易ロジック
        country_map = {'JPY': 'JP', 'USD': 'US', 'EUR': 'EU', 'GBP': 'GB', 'AUD': 'AU', 'CAD': 'CA', 'CHF': 'CH', 'NZD': 'NZ'}
        currency = symbol[:3].upper()
        country_code = country_map.get(currency)

        if not country_code:
            return False # GOLD, BTCUSDなどは国コードがないため判定しない

        now_utc = datetime.now(pytz.utc)
        time_limit = now_utc + timedelta(minutes=minutes_ahead)

        major_events = self.events_df[self.events_df['impact'] == 'high'].copy()
        relevant_events = major_events[major_events['country'] == country_code]

        for _, event in relevant_events.iterrows():
            if now_utc < event['utc_time'] < time_limit:
                logger.warning(
                    f"重要指標接近！ {minutes_ahead}分以内に {event['country']} の「{event['event']}」が発表されます。"
                    f"対象通貨ペア: {symbol} のシグナル生成を一時停止します。"
                )
                return True
        
        return False