# C:\Users\pc\OneDrive\Desktop\phantom_alert_bot\signal_logic.py

import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# --- 1. インジケーター計算関数 ---

# ボリンジャーバンドの追加
def add_bollinger_bands(df: pd.DataFrame, window: int = 20, window_dev: float = 2.0) -> pd.DataFrame:
    """
    データフレームにボリンジャーバンド (BBL, BBM, BBU) を追加します。
    Args:
        df (pd.DataFrame): OHLCVデータを含むDataFrame。
        window (int): 期間。
        window_dev (float): 標準偏差の乗数。
    Returns:
        pd.DataFrame: ボリンジャーバンドが追加されたDataFrame。
    """
    if 'Close' not in df.columns:
        logger.warning("ボリンジャーバンド計算に必要な 'Close' カラムが見つかりません。")
        return df

    bb = ta.bbands(df['Close'], length=window, std=window_dev)

    # pandas_taの出力カラム名がバージョンによって異なる場合があるため、存在する方を使用
    # BBL, BBM, BBU のカラム名を柔軟に特定する
    # 例: BBL_20.0, BBM_20.0, BBU_20.0 または BBL_20, BBM_20, BBU_20
    bbl_col = next((col for col in bb.columns if col.startswith(f'BBL_{window}')), None)
    bbm_col = next((col for col in bb.columns if col.startswith(f'BBM_{window}')), None)
    bbu_col = next((col for col in bb.columns if col.startswith(f'BBU_{window}')), None)

    # 小数点形式も考慮
    if not bbl_col: bbl_col = next((col for col in bb.columns if col.startswith(f'BBL_{float(window)}')), None)
    if not bbm_col: bbm_col = next((col for col in bb.columns if col.startswith(f'BBM_{float(window)}')), None)
    if not bbu_col: bbu_col = next((col for col in bb.columns if col.startswith(f'BBU_{float(window)}')), None)


    if bbl_col and bbm_col and bbu_col:
        df[f'BBL_{window}'] = bb[bbl_col]
        df[f'BBM_{window}'] = bb[bbm_col]
        df[f'BBU_{window}'] = bb[bbu_col]
        logger.debug(f"ボリンジャーバンド (BB_{window}) を追加しました。カラム名: {bbl_col}, {bbm_col}, {bbu_col}")
    else:
        logger.error(f"ボリンジャーバンド (BB_{window}) の必要なカラムが見つかりませんでした。bb.columns: {bb.columns.tolist()}")
        # 全てのカラムが見つからない場合は、NaNでカラムを追加するか、元のdfを返す
        df[f'BBL_{window}'] = np.nan
        df[f'BBM_{window}'] = np.nan
        df[f'BBU_{window}'] = np.nan

    return df

