# line_analyzer.py

import pandas as pd
import numpy as np
import mplfinance as mpf
from scipy.signal import find_peaks
import logging
from datetime import datetime
import MetaTrader5 as mt5_api # ★★★ 修正点1: 正しいライブラリをインポート ★★★

# 既存の自作モジュールをインポート
import config
from mt5_connector import MT5Connector

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 分析設定 ---
# ここで分析したい通貨ペアや時間足を変更できます
SYMBOL_TO_ANALYZE = "USDJPY"
TIMEFRAME_TO_ANALYZE = "H1" # M1, M5, M15, H1, D1 など
CANDLE_COUNT = 250         # 取得するローソク足の数
PEAK_DISTANCE = 15         # スイングハイ・ローを検出する際の間隔（この本数分離れた山・谷を探す）

def find_support_resistance(df: pd.DataFrame, distance: int) -> dict:
    """
    データフレームからスイングハイ・ローを検出し、サポートとレジスタンスの価格レベルを返す。
    """
    # find_peaksは山の頂上（極大値）を見つける関数
    # 高値のピーク（レジスタンス）を見つける
    resistance_indices, _ = find_peaks(df['High'], distance=distance, width=3)
    
    # 安値のピーク（サポート）を見つけるには、データを反転させて同じ関数を使う
    support_indices, _ = find_peaks(-df['Low'], distance=distance, width=3)

    # 見つかったインデックスから価格を取得し、直近のものに絞る
    resistance_levels = df['High'].iloc[resistance_indices].nlargest(3).tolist()
    support_levels = df['Low'].iloc[support_indices].nsmallest(3).tolist()

    logger.info(f"レジスタンスレベルを検出: {resistance_levels}")
    logger.info(f"サポートレベルを検出: {support_levels}")
    
    return {"support": support_levels, "resistance": resistance_levels}

def find_trend_lines(df: pd.DataFrame, distance: int) -> dict:
    """
    直近のスイングハイ・ロー2点ずつを結び、簡易的なトレンドラインの座標を返す。
    """
    # サポート・レジスタンスと同様にスイングポイントを見つける
    resistance_indices, _ = find_peaks(df['High'], distance=distance)
    support_indices, _ = find_peaks(-df['Low'], distance=distance)
    
    trend_lines = {"support": None, "resistance": None}

    # サポートトレンドライン（直近の安値2点を結ぶ）
    if len(support_indices) >= 2:
        # 直近2つの安値のインデックスを取得
        p1_idx, p2_idx = support_indices[-2], support_indices[-1]
        p1 = (df.index[p1_idx], df['Low'].iloc[p1_idx])
        p2 = (df.index[p2_idx], df['Low'].iloc[p2_idx])
        trend_lines["support"] = [p1, p2]
        logger.info(f"サポートトレンドラインを検出: {p1[0]} - {p2[0]}")

    # レジスタンストレンドライン（直近の高値2点を結ぶ）
    if len(resistance_indices) >= 2:
        # 直近2つの高値のインデックスを取得
        p1_idx, p2_idx = resistance_indices[-2], resistance_indices[-1]
        p1 = (df.index[p1_idx], df['High'].iloc[p1_idx])
        p2 = (df.index[p2_idx], df['High'].iloc[p2_idx])
        trend_lines["resistance"] = [p1, p2]
        logger.info(f"レジスタンストレンドラインを検出: {p1[0]} - {p2[0]}")
        
    return trend_lines

def plot_analysis_chart(df: pd.DataFrame, symbol: str, timeframe: str, sr_levels: dict, trend_lines: dict):
    """
    分析結果をチャートに描画して画像として保存する。
    """
    # 水平線（hlines）とトレンドライン（alines）の準備
    hlines = dict(hlines=sr_levels['support'] + sr_levels['resistance'], 
                  colors=['g']*len(sr_levels['support']) + ['r']*len(sr_levels['resistance']),
                  linestyle='-.')
    
    alines_list = [line for line in trend_lines.values() if line is not None]

    # チャートのスタイル設定
    style = mpf.make_mpf_style(base_mpf_style='yahoo', figcolor='#1a1a2e', facecolor='#1a1a2e', 
                               edgecolor='#e0e0e0', gridcolor='#3a3a4e')

    # 出力ファイル名
    output_filename = "analysis_chart.png"
    
    logger.info("チャートの描画を開始します...")
    mpf.plot(df.tail(150), # 直近150本を描画
             type='candle',
             style=style,
             title=f"{symbol} {timeframe} Analysis",
             ylabel="Price",
             volume=True,
             hlines=hlines,
             alines=dict(alines=alines_list, colors=['g', 'r']), # サポート緑、レジスタンス赤
             panel_ratios=(4, 1),
             figscale=1.5,
             savefig=output_filename,
             warn_too_much_data=10000 
            )
    logger.info(f"チャートを {output_filename} として保存しました。")

def main():
    """メイン処理"""
    logger.info("ライン分析アプリを開始します。")

    # MT5に接続
    mt5 = MT5Connector(path=config.MT5_PATH, login=config.MT5_LOGIN, 
                       password=config.MT5_PASSWORD, server=config.MT5_SERVER)
    if not mt5.connect():
        logger.error("MT5への接続に失敗しました。アプリを終了します。")
        return

    # データを取得
    # ★★★ 修正点2: mt5.mt5 ではなく、インポートした mt5_api を使う ★★★
    timeframe_obj = getattr(mt5_api, f'TIMEFRAME_{TIMEFRAME_TO_ANALYZE.upper()}')
    df = mt5.get_candlestick_data(SYMBOL_TO_ANALYZE, timeframe_obj, CANDLE_COUNT)
    
    # MT5から切断
    mt5.disconnect()

    if df.empty:
        logger.error("ローソク足データが取得できませんでした。")
        return

    # 分析を実行
    sr_levels = find_support_resistance(df, distance=PEAK_DISTANCE)
    trend_lines = find_trend_lines(df, distance=PEAK_DISTANCE)

    # チャートを描画
    plot_analysis_chart(df, SYMBOL_TO_ANALYZE, TIMEFRAME_TO_ANALYZE, sr_levels, trend_lines)

    logger.info("ライン分析アプリを終了します。")

if __name__ == "__main__":
    main()