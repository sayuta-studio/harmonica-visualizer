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
    """
    y_offset = canvas_height - 540
    y_center = 460 + y_offset
    y_hole_line = 445 + y_offset

    if "2段階" in str(trajectory_mode) or "2" in str(trajectory_mode):
        y_collide_line = 260 + y_offset
        height_straight = 0
        y_straight_line = y_hole_line
        height_diag = y_straight_line - y_collide_line  # 185
    elif "垂直" in str(trajectory_mode):
        y_collide_line = y_offset
        height_straight = y_hole_line
        y_straight_line = y_offset
        height_diag = 0
    else:
        y_collide_line = 145 + y_offset
        height_straight = HEIGHT_STRAIGHT_ABOVE_HOLE    # 200
        y_straight_line = y_hole_line - height_straight # 245 + y_offset
        height_diag = y_straight_line - y_collide_line  # 100

    return y_center, y_collide_line, y_straight_line, y_hole_line, height_diag, height_straight


def get_visualizer_layout_params(ratio_str, max_w=960, max_h=540):
    """
    親フレームの有効領域 (max_w x max_h) 内にアスペクト比を厳密に維持して最大フィットするように、
    表示用Canvasの物理幅 (width)、物理高さ (height)、および対応する描画スケール (scale) を解決します。
    """
    base_w = 960.0
    base_h = float(get_canvas_height_by_ratio(ratio_str))

    avail_w = max(304.0, float(max_w))
    avail_h = max(240.0, float(max_h))

    scale = min(avail_w / base_w, avail_h / base_h)
    display_w = max(1, int(round(base_w * scale)))
    display_h = max(1, int(round(base_h * scale)))
    exact_scale = display_w / base_w

    return display_w, display_h, exact_scale

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
    elif "14穴" in inst_type:
        visible_indices = list(range(2, 16))
        X_start_draw = 120.0 * scale
        orig_x_start = (72 + 2 * W_PITCH) * scale
        X_shift = orig_x_start - X_start_draw
        X_shift_notes = 48.0 * scale
    elif "12穴" in inst_type or "標準" in inst_type or "バス" in inst_type:
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


def draw_metallic_button_pil_flat(btn_w, btn_h, is_on=False):
    """
    左上に光源をシミュレートした立体的な『扁平縦長ステンレス楕円ボタン』を
    Pillowで生成して返します（スキン自動生成および動画出力のフォールバック描画で共通利用）。
    """
    import math
    from PIL import Image

    img = Image.new("RGBA", (btn_w, btn_h), (0, 0, 0, 0))
    rx = btn_w / 2.0
    ry = btn_h / 2.0
    cx, cy = rx, ry
    pixels = img.load()
    for y_idx in range(btn_h):
        for x_idx in range(btn_w):
            dx = x_idx - cx
            dy = y_idx - cy
            dist_sq = (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry)
            if dist_sq <= 1.0:
                dz = math.sqrt(max(0.0, 1.0 - dist_sq))
                nx, ny, nz = dx / rx, dy / ry, dz
                n_len = math.sqrt(nx * nx + ny * ny + nz * nz)
                if n_len > 0:
                    nx, ny, nz = nx / n_len, ny / n_len, nz / n_len

                lx, ly, lz = -0.5, -0.5, 0.707
                l_len = math.sqrt(lx * lx + ly * ly + lz * lz)
                lx, ly, lz = lx / l_len, ly / l_len, lz / l_len

                dot = nx * lx + ny * ly + nz * lz
                diff = max(0.0, dot)

                r_z = 2.0 * dot * nz - lz
                spec = max(0.0, r_z)
                spec_power = math.pow(spec, 8)

                ambient = 60 if not is_on else 45
                diff_factor = 110 if not is_on else 90
                base_color = ambient + diff * diff_factor + spec_power * 80
                val = min(255, int(base_color))

                edge_dist = 1.0 - math.sqrt(dist_sq)
                alpha = 255
                if edge_dist < 0.1:
                    alpha = int(255 * (edge_dist / 0.1))

                pixels[x_idx, y_idx] = (val, val, val, alpha)
    return img


def get_lever_highlight_color(hex_color):
    """
    スライドレバーONノーツ用の明暗適応ハイライト色を算出します。
    - 明るい色（シアン、黄色、白、明るいパステル等: lum >= 140 または l >= 0.55）:
      明るい地色の上でも埋もれず輪郭がくっきり引き締まる漆黒（#151515）のコントラストライン。
    - 暗い〜中明度色:
      地色の色相を保持しつつ、明度と彩度を引き上げた高輝度ネオン発光ライン。
    """
    import colorsys
    if not hex_color or not str(hex_color).startswith("#"):
        return "#FFFFFF"
    h_str = str(hex_color).lstrip("#")
    if len(h_str) < 6:
        return "#FFFFFF"
    try:
        r = int(h_str[0:2], 16) / 255.0
        g = int(h_str[2:4], 16) / 255.0
        b = int(h_str[4:6], 16) / 255.0
    except ValueError:
        return "#FFFFFF"

    lum = 0.299 * r * 255.0 + 0.587 * g * 255.0 + 0.114 * b * 255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # ユーザー要望：「明度一定以上の場合は暗いラインで、明度一定以下の場合は明るいラインで表示する」
    if lum >= 140.0 or l >= 0.55:
        return "#151515"

    new_l = min(0.95, max(0.85, l + (1.0 - l) * 0.70))
    new_s = max(0.40, min(1.0, s * 0.90)) if s > 0.05 else 0.0
    hr, hg, hb = colorsys.hls_to_rgb(h, new_l, new_s)
    return f"#{int(round(hr * 255.0)):02X}{int(round(hg * 255.0)):02X}{int(round(hb * 255.0)):02X}"


def get_lever_highlight_rgb(hex_color):
    """NumPy/Pillow RGBタプル形式でレバーハイライト色を返します。"""
    hi_hex = get_lever_highlight_color(hex_color).lstrip("#")
    r = int(hi_hex[0:2], 16)
    g = int(hi_hex[2:4], 16)
    b = int(hi_hex[4:6], 16)
    return (r, g, b)


def get_lever_highlight_bgr(hex_color):
    """OpenCV/NumPy BGRタプル形式でレバーハイライト色を返します。"""
    hi_hex = get_lever_highlight_color(hex_color).lstrip("#")
    r = int(hi_hex[0:2], 16)
    g = int(hi_hex[2:4], 16)
    b = int(hi_hex[4:6], 16)
    return (b, g, r)




def generate_default_skins():
    """
    skins/ 内にマウスピース・レバーのPNGスキンが存在しない場合、
    Pillowを用いて、美しく金属光沢を施した画像を動的に生成書き出しします。
    """
    import numpy as np
    from PIL import Image, ImageDraw
    skins_dir = get_portable_path("skins")
    os.makedirs(skins_dir, exist_ok=True)
    
    face_path = os.path.join(skins_dir, "マウスピース.png")  
    lever_off_path = os.path.join(skins_dir, "レバーオフ.png")
    lever_on_path = os.path.join(skins_dir, "レバーオン.png")

    # 1. カバープレート「マウスピース.png」の自立生成
    if not os.path.exists(face_path):
        w, h = 800, 90
        y, x = np.ogrid[:h, :w]
        grad = (x + y * 1.5) / (w + h * 1.5)
        light = np.sin(grad * np.pi * 1.5 - np.pi / 4)
        light = np.clip(light, -0.3, 0.7) + 0.3
        gray_values = 45 + light * 75
        
        tex_np = np.zeros((h, w, 4), dtype=np.uint8)
        tex_np[..., 0] = tex_np[..., 1] = tex_np[..., 2] = gray_values
        tex_np[..., 3] = 255
        
        face_img = Image.fromarray(tex_np, "RGBA")
        mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, w, h], radius=15, fill=255)
        
        final_face = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        final_face.paste(face_img, (0, 0), mask=mask)
        final_face.save(face_path, "PNG")
        print("[システム] skins/マウスピース.png の自動書き出しに成功しました。")

    # 2. スライドレバー「レバーオフ.png」の自立生成 (ステンレス扁平ボタン・通常位置)
    if not os.path.exists(lever_off_path):
        w, h = 48, 48
        lo_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(lo_img)
        draw.rounded_rectangle([0, 16, 24, 32], radius=4, fill="#555555")
        
        btn_w, btn_h = 16, 36
        btn_img = draw_metallic_button_pil_flat(btn_w, btn_h, is_on=False)
        
        btn_mask = Image.new("L", (btn_w, btn_h), 0)
        btn_mask_draw = ImageDraw.Draw(btn_mask)
        btn_mask_draw.ellipse([0, 0, btn_w, btn_h], fill=255)
        
        lo_img.paste(btn_img, (24, 6), mask=btn_mask)
        lo_img.save(lever_off_path, "PNG")
        print("[システム] skins/レバーオフ.png の自動書き出しに成功しました。")

    # 3. スライドレバー「レバーオン.png」の自立生成 (ステンレス扁平ボタン・押し込み位置)
    if not os.path.exists(lever_on_path):
        w, h = 48, 48
        lon_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(lon_img)
        draw.rounded_rectangle([0, 16, 12, 32], radius=4, fill="#3a3a3a")
        
        btn_w, btn_h = 16, 36
        btn_img = draw_metallic_button_pil_flat(btn_w, btn_h, is_on=True)
            
        btn_mask = Image.new("L", (btn_w, btn_h), 0)
        btn_mask_draw = ImageDraw.Draw(btn_mask)
        btn_mask_draw.ellipse([0, 0, btn_w, btn_h], fill=255)
        
        lon_img.paste(btn_img, (12, 6), mask=btn_mask)
        lon_img.save(lever_on_path, "PNG")
        print("[システム] skins/レバーオン.png の自動書き出しに成功しました。")

    import shutil
    for src, dst in [
        ("マウスピース.png", "マウスピース_メタル.png"),
        ("レバーオフ.png", "レバーオフ_シルバー.png"),
        ("レバーオン.png", "レバーオン_シルバー.png"),
    ]:
        s_p = os.path.join(skins_dir, src)
        d_p = os.path.join(skins_dir, dst)
        if os.path.exists(s_p) and not os.path.exists(d_p):
            shutil.copyfile(s_p, d_p)


def format_hole_number(hole_index_0_based: int, inst_type: str = "16穴 (64音・C調)", style: str = "実機標準 (低音ドット付)") -> str:
    """
    穴番号の表示文字列をフォーマット。
    style:
      - "実機標準 (低音ドット付)" / "実機標準"
      - "通し番号 (1〜16)"
    """
    raw_num = hole_index_0_based + 1
    if "通し番号" in str(style):
        return str(raw_num)

    if "16穴" in inst_type:
        if raw_num <= 4:
            return f"·{raw_num}"
        else:
            return str(raw_num - 4)
    elif "14穴" in inst_type:
        if raw_num <= 2:
            return f"·{raw_num}"
        else:
            return str(raw_num - 2)
    else:
        return str(raw_num)
