import os
import time
from datetime import datetime, timedelta

# === 設定 ===
# チャート画像を保存しているディレクトリ
CHARTS_DIR = "static/charts"
# ログファイルを保存しているディレクトリ
LOG_DIR = "static"
# 保持日数
KEEP_DAYS = 30

# === 削除処理 ===
def cleanup_old_files(target_dir, extensions=None):
    """
    指定ディレクトリ内の古いファイルを削除する
    :param target_dir: 掃除対象のディレクトリ
    :param extensions: 拡張子フィルタ（例: ['.png', '.log']）。Noneなら全ファイル対象。
    """
    now = time.time()
    cutoff = now - (KEEP_DAYS * 86400)

    if not os.path.exists(target_dir):
        print(f"ディレクトリが存在しません: {target_dir}")
        return

    for filename in os.listdir(target_dir):
        file_path = os.path.join(target_dir, filename)
        if os.path.isfile(file_path):
            # 拡張子フィルタ
            if extensions and not any(filename.lower().endswith(ext) for ext in extensions):
                continue

            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff:
                try:
                    os.remove(file_path)
                    print(f"削除: {file_path}")
                except Exception as e:
                    print(f"削除失敗: {file_path} ({e})")

# === 実行 ===
if __name__ == "__main__":
    print(f"古いファイルを削除します（保持日数: {KEEP_DAYS}日）")

    # チャート画像削除
    cleanup_old_files(CHARTS_DIR, extensions=[".png"])

    # ログ削除
    cleanup_old_files(LOG_DIR, extensions=[".log", ".txt"])

    print("クリーンアップ完了")
