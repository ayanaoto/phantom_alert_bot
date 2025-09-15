# chart_drawer.py (最終修正版)

import pandas as pd
import mplfinance as mpf
import os
import logging
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

class ChartDrawer:
    def __init__(self, output_dir="static/charts"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"ChartDrawer を初期化しました。出力ディレクトリ: {self.output_dir}")

    def save_candlestick_chart(self, df: pd.DataFrame, symbol: str, timeframe: str, filename_prefix: str, logic_name: str = "Signal"):
        if df.empty:
            logger.warning(f"空のDataFrameのため、チャート生成をスキップ ({symbol}-{timeframe})。")
            return None

        if not isinstance(df.index, pd.DatetimeIndex):
            logger.error("インデックスがDatetimeIndexではありません。チャート生成を中止します。")
            return None
        
        if 'Volume' not in df.columns:
            df['Volume'] = 0

        # --- プロットするインジケーターを動的に決定 ---
        apds = []
        
        # EMA
        for period in [9, 20, 50, 200]:
            ema_col = f'EMA_{period}'
            if ema_col in df.columns and not df[ema_col].isnull().all():
                apds.append(mpf.make_addplot(df[ema_col], panel=0))
        
        # ボリンジャーバンド
        bbl_col = next((col for col in df.columns if col.startswith('BBL_')), None)
        bbu_col = next((col for col in df.columns if col.startswith('BBU_')), None)
        if bbl_col and bbu_col and not df[bbl_col].isnull().all():
            apds.append(mpf.make_addplot(df[bbu_col], color='cyan', linestyle='--'))
            apds.append(mpf.make_addplot(df[bbl_col], color='cyan', linestyle='--'))

        # サブプロット用のパネル番号と比率を管理
        panel_id = 2
        panel_ratios = [4, 1] # メインチャートと出来高の比率

        # MACD
        macd_col = next((col for col in df.columns if col.startswith('MACD_')), None)
        macds_col = next((col for col in df.columns if col.startswith('MACDs_')), None)
        if macd_col and macds_col and not df[macd_col].isnull().all():
            apds.append(mpf.make_addplot(df[macd_col], panel=panel_id, color='fuchsia', ylabel='MACD'))
            apds.append(mpf.make_addplot(df[macds_col], panel=panel_id, color='cyan'))
            panel_ratios.append(1.5)
            panel_id += 1

        # RSI
        rsi_col = next((col for col in df.columns if col.startswith('RSI_')), None)
        if rsi_col and not df[rsi_col].isnull().all():
            apds.append(mpf.make_addplot(df[rsi_col], panel=panel_id, color='orange', ylabel='RSI', ylim=(0, 100)))
            panel_ratios.append(1)
            panel_id += 1

        # ストキャスティクス
        stochk_col = next((col for col in df.columns if col.startswith('STOCHk_')), None)
        stochd_col = next((col for col in df.columns if col.startswith('STOCHd_')), None)
        if stochk_col and stochd_col and not df[stochk_col].isnull().all():
            apds.append(mpf.make_addplot(df[stochk_col], panel=panel_id, color='lime', ylabel='Stoch', ylim=(0,100)))
            apds.append(mpf.make_addplot(df[stochd_col], panel=panel_id, color='red'))
            panel_ratios.append(1)
            panel_id += 1

        # スタイルの設定
        s = mpf.make_mpf_style(base_mpf_style='yahoo', figcolor='#1a1a2e', facecolor='#1a1a2e', edgecolor='#e0e0e0', gridcolor='#3a3a4e')

        # ファイル名とパスの設定
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{filename_prefix}_{timestamp_str}.png" 
        filepath = os.path.join(self.output_dir, filename)

        try:
            mpf.plot(df, type='candle', style=s,
                     title=f"{symbol} {timeframe} - {logic_name}", 
                     ylabel='Price',
                     volume=True,
                     addplot=apds,
                     panel_ratios=tuple(panel_ratios),
                     figscale=1.5,
                     savefig=filepath,
                     warn_too_much_data=10000 
                    )
            logger.info(f"チャートを保存しました: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"チャートの生成中にエラーが発生しました ({symbol}-{timeframe}): {e}", exc_info=True)
            return None