# -*- coding: utf-8 -*-
# config.py (STEP 4-B: 幾何学定義 ＆ 動的リソースパス解決・物理パス防衛版・運指マップ隔離デトックス後)
# - 【ピクセル等倍幾何学】：等幅60音レーン設計、W_PITCH=48, D_HOLE=30、12穴補正シフト（96.0px）を完備。
# - 【デトックス】：運指マッピングデータ（HARMONICA_MAP）は `harmonica_map.py` へ完全に隔離・移行されました。
# - 🚀【マルチアスペクト比拡張】：アスペクト比に応じた縦幅ピクセル解決、および下部基準で幾何学を上に引き延ばすオフセット解決を追加。
# - 🚀【練習Canvasフィット拡張】：親ウィンドウ内にアスペクト比を維持してレターボックス表示するスケール解決を追加。
# - 🚀【レイアウト下部スライド】：動画素材として扱いやすくするため、ハーモニカ中心および判定線を全体的に40px下にずらし、上空の等速下落レーンを極限まで拡大。
# - 🚀【衝突消滅フチからホール中心へ】：ノーツが本体スキンに当たってすぐ消える不都合を防ぐため、衝突終点 Y_HOLE_LINE をホールの最上端フチ（穴の真上）に完全一致。
# - 🚀【STEP 4.5 レバーサイズUP & 外部マゼンタ追加】：レバー視認性向上のためのサイズスケール定義を追加。

import os
import sys