# RSIの追加
def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    データフレームにRSIを追加します。
    Args:
        df (pd.DataFrame): OHLCVデータを含むDataFrame。
        window (int): 期間。
    Returns:
        pd.DataFrame: RSIが追加されたDataFrame。
    """
    if 'Close' not in df.columns:
        logger.warning("RSI計算に必要な 'Close' カラムが見つかりません。")
        return df

    rsi_series = ta.rsi(df['Close'], length=window)
    
    # pandas_ta 0.3.x 系の RSI 出力は Series に直接 RSI_window の名前が付く
    # 新しいバージョンでは DataFrame を返し、カラム名が RSI_window になる可能性も考慮
    if isinstance(rsi_series, pd.Series):
        df[f'RSI_{window}'] = rsi_series
        logger.debug(f"RSI (RSI_{window}) を追加しました。(Series形式)")
    else: # DataFrameの場合
        rsi_col = next((col for col in rsi_series.columns if col.startswith(f'RSI_{window}')), None)
        if not rsi_col: # 小数点形式も考慮
            rsi_col = next((col for col in rsi_series.columns if col.startswith(f'RSI_{float(window)}')), None)
        
        if rsi_col:
            df[f'RSI_{window}'] = rsi_series[rsi_col]
            logger.debug(f"RSI (RSI_{window}) を追加しました。カラム名: {rsi_col}")
        else:
            logger.error(f"RSI (RSI_{window}) の必要なカラムが見つかりませんでした。rsi_series.columns: {rsi_series.columns.tolist()}")
            df[f'RSI_{window}'] = np.nan
    return df

# MACDの追加
def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    データフレームにMACD (MACD, MACDh, MACDs) を追加します。
    Args:
        df (pd.DataFrame): OHLCVデータを含むDataFrame。
        fast (int): 短期EMAの期間。
        slow (int): 長期EMAの期間。
        signal (int): シグナルラインのEMA期間。
    Returns:
        pd.DataFrame: MACDが追加されたDataFrame。
    """
    if 'Close' not in df.columns:
        logger.warning("MACD計算に必要な 'Close' カラムが見つかりません。")
        return df

    macd_data = ta.macd(df['Close'], fast=fast, slow=slow, signal=signal)

    # ログに出力された正確なカラム名を使って直接アクセスを試みる
    # macd_data.columns: ['MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9'] を元に
    base_name = f'_{fast}_{slow}_{signal}'
    
    # 期待されるカラム名を定義
    expected_cols = {
        'MACD': f'MACD{base_name}',
        'MACDh': f'MACDh{base_name}',
        'MACDs': f'MACDs{base_name}'
    }

    found_cols = {}

    # まず、小数点なしの正確なカラム名で直接アクセスを試みる
    for key, expected_col_name in expected_cols.items():
        if expected_col_name in macd_data.columns:
            found_cols[key] = expected_col_name
        else:
            # 小数点付きの形式も考慮してstartswithで検索 (念のため)
            # 例: MACD_12.0_26.0_9.0
            float_base_name = f'_{float(fast)}_{float(slow)}_{float(signal)}'
            expected_float_col_name = expected_col_name.replace(base_name, float_base_name)
            if expected_float_col_name in macd_data.columns:
                found_cols[key] = expected_float_col_name
            else:
                # 汎用的なstartswith検索 (例: MACD_ から始まるもの)
                # ただし、これで複数のカラムがヒットする可能性があるので注意
                potential_cols = [c for c in macd_data.columns if c.startswith(key)]
                if len(potential_cols) == 1:
                    found_cols[key] = potential_cols[0]
                elif len(potential_cols) > 1:
                    # 複数見つかった場合は、最も期間情報に近いものを選ぶか、ログを出す
                    logger.warning(f"MACD {key} のカラムが複数見つかりました: {potential_cols}。最初のものを使用します。")
                    found_cols[key] = potential_cols[0]


    macd_col = found_cols.get('MACD')
    macdh_col = found_cols.get('MACDh')
    macds_col = found_cols.get('MACDs')


    if macd_col and macdh_col and macds_col:
        df[f'MACD_{fast}_{slow}_{signal}'] = macd_data[macd_col]
        df[f'MACDh_{fast}_{slow}_{signal}'] = macd_data[macdh_col]
        df[f'MACDs_{fast}_{slow}_{signal}'] = macd_data[macds_col]
        logger.debug(f"MACD ({fast},{slow},{signal}) を追加しました。カラム名: MACD='{macd_col}', MACDh='{macdh_col}', MACDs='{macds_col}'")
    else:
        logger.error(f"MACD ({fast},{slow},{signal}) の必要なカラムが見つかりませんでした。macd_data.columns: {macd_data.columns.tolist()}")
        logger.error(f"見つけようとしたカラム: MACD='{macd_col}', MACDh='{macdh_col}', MACDs='{macds_col}'")
        # カラムが見つからない場合はNaNで初期化し、KeyErrorを避ける
        df[f'MACD_{fast}_{slow}_{signal}'] = np.nan
        df[f'MACDh_{fast}_{slow}_{signal}'] = np.nan
        df[f'MACDs_{fast}_{slow}_{signal}'] = np.nan

    return df

