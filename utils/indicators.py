import logging
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)

# --- 既存の calculate_ichimoku 関数 (前回の修正版) ---
def calculate_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    # ... (前回の修正内容をそのまま貼り付ける) ...
    logger.debug("calculate_ichimoku: 関数が呼び出されました。")
    logger.debug(f"calculate_ichimoku: 入力DataFrameの最初の5行:\n{df.head().to_string()}")
    logger.debug(f"calculate_ichimoku: 入力DataFrameの列:\n{df.columns.tolist()}")
    logger.debug(f"calculate_ichimoku: 入力DataFrameの行数: {len(df)}")

    required_ohlc_columns = ['open', 'high', 'low', 'close']
    if not all(col in df.columns for col in required_ohlc_columns):
        logger.error(f"必須のOHLC列がDataFrameに見つかりません。必要な列: {required_ohlc_columns}, 現在の列: {df.columns.tolist()}")
        df['tenkan_sen'] = float('nan')
        df['kijun_sen'] = float('nan')
        df['senkou_span_a'] = float('nan')
        df['senkou_span_b'] = float('nan')
        df['chikou_span'] = float('nan')
        return df

    min_required_rows = 52
    if len(df) < min_required_rows:
        logger.warning(f"一目均衡表の計算にはDataFrameの行数が不足しています。現在: {len(df)}、最低必要数: {min_required_rows}")
        df['tenkan_sen'] = float('nan')
        df['kijun_sen'] = float('nan')
        df['senkou_span_a'] = float('nan')
        df['senkou_span_b'] = float('nan')
        df['chikou_span'] = float('nan')
        return df

    try:
        df.ta.ichimoku(append=True)
        logger.debug(f"calculate_ichimoku: pandas_ta.ichimoku 実行後のDataFrameの列:\n{df.columns.tolist()}")

        tenkan_col_name = 'IKS_9'
        kijun_col_name = 'IKS_26'
        senkou_a_col_name = 'ISA_26'
        senkou_b_col_name = 'ISB_52'
        chikou_col_name = 'ISC_26'

        expected_ichimoku_cols = [tenkan_col_name, kijun_col_name, senkou_a_col_name, senkou_b_col_name, chikou_col_name]
        missing_ichimoku_cols = [col for col in expected_ichimoku_cols if col not in df.columns]

        if missing_ichimoku_cols:
             logger.error(f"一目均衡表の必須列がpandas_taから生成されませんでした。不足している列: {missing_ichimoku_cols}, 現在の列: {df.columns.tolist()}")
             for col_name in ['tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span']:
                 if col_name not in df.columns:
                     df[col_name] = float('nan')
             return df

        df['tenkan_sen'] = df[tenkan_col_name]
        df['kijun_sen'] = df[kijun_col_name]
        df['senkou_span_a'] = df[senkou_a_col_name]
        df['senkou_span_b'] = df[senkou_b_col_name]
        df['chikou_span'] = df[chikou_col_name]

        logger.debug(f"一目均衡表を計算しました。最終値: 転換線={df['tenkan_sen'].iloc[-1]:.4f}, 基準線={df['kijun_sen'].iloc[-1]:.4f}, 雲A={df['senkou_span_a'].iloc[-1]:.4f}, 雲B={df['senkou_span_b'].iloc[-1]:.4f}, 遅行線={df['chikou_span'].iloc[-1]:.4f}")

    except KeyError as e:
        logger.error(f"一目均衡表計算中に列アクセスエラーが発生しました: {e}。DataFrameの列を確認してください。", exc_info=True)
        for col_name in ['tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span']:
            if col_name not in df.columns:
                df[col_name] = float('nan')
    except Exception as e:
        logger.error(f"一目均衡表計算中に予期せぬエラーが発生しました: {e}", exc_info=True)
        for col_name in ['tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span']:
            if col_name not in df.columns:
                df[col_name] = float('nan')

    return df


