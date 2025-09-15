import tkinter as tk
from PIL import Image, ImageTk
import subprocess
import threading
import time
import requests
import webbrowser
import os
from playsound import playsound 

# --- 設定 ---
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
# 仮想環境の python.exe を使用
PYTHON_EXE = os.path.join(PROJECT_PATH, 'venv', 'Scripts', 'pythonw.exe') 
APP_SCRIPT = os.path.join(PROJECT_PATH, 'app.py')
SERVER_URL = "http://127.0.0.1:5000"
# Microsoft Edgeの正確なパスを設定
BROWSER_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" 
BROWSER_ARGS = ['--profile-directory=Default']
BG_IMAGE_PATH = os.path.join(PROJECT_PATH, 'static', 'bg_cyber_alt2.png')
SE_FILE_PATH = os.path.join(PROJECT_PATH, 'static', 'click.mp3') 
MIN_DISPLAY_TIME_MS = 5000 

# --- グローバル変数 ---
server_ready = threading.Event()
is_blinking = True

# --- GUI作成 ---
root = tk.Tk()
root.attributes('-fullscreen', True)
root.attributes('-topmost', True)
root.configure(bg='#1a1a2e')

try:
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    bg_image_pil = Image.open(BG_IMAGE_PATH).resize((screen_width, screen_height), Image.Resampling.LANCZOS)
    bg_image_tk = ImageTk.PhotoImage(bg_image_pil)
    bg_label = tk.Label(root, image=bg_image_tk, borderwidth=0)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
except Exception as e:
    print(f"警告: 背景画像が読み込めませんでした: {e}")

loading_label = tk.Label(
    root, text="Now Loading...", font=("Orbitron", 40, "bold"),
    fg="#00FF99", bg='#1a1a2e'
)
loading_label.place(relx=0.98, rely=0.95, anchor='se')

# --- 機能定義 ---
def run_backend():
    print("バックエンドサーバーを起動します...")
    # ★★★ 修正点: subprocess.call() を Popen() に変更 ★★★
    # これにより、バックエンドの起動中にGUIがフリーズするのを防ぎます
    subprocess.Popen([PYTHON_EXE, APP_SCRIPT], creationflags=subprocess.CREATE_NO_WINDOW)

def check_server():
    while not server_ready.is_set():
        try:
            requests.get(SERVER_URL, timeout=1)
            print("サーバーの準備が完了しました。")
            server_ready.set()
        except requests.ConnectionError:
            time.sleep(1)

def fade_out_and_exit(alpha=1.0):
    global is_blinking
    is_blinking = False
    if alpha > 0:
        root.attributes('-alpha', alpha)
        alpha -= 0.05
        root.after(40, lambda: fade_out_and_exit(alpha))
    else:
        root.destroy()

def start_main_app():
    server_ready.wait() 
    print("ブラウザを起動し、ローディング画面を閉じます。")
    try:
        command = [BROWSER_PATH] + BROWSER_ARGS + [SERVER_URL]
        subprocess.Popen(command)
    except Exception as e:
        print(f"ブラウザの起動に失敗しました: {e}")
    fade_out_and_exit()

def toggle_loading_label():
    if is_blinking:
        current_text = loading_label.cget('text')
        if current_text:
            loading_label.config(text="")
        else:
            loading_label.config(text="Now Loading...")
        root.after(800, toggle_loading_label)

def play_se():
    """ 効果音を再生する """
    try:
        playsound(SE_FILE_PATH)
    except Exception as e:
        print(f"警告: 効果音 '{SE_FILE_PATH}' の再生に失敗しました: {e}")

# --- メイン実行 ---
if __name__ == '__main__':
    # run_backendをメインスレッドで直接呼び出し、非同期に子プロセスを起動する
    # threading.Thread(target=run_backend, daemon=True).start() は不要になる
    run_backend() 
    threading.Thread(target=check_server, daemon=True).start()
    threading.Thread(target=play_se, daemon=True).start()
    root.after(MIN_DISPLAY_TIME_MS, start_main_app)
    toggle_loading_label()
    root.mainloop()