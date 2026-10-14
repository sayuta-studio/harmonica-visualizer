# -*- coding: utf-8 -*-
# main.py (STEP 2: 起動エントリー ＆ ロギング専用スリム版)
# - 【大デトックス】：起動・パス解決・エラー自白ログのみに責任を持ち、コアアプリを別ファイルへ完全隔離。

import os
import sys
import traceback

def write_crash_log(e_val):
    error_msg = traceback.format_exc()
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(base_dir, "error_log.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=== Chromatic Harmonica Trainer Error Log ===\n")
            f.write(error_msg)
    except Exception:
        pass
    print("\n" + "="*60)
    print("[致命的起動エラー] アプリケーションの起動に失敗しました。")
    print(error_msg)
    print("="*60)
    print("\n詳細は同じフォルダ内の 'error_log.txt' に保存されました。")
    print("確認後、Enterキーを押して画面を閉じてください...")
    input()
    sys.exit(1)

# パス解決（PyInstaller絶対パス解決）
try:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        if sys._MEIPASS not in sys.path:
            sys.path.insert(0, sys._MEIPASS)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
except Exception as e:
    write_crash_log(e)

# 分割されたコアコントローラーのロード
try:
    from app_controller import HarmonicaAppIntegrator
except Exception as e:
    write_crash_log(e)

def main():
    try:
        app = HarmonicaAppIntegrator()
        app.mainloop()
    except Exception as e:
        write_crash_log(e)

if __name__ == "__main__":
    main()