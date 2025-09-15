import json
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # デフォルトをINFOに設定

# handlersをクリアして再設定 (app.pyのロギング設定と競合しないように)
if logging.root.handlers:
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def load_json_file(filepath):
    """
    指定されたJSONファイルを読み込んで辞書として返す。
    ファイルが存在しない場合は空の辞書を返す。
    """
    if not os.path.exists(filepath):
        logger.warning(f"⚠ JSONファイルが存在しません: {filepath}")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析エラー（{filepath}）: {e}")
        return {}
    except Exception as e:
        logger.error(f"❌ JSON読み込みエラー（{filepath}）: {e}")
        return {}

def save_json_file(filepath, data):
    """
    データ（辞書）をJSON形式で指定ファイルに保存する。
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"✅ JSONファイルを保存しました: {filepath}")
    except Exception as e:
        logger.error(f"❌ JSON保存エラー（{filepath}）: {e}")