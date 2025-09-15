# scalping_logic.py

import pandas as pd
import pandas_ta as ta
import logging
import numpy as np

logger = logging.getLogger(__name__)

# --- 1. インジケーター計算関数 (daytrade_logic.pyと同じものを流用) ---

def add_bollinger_bands(df: pd.DataFrame, window: int = 20, window_dev: float = 2.0) -> pd.DataFrame:
    if 'Close' not in df.columns: return df
    try:
        bb = ta.bbands(df['Close'], length=window, std=window_dev)
        if bb is not None and not bb.empty:
            for col in bb.columns:
                if col not in df.columns:
                    df[col] = bb[col]
    except Exception as e:
        logger.warning(f"Bollinger Bands計算中にエラー: {e}")
    return df

def add_stochastic(df: pd.DataFrame, k: int = 14, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    if not all(c in df.columns for c in ['High', 'Low', 'Close']): return df
    stoch_data = ta.stoch(df['High'], df['Low'], df['Close'], k=k, d=d, smooth_k=smooth_k)
    if stoch_data is not None and not stoch_data.empty:
        for col in stoch_data.columns:
            if col not in df.columns:
                df[col] = stoch_data[col]
    return df

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """スキャルピングで使うインジケーターのみ追加"""
    if df.empty: return df
    try:
        df = add_bollinger_bands(df)
        df = add_stochastic(df)
        logger.info("すべてのテクニカルインジケーターを追加しました。(Scalping Logic)")
    except Exception as e:
        logger.error(f"インジケーターの追加中にエラーが発生しました: {e}", exc_info=True)
    return df.copy()

# --- 2. シグナル生成関数 (★★★ スキャルピング用に簡略化 ★★★) ---

def generate_signal(df: pd.DataFrame) -> dict | None:
    """ストキャスティクスとボリンジャーバンドを使ったシンプルなスキャルピングロジック"""
    if df.empty or len(df) < 20: return None

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    # 必要なインジケーターが揃っているか確認
    stochk_name = f'STOCHk_14_3_3'
    stochd_name = f'STOCHd_14_3_3'
    bbl_name = f'BBL_20_2.0'
    bbu_name = f'BBU_20_2.0'
    required = [stochk_name, stochd_name, bbl_name, bbu_name]
    if any(ind not in latest.index or pd.isna(latest[ind]) for ind in required):
        return None

    signal_type = None
    reasons = []

    # 【買いロジック】ストキャスが売られすぎ圏でGC、かつBB下限タッチ
    if latest['Close'] < latest[bbl_name] and \
       previous[stochk_name] < previous[stochd_name] and \
       latest[stochk_name] > latest[stochd_name] and \
       latest[stochk_name] < 25:
        signal_type = "買い"
        reasons.append("BB下限タッチ & ストキャスGC")

    # 【売りロジック】ストキャスが買われすぎ圏でDC、かつBB上限タッチ
    elif latest['Close'] > latest[bbu_name] and \
         previous[stochk_name] > previous[stochd_name] and \
         latest[stochk_name] < latest[stochd_name] and \
         latest[stochk_name] > 75:
        signal_type = "売り"
        reasons.append("BB上限タッチ & ストキャスDC")

    if signal_type:
        logger.info(f"シグナル生成(Scalping): {signal_type}, 根拠: {', '.join(reasons)}")
        return {"type": signal_type, "price": latest['Close'], "timestamp": latest.name, "reasons": reasons}
        
    return None