# ストキャスティクス (Stochastic Oscillator) の追加
def add_stochastic(df: pd.DataFrame, k_window: int = 14, d_window: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    """
    データフレームにストキャスティクス (%K, %D) を追加します。
    Args:
        df (pd.DataFrame): OHLCVデータを含むDataFrame。
        k_window (int): %K の期間。
        d_window (int): %D の期間。
        smooth_k (int): %K の平滑化期間。
    Returns:
        pd.DataFrame: ストキャスティクスが追加されたDataFrame。
    """
    if not all(col in df.columns for col in ['High', 'Low', 'Close']):
        logger.warning("ストキャスティクス計算に必要な 'High', 'Low', 'Close' カラムが見つかりません。")
        return df

    stoch_data = ta.stoch(df['High'], df['Low'], df['Close'], k=k_window, d=d_window, smooth_k=smooth_k)

    # STOCHk, STOCHd のカラム名を柔軟に特定する
    stochk_col = next((col for col in stoch_data.columns if col.startswith(f'STOCHk_{k_window}_{d_window}_{smooth_k}')), None)
    stochd_col = next((col for col in stoch_data.columns if col.startswith(f'STOCHd_{k_window}_{d_window}_{smooth_k}')), None)

    # 小数点形式も考慮
    if not stochk_col: stochk_col = next((col for col in stoch_data.columns if col.startswith(f'STOCHk_{float(k_window)}_{float(d_window)}_{float(smooth_k)}')), None)
    if not stochd_col: stochd_col = next((col for col in stoch_data.columns if col.startswith(f'STOCHd_{float(k_window)}_{float(d_window)}_{float(smooth_k)}')), None)

    if stochk_col and stochd_col:
        df[f'STOCHk_{k_window}_{d_window}_{smooth_k}'] = stoch_data[stochk_col]
        df[f'STOCHd_{k_window}_{d_window}_{smooth_k}'] = stoch_data[stochd_col]
        logger.debug(f"ストキャスティクス (Stoch_{k_window}_{d_window}_{smooth_k}) を追加しました。カラム名: {stochk_col}, {stochd_col}")
    else:
        logger.error(f"ストキャスティクス (Stoch_{k_window}_{d_window}_{smooth_k}) の必要なカラムが見つかりませんでした。stoch_data.columns: {stoch_data.columns.tolist()}")
        df[f'STOCHk_{k_window}_{d_window}_{smooth_k}'] = np.nan
        df[f'STOCHd_{k_window}_{d_window}_{smooth_k}'] = np.nan

    return df

# EMA (指数移動平均) の追加
def add_ema(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """
    データフレームに指数移動平均 (EMA) を追加します。
    Args:
        df (pd.DataFrame): OHLCVデータを含むDataFrame。
        window (int): EMAの期間。
    Returns:
        pd.DataFrame: EMAが追加されたDataFrame。
    """
    if 'Close' not in df.columns:
        logger.warning("EMA計算に必要な 'Close' カラムが見つかりません。")
        return df

    ema_series = ta.ema(df['Close'], length=window)
    if isinstance(ema_series, pd.Series):
        df[f'EMA_{window}'] = ema_series
        logger.debug(f"EMA (EMA_{window}) を追加しました。(Series形式)")
    else:
        ema_col = next((col for col in ema_series.columns if col.startswith(f'EMA_{window}')), None)
        if not ema_col: # 小数点形式も考慮
            ema_col = next((col for col in ema_series.columns if col.startswith(f'EMA_{float(window)}')), None)

        if ema_col:
            df[f'EMA_{window}'] = ema_series[ema_col]
            logger.debug(f"EMA (EMA_{window}) を追加しました。カラム名: {ema_col}")
        else:
            logger.error(f"EMA (EMA_{window}) の必要なカラムが見つかりませんでした。ema_series.columns: {ema_series.columns.tolist()}")
            df[f'EMA_{window}'] = np.nan
    return df

# ATR (Average True Range) の追加
def add_atr(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    データフレームにATRを追加します。
    Args:
        df (pd.DataFrame): OHLCVデータを含むDataFrame。
        window (int): ATRの期間。
    Returns:
        pd.DataFrame: ATRが追加されたDataFrame。
    """
    if not all(col in df.columns for col in ['High', 'Low', 'Close']):
        logger.warning("ATR計算に必要な 'High', 'Low', 'Close' カラムが見つかりません。")
        return df

    atr_series = ta.atr(df['High'], df['Low'], df['Close'], length=window)
    if isinstance(atr_series, pd.Series):
        df[f'ATR_{window}'] = atr_series
        logger.debug(f"ATR (ATR_{window}) を追加しました。(Series形式)")
    else:
        atr_col = next((col for col in atr_series.columns if col.startswith(f'ATR_{window}')), None)
        if not atr_col: # 小数点形式も考慮
            atr_col = next((col for col in atr_series.columns if col.startswith(f'ATR_{float(window)}')), None)

        if atr_col:
            df[f'ATR_{window}'] = atr_series[atr_col]
            logger.debug(f"ATR (ATR_{window}) を追加しました。カラム名: {atr_col}")
        else:
            logger.error(f"ATR (ATR_{window}) の必要なカラムが見つかりませんでした。atr_series.columns: {atr_series.columns.tolist()}")
            df[f'ATR_{window}'] = np.nan
    return df


# すべてのインジケーターをデータフレームに追加する統合関数
def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    指定されたDataFrameにすべての必要なテクニカルインジケーターを追加します。
    Args:
        df (pd.DataFrame): OHLCVデータを含むDataFrame。
    Returns:
        pd.DataFrame: すべてのインジケーターが追加されたDataFrame。
    """
    if df.empty:
        logger.warning("インジケーター計算のためのDataFrameが空です。")
        return df

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"必須カラム '{col}' がDataFrameに存在しません。インジケーター計算をスキップします。")
            return df

    nan_ratio = df[required_cols].isnull().sum().sum() / (len(df) * len(required_cols))
    if nan_ratio > 0.1:
        logger.warning(f"データに多くのNaNが含まれています（約 {nan_ratio*100:.2f}%）。インジケーター計算に影響する可能性があります。")

    try:
        # インジケーターの追加順序は、依存関係に基づいて考慮する
        df = add_bollinger_bands(df, window=20, window_dev=2.0)
        df = add_rsi(df, window=14)
        df = add_macd(df, fast=12, slow=26, signal=9)
        df = add_stochastic(df, k_window=14, d_window=3, smooth_k=3)
        df = add_ema(df, window=9)
        df = add_ema(df, window=20)
        df = add_ema(df, window=50)
        df = add_ema(df, window=100)
        df = add_ema(df, window=200)
        df = add_atr(df, window=14)

        logger.info("すべてのテクニカルインジケーターを追加しました。")
    except Exception as e:
        logger.error(f"インジケーターの追加中にエラーが発生しました: {e}", exc_info=True)
        return df

    return df.copy()

# --- 2. シグナル生成関数 ---

def generate_signal(df: pd.DataFrame) -> dict | None:
    """
    テクニカルインジケーターに基づいて売買シグナルを生成します。
    Args:
        df (pd.DataFrame): インジケーターが追加されたOHLCVデータを含むDataFrame。
    Returns:
        dict | None: シグナル情報を含む辞書（'type', 'price', 'timestamp', 'reasons'）
                    またはシグナルがない場合はNone。
    """
    if df.empty or len(df) < 200: # 最低限のデータ量があるか確認 (インジケーター計算に必要)
        logger.warning("シグナル生成のためのデータが不十分です。")
        return None

    # 最新のローソク足のデータ
    latest = df.iloc[-1]
    # 1つ前のローソク足のデータ (RSIトレンド、MACDクロスオーバーなどの判断に使う)
    previous = df.iloc[-2]

    signal_type = None
    reasons = []

    # 各インジケーターが存在し、NaNでないか確認
    required_indicators = [
        'BBL_20', 'BBM_20', 'BBU_20', 'RSI_14',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'STOCHk_14_3_3', 'STOCHd_14_3_3',
        'EMA_9', 'EMA_20', 'EMA_50', 'EMA_100', 'EMA_200', 'ATR_14'
    ]
    for ind in required_indicators:
        if ind not in latest.index or pd.isna(latest[ind]) or \
           ind not in previous.index or pd.isna(previous[ind]):
            logger.debug(f"シグナル生成に必要なインジケーター '{ind}' が不足しているか、NaNです。シグナル生成をスキップします。")
            return None

    # --- 買いシグナルロジック ---
    # 1. RSIによる過売りの判断
    if latest['RSI_14'] < 30:
        reasons.append(f"RSI({latest['RSI_14']:.2f}) が売られすぎ水準 (30未満) です。")
        if not signal_type: signal_type = "買い"

    # 2. MACDのゴールデンクロス
    if previous['MACD_12_26_9'] < previous['MACDs_12_26_9'] and \
       latest['MACD_12_26_9'] > latest['MACDs_12_26_9']:
        reasons.append("MACDがゴールデンクロスしました。")
        if not signal_type: signal_type = "買い"

    # 3. ストキャスティクスのゴールデンクロス (かつ過売り水準)
    if previous['STOCHk_14_3_3'] < previous['STOCHd_14_3_3'] and \
       latest['STOCHk_14_3_3'] > latest['STOCHd_14_3_3'] and \
       latest['STOCHk_14_3_3'] < 30:
        reasons.append("ストキャスティクスがゴールデンクロスしました（過売り水準）。")
        if not signal_type: signal_type = "買い"

    # 4. 価格がボリンジャーバンド下限にタッチ or 下抜けて反発
    if latest['Close'] < latest['BBL_20'] and latest['Close'] > previous['Close']:
        reasons.append(f"価格({latest['Close']:.3f})がボリンジャーバンド下限({latest['BBL_20']:.3f})を下抜けから反発しました。")
        if not signal_type: signal_type = "買い"

    # 5. 短期EMAが長期EMAを上抜ける
    if previous['EMA_9'] < previous['EMA_20'] and latest['EMA_9'] > latest['EMA_20']:
        reasons.append("短期EMA(9)が中期EMA(20)を上抜けました。")
        if not signal_type: signal_type = "買い"

    if previous['EMA_20'] < previous['EMA_50'] and latest['EMA_20'] > latest['EMA_50']:
        reasons.append("中期EMA(20)が長期EMA(50)を上抜けました。")
        if not signal_type: signal_type = "買い"

    # 複数EMAのパーフェクトオーダー（上昇トレンドを示唆）
    # EMA200 > EMA100 > EMA50 > EMA20 > EMA9
    if (latest['EMA_200'] > latest['EMA_100'] > latest['EMA_50'] > latest['EMA_20'] > latest['EMA_9']) and \
       (previous['EMA_200'] > previous['EMA_100'] > previous['EMA_50'] > previous['EMA_20'] > previous['EMA_9']):
        reasons.append("EMAがパーフェクトオーダー（上昇）です。")
        # これは単独でシグナルではなく、他のシグナルの補強材料とすることが多い
        # if not signal_type: signal_type = "買い"


    # --- 売りシグナルロジック ---
    # 1. RSIによる買われすぎの判断
    if latest['RSI_14'] > 70:
        reasons.append(f"RSI({latest['RSI_14']:.2f}) が買われすぎ水準 (70超え) です。")
        signal_type = "売り" # 買いシグナルより優先されるように、無条件で上書き

    # 2. MACDのデッドクロス
    if previous['MACD_12_26_9'] > previous['MACDs_12_26_9'] and \
       latest['MACD_12_26_9'] < latest['MACDs_12_26_9']:
        reasons.append("MACDがデッドクロスしました。")
        signal_type = "売り" # 上書き

    # 3. ストキャスティクスのデッドクロス (かつ買われすぎ水準)
    if previous['STOCHk_14_3_3'] > previous['STOCHd_14_3_3'] and \
       latest['STOCHk_14_3_3'] < latest['STOCHd_14_3_3'] and \
       latest['STOCHk_14_3_3'] > 70:
        reasons.append("ストキャスティクスがデッドクロスしました（買われすぎ水準）。")
        signal_type = "売り" # 上書き

    # 4. 価格がボリンジャーバンド上限にタッチ or 上抜けて反落
    if latest['Close'] > latest['BBU_20'] and latest['Close'] < previous['Close']:
        reasons.append(f"価格({latest['Close']:.3f})がボリンジャーバンド上限({latest['BBU_20']:.3f})を上抜けから反落しました。")
        signal_type = "売り" # 上書き

    # 5. 短期EMAが長期EMAを下に抜ける
    if previous['EMA_9'] > previous['EMA_20'] and latest['EMA_9'] < latest['EMA_20']:
        reasons.append("短期EMA(9)が中期EMA(20)を下に抜けました。")
        signal_type = "売り" # 上書き

    if previous['EMA_20'] > previous['EMA_50'] and latest['EMA_20'] < latest['EMA_50']:
        reasons.append("中期EMA(20)が長期EMA(50)を下に抜けました。")
        signal_type = "売り" # 上書き

    # 複数EMAのパーフェクトオーダー（下降トレンドを示唆）
    # EMA9 > EMA20 > EMA50 > EMA100 > EMA200
    if (latest['EMA_9'] > latest['EMA_20'] > latest['EMA_50'] > latest['EMA_100'] > latest['EMA_200']) and \
       (previous['EMA_9'] > previous['EMA_20'] > previous['EMA_50'] > previous['EMA_100'] > previous['EMA_200']):
        reasons.append("EMAがパーフェクトオーダー（下降）です。")
        # if not signal_type: signal_type = "売り"


    if signal_type:
        return {
            "type": signal_type,
            "price": latest['Close'],
            "timestamp": latest.name,
            "reasons": list(set(reasons))
        }
    return None

# --- テスト用のコード (signal_logic.py を直接実行した場合のみ実行される) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- signal_logic.py のテストを開始します ---")

    # ダミーデータの生成 (実際のMT5データと同じ形式を模擬)
    data = {
        'time': pd.to_datetime([f'2023-01-01 00:{i:02d}:00' for i in range(250)], unit='ns', utc=True),
        'open': np.linspace(100, 150, 250) + np.random.rand(250) * 0.5,
        'high': np.linspace(101, 152, 250) + np.random.rand(250) * 2,
        'low': np.linspace(99, 148, 250) - np.random.rand(250) * 2,
        'close': np.linspace(100.5, 149.5, 250) + np.random.rand(250) * 0.5,
        'tick_volume': np.random.randint(100, 1000, 250)
    }
    df = pd.DataFrame(data)
    # MT5Connectorが返す形式に合わせるため、Timeカラムを作成しインデックスに設定
    df['Time'] = pd.to_datetime(df['time'], unit='ns', utc=True)
    df = df.set_index('Time')
    # タイムゾーンを 'Asia/Tokyo' に変換
    df.index = df.index.tz_convert('Asia/Tokyo')


    # mplfinanceの要件に合わせてカラム名を変更 (大文字始まりに)
    df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'tick_volume': 'Volume'
    }, inplace=True)


    logger.info(f"ダミーデータ (最初の5行):\n{df.head()}")
    logger.info(f"ダミーデータ (最後の5行):\n{df.tail()}")

    # 全てのインジケーターを追加
    df_with_indicators = add_all_indicators(df.copy())
    logger.info(f"インジケーター追加後のデータフレームのカラム:\n{df_with_indicators.columns.tolist()}")
    logger.info(f"インジケーター追加後のデータフレーム (最後の5行):\n{df_with_indicators.tail()}")

    # シグナルを生成
    signal = generate_signal(df_with_indicators)

    if signal:
        logger.info(f"生成されたシグナル: {signal}")
    else:
        logger.info("シグナルは生成されませんでした。")

    logger.info("--- signal_logic.py のテストを終了します ---")