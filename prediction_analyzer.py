# prediction_analyzer.py (最終版 v3：テキスト色を白に統一)

import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import logging
from datetime import datetime
import MetaTrader5 as mt5_api

# 既存の自作モジュールをインポート
import config
from mt5_connector import MT5Connector
from gmail_notifier import GmailNotifier

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 分析設定 ---
SYMBOL_TO_ANALYZE = "USDJPY"
TIMEFRAME_TO_ANALYZE = "M15"
CANDLE_COUNT = 600
PEAK_DISTANCE = 30
FIBO_RANGE_CANDLES = 100

# --- 表示設定スイッチ ---
DRAW_SUPPORT_RESISTANCE = True
DRAW_TREND_LINES = True
DRAW_FIBONACCI = True
DRAW_TEXT_LABELS = True

def find_support_resistance(df: pd.DataFrame, distance: int) -> dict:
    current_price = df['Close'].iloc[-1]
    resistance_indices, _ = find_peaks(df['High'], distance=distance, width=3)
    support_indices, _ = find_peaks(-df['Low'], distance=distance, width=3)
    all_resistances = df['High'].iloc[resistance_indices]
    all_supports = df['Low'].iloc[support_indices]
    closest_resistances = all_resistances[all_resistances > current_price].nsmallest(2).tolist()
    closest_supports = all_supports[all_supports < current_price].nlargest(2).tolist()
    return {"support": closest_supports, "resistance": closest_resistances}

def find_trend_lines(df: pd.DataFrame, distance: int) -> dict:
    resistance_indices, _ = find_peaks(df['High'], distance=distance)
    support_indices, _ = find_peaks(-df['Low'], distance=distance)
    trend_lines = {"support": None, "resistance": None}
    if len(support_indices) >= 2:
        p1_idx, p2_idx = support_indices[-2], support_indices[-1]
        p1 = (df.index[p1_idx], df['Low'].iloc[p1_idx])
        p2 = (df.index[p2_idx], df['Low'].iloc[p2_idx])
        trend_lines["support"] = [p1, p2]
    if len(resistance_indices) >= 2:
        p1_idx, p2_idx = resistance_indices[-2], resistance_indices[-1]
        p1 = (df.index[p1_idx], df['High'].iloc[p1_idx])
        p2 = (df.index[p2_idx], df['High'].iloc[p2_idx])
        trend_lines["resistance"] = [p1, p2]
    return trend_lines

def find_fibonacci_levels(df: pd.DataFrame, period: int) -> dict:
    recent_df = df.iloc[-period:]
    high_price, low_price = recent_df['High'].max(), recent_df['Low'].min()
    price_diff = high_price - low_price
    levels = {
        "Fibo 23.6%": high_price - price_diff * 0.236,
        "Fibo 38.2%": high_price - price_diff * 0.382,
        "Fibo 50.0%": high_price - price_diff * 0.5,
        "Fibo 61.8%": high_price - price_diff * 0.618,
    }
    return levels

# ★★★★★ ここがテキストの色を変更した箇所 ★★★★★
def draw_text_labels(ax, df, sr_levels, fibo_levels):
    """チャートの右端に各ラインの価格ラベルを描画する"""
    last_candle_x = len(df.tail(150)) -1
    
    if DRAW_SUPPORT_RESISTANCE:
        for level in sr_levels['support']:
            ax.text(last_candle_x + 1, level, f" S: {level:.3f}", color='white', va='center', fontsize=9)
        for level in sr_levels['resistance']:
            ax.text(last_candle_x + 1, level, f" R: {level:.3f}", color='white', va='center', fontsize=9)
            
    if DRAW_FIBONACCI:
        for name, level in fibo_levels.items():
            ax.text(last_candle_x + 1, level, f" {name}", color='white', va='center', fontsize=9)

def plot_analysis_chart(df: pd.DataFrame, symbol: str, timeframe: str, sr_levels: dict, trend_lines: dict, fibo_levels: dict):
    hlines_data, hlines_colors, hlines_styles = [], [], []
    if DRAW_SUPPORT_RESISTANCE:
        hlines_data.extend(sr_levels['support'] + sr_levels['resistance'])
        hlines_colors.extend(['lime']*len(sr_levels['support']) + ['red']*len(sr_levels['resistance']))
        hlines_styles.extend(['-.']*len(sr_levels['support']) + ['-.']*len(sr_levels['resistance']))
    if DRAW_FIBONACCI:
        hlines_data.extend(fibo_levels.values())
        hlines_colors.extend(['yellow']*len(fibo_levels))
        hlines_styles.extend([':']*len(fibo_levels))
    
    hlines_dict = dict(hlines=hlines_data, colors=hlines_colors, linestyle=hlines_styles) if hlines_data else None
    alines_list = [line for line in trend_lines.values() if line is not None] if DRAW_TREND_LINES else []

    style = mpf.make_mpf_style(base_mpf_style='yahoo', figcolor='#1a1a2e', facecolor='#1a1a2e', 
                               edgecolor='#e0e0e0', gridcolor='#3a3a4e')
    output_filename = "analysis_chart.png"
    
    fig, axes = mpf.plot(df.tail(150), type='candle', style=style, title=f"{symbol} {timeframe} Analysis with Fibonacci",
                         ylabel="Price", volume=True, hlines=hlines_dict,
                         alines=dict(alines=alines_list, colors=['lime', 'red']), panel_ratios=(4, 1),
                         figscale=1.5, returnfig=True, warn_too_much_data=10000)

    if DRAW_TEXT_LABELS:
        draw_text_labels(axes[0], df, sr_levels, fibo_levels)

    fig.savefig(output_filename)
    plt.close(fig)
    
    logger.info(f"チャートを {output_filename} として保存しました。")
    return output_filename