def resource_path(relative_path):
    """
    PyInstallerワンファイルEXE展開先の一時フォルダ（_MEIPASS）と、
    通常開発時のカレントディレクトリを透過的に自動解決し、安全な絶対パスを返します。
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_portable_path(relative_path):
    """
    UAC保護領域への書き込みクラッシュを完全に先回り防衛するため、
    ユーザーが実際に実行ファイルを配置・実行している物理フォルダ直下の絶対パスを返します。
    """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)

def get_canvas_height_by_ratio(ratio_str):
    """
    アスペクト比文字列から、横幅960基準の縦幅ピクセル数を正確に返します。
    """
    if ratio_str == "9:16":
        return 1706  # 960 * 16 / 9 (縦長ショート)
    elif ratio_str == "4:3":
        return 720   # 960 * 3 / 4 (スタンダード)
    else:
        return 540   # 16:9 (ワイド標準)

def get_y_layout_params(canvas_height):
    """
    全体のキャンバス高さ (canvas_height) に応じて、
    下部基準でハーモニカ幾何学が1ミリも動かず完全不動となるように、
    各Y軸の座標を計算・変換して返します（2段階ビジュアル基準）。
    """
    y_offset = canvas_height - 540
    
    y_center = 460 + y_offset        # 420から40px下げ
    y_collide_line = 260 + y_offset  # 2段階モード標準の収束開始ライン
    y_hole_line = 445 + y_offset     # 衝突終点をホールの最上端（入り口のフチ、穴の真上）へ同期設定！
    height_converge = 185            # 2段階収束高さ（445 - 260 = 185）
    
    return y_center, y_collide_line, y_hole_line, height_converge


def get_y_trajectory_params(canvas_height, trajectory_mode="3段階 (練習標準)"):
    """
    軌道モードに応じたY軸座標パラメータを一元計算して返します。
    - 「3段階 (練習標準)」: 上部垂直(0〜145: 145px) ➔ 斜め収束(145〜245: 100px) ➔ 穴直上ロング垂直(245〜445: 200px)
    - 「2段階 (ビジュアル)」: 上部垂直(0〜260: 260px) ➔ 斜め収束(260〜445: 185px) ➔ 直上垂直なし(0px)
    - 「垂直落下 (穴直上)」: 画面最上部から穴直上まで全区間垂直(0〜445: 445px)
    """
    y_offset = canvas_height - 540
    y_center = 460 + y_offset
    y_hole_line = 445 + y_offset

    if "2段階" in str(trajectory_mode):
        y_collide_line = 260 + y_offset
        height_straight = 0
        y_straight_line = y_hole_line
        height_diag = y_straight_line - y_collide_line  # 185
    else:
        y_collide_line = 145 + y_offset
        height_straight = HEIGHT_STRAIGHT_ABOVE_HOLE    # 200
        y_straight_line = y_hole_line - height_straight # 245 + y_offset
        height_diag = y_straight_line - y_collide_line  # 100

    return y_center, y_collide_line, y_straight_line, y_hole_line, height_diag, height_straight


def get_visualizer_layout_params(ratio_str):
    """
    練習画面の最大表示枠 960x540 内に美しく収まるように、
    表示用Canvasの物理幅 (width)、物理高さ (height)、および対応する縮小描画スケール (scale) を解決します。
    """
    if ratio_str == "9:16":
        display_h = 540
        display_w = 304       
        scale = 304.0 / 960.0 
    elif ratio_str == "4:3":
        display_h = 540
        display_w = 720       
        scale = 720.0 / 960.0
    else:
        display_h = 540
        display_w = 960
        scale = 1.0
        
    return display_w, display_h, scale

# カラーパレット (デフォルト値：SettingsController of テーマ機能によって動的に上書きされます)
COLOR_BLOW_RGB = (255, 85, 0)     # 吹き：オレンジ
COLOR_BLOW_INNER = "#FF9900"     # 吹き：ゴールド (穴の中)
COLOR_DRAW_RGB = (0, 191, 255)    # 吸い：水色・ライトブルー
COLOR_DRAW_INNER = "#00FFFF"     # 吸い：シアン

# レイアウト定数 (ピクセル等倍)
W_PITCH = 48                    # 1穴 of ピッチ幅
D_HOLE = 30                     # 穴 of 直径
Y_CENTER = 460                  # ハーモニカ本体のY軸中心座標 (※16:9基準。アスペクト比可変時は動的オフセット)
X_START_BASE = 72               # 16穴描画時の開始X座標
X_MARGIN_ABSOLUTE = 24          # 左右の絶対マージン余白
CANVAS_WIDTH = 960              # Canvasの横幅 固定
CANVAS_HEIGHT = 540             # Canvas of 縦幅 (※デフォルト16:9)

# 12穴標準/バス選択時の補正量（本体および下落ノーツスライド量）
X_SHIFT_12HOLE = 96.0           

# 衝突終点および収束境界スライドライントラック（穴の真上へ吸着）
Y_COLLIDE_LINE = 145            # 3段階モードの等速下落と斜め収束の境界 (0〜145: 上部垂直145px)
HEIGHT_STRAIGHT_ABOVE_HOLE = 200 # 3段階モードの穴直上ロング垂直落下区間高さ (245〜445: 200px)
Y_STRAIGHT_LINE = 245           # 3段階モードの斜め収束終了・穴直上垂直開始ライン (445 - 200 = 245)
Y_HOLE_LINE = 445               # 物理穴の衝突終点（ホールの最上フチに完全同期）
HEIGHT_CONVERGE = 185           # 2段階モード基準の収束高さ (445 - 260 = 185)
HEIGHT_DIAG_CONVERGE = 100      # 3段階モードの斜め収束区間高さ (245 - 145 = 100)
PIXELS_PER_BEAT = 120           # 1拍あたりの等速下落ピクセル数

# 🚀【解決】：扁平な縦長メタル楕円（16x36）表示のための最大画像キャンバスサイズ
LEVER_WIDTH_DEFAULT = 48        
LEVER_HEIGHT_DEFAULT = 48


def hex_to_rgb(hex_str):
    """HEXカラーコード文字列 (#RRGGBB または #RGB) を (R, G, B) タプルに変換します。"""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def get_layout_params(inst_type, scale=1.0):
    """
    楽器タイプ (16穴 / 12穴標準 / 12穴バス) と描画スケールに応じた
    表示対象ホールインデックス・描画開始X座標・シフト補正量を一元計算して返します。
    """
    if "16穴" in inst_type:
        visible_indices = list(range(16))
        X_start_draw = 72.0 * scale
        X_shift = 0.0
        X_shift_notes = 0.0
    elif "標準" in inst_type or "バス" in inst_type:
        visible_indices = list(range(4, 16))
        X_start_draw = 168.0 * scale
        orig_x_start = (72 + 4 * W_PITCH) * scale
        X_shift = orig_x_start - X_start_draw
        X_shift_notes = X_SHIFT_12HOLE * scale
    else:
        visible_indices = list(range(16))
        X_start_draw = 72.0 * scale
        X_shift = 0.0
        X_shift_notes = 0.0

    return visible_indices, X_start_draw, X_shift, X_shift_notes


def get_note_dest_x(note, inst_type, scale=1.0, start_tick=0):
    """
    指定された楽器タイプ・Tick位置での、着地目標穴内4分割領域の
    最終着地X座標（シフト補正およびスケール連動済み）を一元計算して返します。
    """
    from harmonica_map import get_note_fingering_for_song
    fingering = get_note_fingering_for_song(start_tick, note, inst_type)
    if not fingering:
        return 480.0 * scale

    _, _, X_shift, _ = get_layout_params(inst_type, scale)

    hole = fingering["hole"]
    action = fingering["action"]
    lever = fingering["lever"]

    hole_idx = hole - 1
    W_pitch_s = W_PITCH * scale
    center_x_absolute = (72.0 * scale) + (hole_idx * W_pitch_s) + (W_pitch_s / 2.0)

    if hole == 16:
        pattern = 3
    elif hole in [4, 8, 12]:
        pattern = 2
    else:
        pattern = 1

    if pattern == 1:
        if action == "吹" and lever == "OFF": offset = -18.0 * scale
        elif action == "吹" and lever == "ON":  offset = -6.0 * scale
        elif action == "吸" and lever == "OFF": offset = 6.0 * scale
        elif action == "吸" and lever == "ON":  offset = 18.0 * scale
        else: offset = 0.0
    elif pattern == 2:
        if action == "吸" and lever == "OFF": offset = -18.0 * scale
        elif action == "吸" and lever == "ON":  offset = -6.0 * scale
        elif action == "吹" and lever == "OFF": offset = 6.0 * scale
        elif action == "吹" and lever == "ON":  offset = 18.0 * scale
        else: offset = 0.0
    elif pattern == 3:
        if action == "吸" and lever == "OFF": offset = -18.0 * scale
        elif action == "吹" and lever == "OFF": offset = -6.0 * scale
        elif action == "吹" and lever == "ON":  offset = 6.0 * scale
        elif action == "吸" and lever == "ON":  offset = 18.0 * scale
        else: offset = 0.0
    else:
        offset = 0.0

    dest_x = center_x_absolute + offset - X_shift
    return dest_x
