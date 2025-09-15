# daytrade_logic.py (戦略ロジック強化・修正版)

import pandas as pd
import pandas_ta as ta
import logging
import numpy as np
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)

# --- 1. インジケーター計算関数 (既存のものをそのまま利用) ---

def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    if 'Close' not in df.columns: return df
    df[f'RSI_{window}'] = ta.rsi(df['Close'], length=window)
    return df

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """このロジックで必要最低限のインジケーターのみ追加"""
    if df.empty: return df
    try:
        df = add_rsi(df)
        logger.info("RSIインジケーターを追加しました。(Strategic Logic)")
    except Exception as e:
        logger.error(f"インジケーターの追加中にエラーが発生しました: {e}", exc_info=True)
    return df.copy()

# ★★★★★ ここからが「強い水平線」を特定するロジック ★★★★★

def find_strong_sr_levels(df: pd.DataFrame, symbol: str, peak_distance: int = 10, cluster_tolerance_pips: int = 20, min_touches: int = 3) -> dict:
    """
    過去のデータから、複数回反発した「強い」サポート・レジスタンスラインを特定する。
    1. すべてのスイングハイ・ローを検出する。
    2. 近い価格の点をグループ化（クラスタリング）する。
    3. 指定回数以上タッチされたグループだけを「強いライン」として採用する。
    """
    if df.empty:
        return {"support": [], "resistance": []}

    point_unit = 0.01 if 'JPY' in symbol else 0.0001
    tolerance = cluster_tolerance_pips * point_unit

    high_indices, _ = find_peaks(df['High'], distance=peak_distance)
    low_indices, _ = find_peaks(-df['Low'], distance=peak_distance)
    all_highs = df['High'].iloc[high_indices].tolist()
    all_lows = df['Low'].iloc[low_indices].tolist()

    def cluster_prices(prices: list, tolerance: float) -> list:
        if not prices:
            return []
        
        prices.sort()
        clusters = []
        current_cluster = [prices[0]]
        
        for price in prices[1:]:
            if price <= current_cluster[-1] + tolerance:
                current_cluster.append(price)
            else:
                clusters.append(current_cluster)
                current_cluster = [price]
        clusters.append(current_cluster)
        return clusters

    resistance_clusters = cluster_prices(all_highs, tolerance)
    support_clusters = cluster_prices(all_lows, tolerance)

    strong_resistances = [np.mean(cluster) for cluster in resistance_clusters if len(cluster) >= min_touches]
    strong_supports = [np.mean(cluster) for cluster in support_clusters if len(cluster) >= min_touches]
    
    logger.info(f"強いレジスタンスラインを検出: {[f'{lvl:.3f}' for lvl in strong_resistances]}")
    logger.info(f"強いサポートラインを検出: {[f'{lvl:.3f}' for lvl in strong_supports]}")

    return {"support": strong_supports, "resistance": strong_resistances}

# ★★★★★ ここからが新しい「逆ファントムアラート」のロジック ★★★★★

def detect_phantom_trap(df: pd.DataFrame, strong_sr_levels: dict, volume_period: int = 20, volume_threshold_ratio: float = 0.8) -> dict | None:
    """
    強い水平線をブレイクしたように見えて、出来高が伴わない「ダマシ（罠）」を検出する。
    """
    if df.empty or len(df) < volume_period: return None
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    # 最近の平均出来高を計算
    avg_volume = df['Volume'].iloc[-volume_period:-1].mean()
    
    # 罠の条件をチェック
    for level in strong_sr_levels['resistance']:
        # レジスタンスを上にブレイクしたが、出来高が平均より少ない場合
        if previous['Close'] < level and latest['Close'] > level:
            if latest['Volume'] < avg_volume * volume_threshold_ratio:
                reasons = [f"レジスタンス({level:.3f})をブレイクしたが出来高が少ない", f"出来高: {latest['Volume']:.0f} < 平均: {(avg_volume * volume_threshold_ratio):.0f}"]
                return {"type": "売り罠アラート", "price": latest['Close'], "timestamp": latest.name, "reasons": reasons, "log_type": "PHANTOM_TRAP"}

    for level in strong_sr_levels['support']:
        # サポートを下にブレイクしたが、出来高が平均より少ない場合
        if previous['Close'] > level and latest['Close'] < level:
            if latest['Volume'] < avg_volume * volume_threshold_ratio:
                reasons = [f"サポート({level:.3f})をブレイクしたが出来高が少ない", f"出来高: {latest['Volume']:.0f} < 平均: {(avg_volume * volume_threshold_ratio):.0f}"]
                return {"type": "買い罠アラート", "price": latest['Close'], "timestamp": latest.name, "reasons": reasons, "log_type": "PHANTOM_TRAP"}

    return None

# ★★★★★ ここからが「シグナル生成」ロジック (修正版) ★★★★★

def generate_signal(df: pd.DataFrame, strong_sr_levels: dict) -> dict | None:
    """
    強い水平線と現在の価格アクションに基づき、「反発」または「ブレイク」を判断する。
    """
    if df.empty or len(df) < 2: return None

    # ★★★ 最初に「罠」の検知ロジックを呼び出す ★★★
    phantom_signal = detect_phantom_trap(df, strong_sr_levels)
    if phantom_signal:
        return phantom_signal # 罠を検知したら、他の判断をせずに即座に結果を返す

    latest = df.iloc[-1]
    previous = df.iloc[-2]
    current_price = latest['Close']

    # --- 反発狙いのロジック ---
    for level in strong_sr_levels['support']:
        # サポートラインに近づき、かつ最後の足が陽線（上昇）で終わった場合
        if abs(latest['Low'] - level) < (latest['High'] - latest['Low']) and latest['Close'] > latest['Open']:
            if latest['RSI_14'] < 45: # 売られすぎ圏からの反発をRSIで確認
                reasons = [f"強いサポートライン({level:.3f})からの反発", f"RSI({latest['RSI_14']:.1f})"]
                return {"type": "買い", "price": current_price, "timestamp": latest.name, "reasons": reasons, "log_type": "SIGNAL"}
    
    for level in strong_sr_levels['resistance']:
        # レジスタンスラインに近づき、かつ最後の足が陰線（下落）で終わった場合
        if abs(latest['High'] - level) < (latest['High'] - latest['Low']) and latest['Close'] < latest['Open']:
            if latest['RSI_14'] > 55: # 買われすぎ圏からの反発をRSIで確認
                reasons = [f"強いレジスタンスライン({level:.3f})からの反発", f"RSI({latest['RSI_14']:.1f})"]
                return {"type": "売り", "price": current_price, "timestamp": latest.name, "reasons": reasons, "log_type": "SIGNAL"}

    # --- ブレイク見送りのロジック ---
    for level in strong_sr_levels['support']:
        # 強いサポートを終値で明確に下にブレイクした場合
        if previous['Close'] > level and latest['Close'] < level:
             return {"type": "見送り", "price": current_price, "timestamp": latest.name, 
                     "reasons": [f"重要サポートライン ({level:.3f}) を下にブレイク。トレンド転換の可能性。"], "log_type": "BREAKOUT"}

    for level in strong_sr_levels['resistance']:
        # 強いレジスタンスを終値で明確に上にブレイクした場合
        if previous['Close'] < level and latest['Close'] > level:
             return {"type": "見送り", "price": current_price, "timestamp": latest.name, 
                     "reasons": [f"重要レジスタンスライン ({level:.3f}) を上にブレイク。トレンド継続の可能性。"], "log_type": "BREAKOUT"}

    return None