def generate_predictions(current_price: float, sr_levels: dict, trend_lines: dict, fibo_levels: dict, df: pd.DataFrame) -> list:
    predictions = []
    if DRAW_SUPPORT_RESISTANCE and sr_levels['resistance']:
        predictions.append(f"シナリオ: 直近のレジスタンス {min(sr_levels['resistance']):.3f} での反落に注意。")
    if DRAW_SUPPORT_RESISTANCE and sr_levels['support']:
        predictions.append(f"シナリオ: 直近のサポート {max(sr_levels['support']):.3f} での反発上昇に注意。")
    if DRAW_FIBONACCI:
        for name, level in fibo_levels.items():
            if abs(current_price - level) < (df['High'].mean() - df['Low'].mean()) * 0.2:
                predictions.append(f"注目: 現在価格が {name}レベル ({level:.3f}) に近接しています。")
    if DRAW_TREND_LINES and trend_lines['support']:
        (p1_time, p1_price), (p2_time, p2_price) = trend_lines['support']
        x1, x2 = df.index.get_loc(p1_time), df.index.get_loc(p2_time)
        if x2 != x1:
            slope = (p2_price - p1_price) / (x2 - x1)
            future_price = p1_price + slope * (len(df) - 1 + 3 - x1)
            predictions.append(f"トレンド予測: 3本先、上昇トレンドラインは {future_price:.3f} 付近を通過。")
    if DRAW_TREND_LINES and trend_lines['resistance']:
        (p1_time, p1_price), (p2_time, p2_price) = trend_lines['resistance']
        x1, x2 = df.index.get_loc(p1_time), df.index.get_loc(p2_time)
        if x2 != x1:
            slope = (p2_price - p1_price) / (x2 - x1)
            future_price = p1_price + slope * (len(df) - 1 + 3 - x1)
            predictions.append(f"トレンド予測: 3本先、下降トレンドラインは {future_price:.3f} 付近に到達。")
    return predictions

def main():
    logger.info("未来予測ライン分析アプリ（最終版v3）を開始します。")

    mt5 = MT5Connector(path=config.MT5_PATH, login=config.MT5_LOGIN, 
                       password=config.MT5_PASSWORD, server=config.MT5_SERVER)
    if not mt5.connect(): return

    timeframe_obj = getattr(mt5_api, f'TIMEFRAME_{TIMEFRAME_TO_ANALYZE.upper()}')
    df = mt5.get_candlestick_data(SYMBOL_TO_ANALYZE, timeframe_obj, CANDLE_COUNT)
    
    mt5.disconnect()
    if df.empty: return

    sr_levels = find_support_resistance(df, distance=PEAK_DISTANCE)
    trend_lines = find_trend_lines(df, distance=PEAK_DISTANCE)
    fibo_levels = find_fibonacci_levels(df, period=FIBO_RANGE_CANDLES)
    current_price = df['Close'].iloc[-1]
    predictions = generate_predictions(current_price, sr_levels, trend_lines, fibo_levels, df)
    
    header = f"--- 未来予測シナリオ ({SYMBOL_TO_ANALYZE} {TIMEFRAME_TO_ANALYZE}) ---"
    current_price_info = f"* 現在価格: {current_price:.3f}"
    prediction_text = "\n".join([f"- {pred}" for pred in predictions]) if predictions else "- 有意な予測シナリオはありません。"
    full_prediction_text = f"{header}\n{current_price_info}\n" + "-"*50 + f"\n{prediction_text}\n" + "="*50
    print("\n" + full_prediction_text + "\n")

    chart_filename = plot_analysis_chart(df, SYMBOL_TO_ANALYZE, TIMEFRAME_TO_ANALYZE, sr_levels, trend_lines, fibo_levels)

    gmail_notifier = GmailNotifier()
    if gmail_notifier.is_enabled:
        email_subject = f"【Phantom分析】{SYMBOL_TO_ANALYZE} {TIMEFRAME_TO_ANALYZE} 未来予測"
        email_body = f"分析対象: {SYMBOL_TO_ANALYZE} ({TIMEFRAME_TO_ANALYZE})\n" + f"現在価格: {current_price:.3f}\n\n" + "【予測シナリオ】\n" + prediction_text
        gmail_notifier.send_email_notification(subject=email_subject, body=email_body, image_path=chart_filename)

    logger.info("未来予測ライン分析アプリを終了します。")

if __name__ == "__main__":
    main()