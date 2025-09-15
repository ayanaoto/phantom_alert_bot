# new_signal_generator.py
import pandas_ta as ta_pandas # pandas_ta
import pandas as pd
import logging
import numpy as np

# signal_logic.py から必要な関数をインポート
# signal_logic.py 内の関数を直接使うように変更します
from signal_logic import add_all_indicators, apply_all_signal_logics

logger = logging.getLogger(__name__)

# シグナル生成ロジックの定義
def generate_signal(df, symbol, timeframe, logic="default"):
    """
    OHLCデータと指定されたロジックに基づいて取引シグナルを生成します。
    signal_logic.py の関数を呼び出し、TP/SLなどの取引関連情報を追加します。

    Args:
        df (pd.DataFrame): OHLCデータを含むDataFrame。
                           カラムは 'open', 'high', 'low', 'close', 'tick_volume' である必要があります。
                           インデックスは時間データである必要があります。
        symbol (str): 通貨ペアのシンボル。
        timeframe (str): 時間足の文字列（例: "M5", "H1"）。
        logic (str): 使用するシグナル生成ロジック ('default', 'strict')。

    Returns:
        dict: シグナル情報を含む辞書（'BUY', 'SELL', 'HOLD'など）
              またはデータ不足の場合は None。
              例: {'symbol': 'USDJPY', 'timeframe': 'M5', 'signal': 'BUY',
                   'price': 155.00, 'entry': 154.95, 'tp': 155.20, 'sl': 154.80,
                   'desc': 'RSI買いシグナル発生', 'ichimoku_signal': 'HOLD', ...}
    """
    if df.empty:
        logger.warning(f"{symbol}-{timeframe}: シグナル生成のためのデータが空です。")
        return None

    # signal_logic.py の add_all_indicators を使用してインジケーターを追加
    # add_all_indicatorsは、データ不足の場合でもNaNを埋めてDataFrameを返すため、
    # ここで None を返す可能性はほとんどありません。
    df_with_indicators = add_all_indicators(df.copy()) # 元のdfを変更しないようにcopy()を渡す

    # インジケーター計算後、NaNが多いなどの理由でシグナル判定ができない場合があるため、チェック
    # apply_all_signal_logics はデータ不足の場合でも 'HOLD' を返すため、このチェックは主に情報提供用
    if df_with_indicators.empty or df_with_indicators.iloc[-1].isnull().all():
        logger.warning(f"{symbol}-{timeframe}: インジケーター計算後のデータが不足しているため、シグナル判定をスキップします。")
        return None # または HOLD シグナルを返す

    # signal_logic.py の apply_all_signal_logics を使用して総合シグナルを取得
    # apply_all_signal_logics は必ず辞書を返します (データ不足の場合は HOLD)
    signal_info = apply_all_signal_logics(df_with_indicators, logic=logic)

    # 現在価格を取得 (signal_logic から返される 'price' を使用)
    current_price = signal_info['price']

    # TP/SLの仮計算（これはシグナルロジックに基づいて調整する必要があります）
    # ここでは仮の計算として、現在の価格に基づいてパーセンテージで設定します
    # 実際の取引では、ATRや特定のピボットポイントなどに基づいて決定すべきです。
    tp = np.nan
    sl = np.nan
    entry_price = current_price # エントリー価格は現在の終値とする

    # シグナルに応じてTP/SLを設定
    if signal_info['signal'] == "BUY":
        tp = current_price * 1.002 # 例: 0.2%上のTP
        sl = current_price * 0.998 # 例: 0.2%下のSL
    elif signal_info['signal'] == "SELL":
        tp = current_price * 0.998 # 例: 0.2%下のTP
        sl = current_price * 1.002 # 例: 0.2%上のSL
    
    # 最終的なシグナル情報を作成
    # signal_info が持つ全てのキーをコピーし、TP/SL/Entryを追加
    final_signal_output = signal_info.copy()
    final_signal_output.update({
        'symbol': symbol,
        'timeframe': timeframe,
        'entry': entry_price,
        'tp': tp,
        'sl': sl,
        # 'price'はsignal_infoに既に含まれている
        # 'desc'もsignal_infoに既に含まれている
    })

    return final_signal_output

# --- テストコード ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("--- シグナルジェネレーターのテスト ---")

    # signal_logic.py のテストコードとほぼ同じダミーデータを生成
    import datetime
    import pytz # timezone情報を扱うために追加
    num_bars = 200
    current_utc_time = datetime.datetime.now(pytz.utc)
    times = pd.date_range(end=current_utc_time, periods=num_bars, freq='Min').tolist()
    times = [int(t.timestamp()) for t in times]

    np.random.seed(42)
    base_price = 150.0
    price_changes = np.random.normal(0, 0.1, num_bars).cumsum()
    close_prices = base_price + price_changes
    open_prices = close_prices - np.random.normal(0, 0.05, num_bars)
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.normal(0, 0.05, num_bars))
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.normal(0, 0.05, num_bars))

    dummy_data = {
        'time': times,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'tick_volume': np.random.randint(1000, 5000, num_bars),
        'spread': np.random.randint(1, 3, num_bars),
        'real_volume': np.random.randint(100, 500, num_bars)
    }
    
    dummy_df = pd.DataFrame(dummy_data)
    dummy_df = dummy_df.set_index('time')
    dummy_df.index = pd.to_datetime(dummy_df.index, unit='s', utc=True)

    # シグナル生成テスト
    print("\nデフォルトロジックでシグナルをテスト:")
    signal = generate_signal(dummy_df.copy(), "TESTUSDJPY", "H1", logic="default")
    if signal:
        print(f"シグナル結果: {signal}")
    else:
        print("シグナルは生成されませんでした。")

    print("\n厳格ロジックでシグナルをテスト:")
    signal_strict = generate_signal(dummy_df.copy(), "TESTUSDJPY", "H1", logic="strict")
    if signal_strict:
        print(f"厳格シグナル結果: {signal_strict}")
    else:
        print("厳格シグナルは生成されませんでした。")

    # データが少ない場合のテスト
    print("\nデータが少ない場合のテスト (10本):")
    dummy_df_short = dummy_df.iloc[-10:].copy() # 10本のみ
    signal_short = generate_signal(dummy_df_short, "TESTUSDJPY_SHORT", "M1", logic="default")
    if signal_short:
        print(f"データが少ない場合のシグナル結果: {signal_short}")
        if signal_short['signal'] == "HOLD":
            print("✅ データ不足でHOLDシグナルが正しく返されました。")
        else:
            print("❌ データ不足にもかかわらずHOLD以外のシグナルが返されました。")
    else:
        print("データが少ないためシグナルは生成されませんでした。(Noneが返された)")

    print("\n--- テスト終了 ---")