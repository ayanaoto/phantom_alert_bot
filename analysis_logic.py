# analysis_logic.py (共通分析部品)

import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import logging
from datetime import datetime
import os # ★★★ この行を追加 ★★★


logger = logging.getLogger(__name__)

# 分析設定（外部から変更可能にする）
DEFAULT_PEAK_DISTANCE = 15
DEFAULT_FIBO_RANGE = 100

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
        "Fibo 23.6%": high_price - price_diff * 0.236, "Fibo 38.2%": high_price - price_diff * 0.382,
        "Fibo 50.0%": high_price - price_diff * 0.5, "Fibo 61.8%": high_price - price_diff * 0.618,
    }
    return levels

def generate_predictions(current_price: float, sr_levels: dict, trend_lines: dict, fibo_levels: dict, df: pd.DataFrame) -> list:
    predictions = []
    if sr_levels['resistance']:
        predictions.append(f"シナリオ: 直近のレジスタンス {min(sr_levels['resistance']):.3f} での反落に注意。")
    if sr_levels['support']:
        predictions.append(f"シナリオ: 直近のサポート {max(sr_levels['support']):.3f} での反発上昇に注意。")
    for name, level in fibo_levels.items():
        if abs(current_price - level) < (df['High'].mean() - df['Low'].mean()) * 0.2:
            predictions.append(f"注目: 現在価格が {name}レベル ({level:.3f}) に近接しています。")
    last_x = len(df) - 1
    if trend_lines['support']:
        (p1_time, p1_price), (p2_time, p2_price) = trend_lines['support']
        x1, x2 = df.index.get_loc(p1_time), df.index.get_loc(p2_time)
        if x2 != x1:
            slope = (p2_price - p1_price) / (x2 - x1)
            future_price = p1_price + slope * (last_x + 3 - x1)
            predictions.append(f"トレンド予測: 3本先、上昇トレンドラインは {future_price:.3f} 付近を通過。")
    if trend_lines['resistance']:
        (p1_time, p1_price), (p2_time, p2_price) = trend_lines['resistance']
        x1, x2 = df.index.get_loc(p1_time), df.index.get_loc(p2_time)
        if x2 != x1:
            slope = (p2_price - p1_price) / (x2 - x1)
            future_price = p1_price + slope * (last_x + 3 - x1)
            predictions.append(f"トレンド予測: 3本先、下降トレンドラインは {future_price:.3f} 付近に到達。")
    return predictions

def draw_text_labels(ax, df, sr_levels, fibo_levels):
    last_candle_x = len(df.tail(150)) - 1
    for level in sr_levels['support']: ax.text(last_candle_x + 1, level, f" S: {level:.3f}", color='white', va='center', fontsize=9)
    for level in sr_levels['resistance']: ax.text(last_candle_x + 1, level, f" R: {level:.3f}", color='white', va='center', fontsize=9)
    for name, level in fibo_levels.items(): ax.text(last_candle_x + 1, level, f" {name}", color='white', va='center', fontsize=9)

def plot_analysis_chart(df: pd.DataFrame, symbol: str, timeframe: str, sr_levels: dict, trend_lines: dict, fibo_levels: dict, output_dir: str):
    hlines_data = sr_levels['support'] + sr_levels['resistance'] + list(fibo_levels.values())
    hlines_colors = ['lime']*len(sr_levels['support']) + ['red']*len(sr_levels['resistance']) + ['yellow']*len(fibo_levels)
    hlines_styles = ['-.']*len(sr_levels['support']) + ['-.']*len(sr_levels['resistance']) + [':']*len(fibo_levels)
    hlines_dict = dict(hlines=hlines_data, colors=hlines_colors, linestyle=hlines_styles)
    alines_list = [line for line in trend_lines.values() if line is not None]
    style = mpf.make_mpf_style(base_mpf_style='yahoo', figcolor='#1a1a2e', facecolor='#1a1a2e', edgecolor='#e0e0e0', gridcolor='#3a3a4e')
    
    timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"manual_analysis_{symbol}_{timeframe}_{timestamp_str}.png"
    filepath = os.path.join(output_dir, filename)

    fig, axes = mpf.plot(df.tail(150), type='candle', style=style, title=f"{symbol} {timeframe} Manual Analysis",
                         ylabel="Price", volume=True, hlines=hlines_dict,
                         alines=dict(alines=alines_list, colors=['lime', 'red']), panel_ratios=(4, 1),
                         figscale=1.5, returnfig=True, warn_too_much_data=10000)
    draw_text_labels(axes[0], df, sr_levels, fibo_levels)
    fig.savefig(filepath)
    plt.close(fig)
    logger.info(f"手動分析チャートを保存しました: {filepath}")
    return filepath