# --- calculate_macd 関数を追加（または既存のものを修正） ---
def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrameにMACDインジケーターを追加します。
    """
    logger.debug("calculate_macd: 関数が呼び出されました。")
    required_close_column = 'close'
    if required_close_column not in df.columns:
        logger.error(f"MACD計算に必須の'{required_close_column}'列がDataFrameに見つかりません。現在の列: {df.columns.tolist()}")
        df['MACD'] = float('nan')
        df['MACDh'] = float('nan')
        df['MACDs'] = float('nan')
        return df

    try:
        # pandas_ta を使用してMACDを計算
        # デフォルトでは MACD_12_26_9, MACDH_12_26_9, MACDS_12_26_9 のような列名が生成されます。
        df.ta.macd(append=True)
        logger.debug(f"calculate_macd: pandas_ta.macd 実行後のDataFrameの列:\n{df.columns.tolist()}")

        macd_col_name = 'MACD_12_26_9'
        macdh_col_name = 'MACDH_12_26_9'
        macds_col_name = 'MACDS_12_26_9'

        expected_macd_cols = [macd_col_name, macdh_col_name, macds_col_name]
        missing_macd_cols = [col for col in expected_macd_cols if col not in df.columns]

        if missing_macd_cols:
            logger.error(f"MACDの必須列がpandas_taから生成されませんでした。不足している列: {missing_macd_cols}")
            df['MACD'] = float('nan')
            df['MACDh'] = float('nan')
            df['MACDs'] = float('nan')
            return df

        df['MACD'] = df[macd_col_name]
        df['MACDh'] = df[macdh_col_name] # MACD Histogram
        df['MACDs'] = df[macds_col_name] # MACD Signal Line

        logger.debug(f"MACDを計算しました。最終値: MACD={df['MACD'].iloc[-1]:.4f}, MACDh={df['MACDh'].iloc[-1]:.4f}, MACDs={df['MACDs'].iloc[-1]:.4f}")

    except Exception as e:
        logger.error(f"MACD計算中にエラーが発生しました: {e}", exc_info=True)
        df['MACD'] = float('nan')
        df['MACDh'] = float('nan')
        df['MACDs'] = float('nan')

    return df

# --- calculate_stochastic 関数を追加（または既存のものを修正） ---
def calculate_stochastic(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrameにストキャスティクスインジケーターを追加します。
    """
    logger.debug("calculate_stochastic: 関数が呼び出されました。")
    required_ohlc_columns = ['high', 'low', 'close']
    if not all(col in df.columns for col in required_ohlc_columns):
        logger.error(f"ストキャスティクス計算に必須のOHLC列がDataFrameに見つかりません。必要な列: {required_ohlc_columns}, 現在の列: {df.columns.tolist()}")
        df['STOCHk'] = float('nan')
        df['STOCHd'] = float('nan')
        return df

    try:
        # pandas_ta を使用してストキャスティクスを計算
        # デフォルトでは STOCHk_14_3_3, STOCHd_14_3_3 のような列名が生成されます。
        df.ta.stoch(append=True)
        logger.debug(f"calculate_stochastic: pandas_ta.stoch 実行後のDataFrameの列:\n{df.columns.tolist()}")

        stochk_col_name = 'STOCHk_14_3_3'
        stochd_col_name = 'STOCHd_14_3_3'

        expected_stoch_cols = [stochk_col_name, stochd_col_name]
        missing_stoch_cols = [col for col in expected_stoch_cols if col not in df.columns]

        if missing_stoch_cols:
            logger.error(f"ストキャスティクスの必須列がpandas_taから生成されませんでした。不足している列: {missing_stoch_cols}")
            df['STOCHk'] = float('nan')
            df['STOCHd'] = float('nan')
            return df

        df['STOCHk'] = df[stochk_col_name]
        df['STOCHd'] = df[stochd_col_name]

        logger.debug(f"ストキャスティクスを計算しました。最終値: STOCHk={df['STOCHk'].iloc[-1]:.4f}, STOCHd={df['STOCHd'].iloc[-1]:.4f}")

    except Exception as e:
        logger.error(f"ストキャスティクス計算中にエラーが発生しました: {e}", exc_info=True)
        df['STOCHk'] = float('nan')
        df['STOCHd'] = float('nan')

    return df