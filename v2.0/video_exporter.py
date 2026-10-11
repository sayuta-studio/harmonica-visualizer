# -*- coding: utf-8 -*-
# video_exporter.py (STEP 4-B: オフライン高画質動画出力・消音マージン完全撤廃・バグ根治版)
# - 【同時点灯完全根治】：消音時の0.25秒マージンを完全撤廃。余韻のすれ違いによる「新旧の穴が同時にピカピカ点灯してしまう」バグを動画エクスポート側でも100%完全に根絶しました。
# - 【C#残骸完全消滅】：get_note_dest_x_exporterに混入していたC#強制書き換え補正残骸を完全に一掃。ドシャープがデフォルトで不自然に隣の1オクターブ下に下落する問題を解決しました。
# - 🚀【マルチアスペクト・スキン拡張】：16:9 / 9:16 / 4:3 解像度動的解決、および skins/ 透過PNGスキンの100%精密アルファペースト合成を完全統合。
# - 🚀【マウスピーススキン化】：スキンのファイル名を「マウスピース.png」へ完全連動リネーム。
# - 🚀【穴番号内寄せ ＆ 音名外出し】：Pillow/OpenCV 側の描画位置も visualizer.py と完全同期し、穴番号をホール直下（+24px）、音名をプレート外（+60px）へと入れ替え補正。
# - 🚀【書き出し中止の物理解放】：スレッド開始時の export_btn 強制無効化（disabled）およびスレッド内でのボタン直接制御を全廃。完了/中止後のクリーンアップ終了コールバックを新設。
# - 🚀【ハードコーディングの撤廃】：apply_opencv_vector_notes_draw内の直書き定数を廃止し、get_y_layout_paramsのリアルタイム同期へ大転換。
# - 🚀【レバー不動パラパラ＆48px化】：レバーON時のXスライド座標変化を全廃(オフセットゼロ不動)。リサイズサイズを 48x48px へサイズアップ。
# - 🚀【FFmpeg鉄壁例外防衛フォールバック】：音声マージ失敗時、映像と音声を別々の独立ファイルとして output/ 内に安全退避書き出し。
# - 🚀【ガイド線バグ修復】：ノーツ非表示時でも、ガイド線がオンであれば、内側の等幅グリッドガイドが動画内へ確実に美しくレンダリングされるように修正。
# - 🚀【フォールバック3Dメタル扁平化】：スキンOFF時でも赤・黄を廃止し、ステンレスカラーで、16x36pxの比率を持つ美しい扁平縦長楕円のパラパラ沈み込み描画へ一本化！
# - 🚀【面取り左上崩れ完全治療】：過去のデバッグプリントの残骸が引き起こしていた左上の頂点抜け落ちを、pts_accum.append([lane_x_left, int(y_top + ch)]) へ完全に復元修復！
# - 🚀【Pillow逆転バグ ＆ CTkImage警告根治】：シャフト開始座標をプレート右端に完全吸着させ浮き隙間を解決。プレビュー表示を CTkImage 構築へ切り替え。
# - 🚀【ベクターストローク大拡張同期】：スキンOFF時のベクター表示でも、本体からの隙間を「OFF時：22px」「ON時：3px」に同期。X移動なしで19pxの巨大沈み込みを表現！

import os
import sys
import time
import subprocess
import threading
import traceback
import numpy as np
import math

try:
    import cv2
    import customtkinter as ctk
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("[警告] opencv-python, pillow または customtkinter が見つかりません。")

_CACHE = {
    "key": None,          
    "base_image": None,   
}

from audio_engine import synthesize_midi_to_wav
from config import (
    COLOR_BLOW_RGB, COLOR_BLOW_INNER,
    COLOR_DRAW_RGB, COLOR_DRAW_INNER,
    W_PITCH, D_HOLE, CANVAS_WIDTH, CANVAS_HEIGHT,
    get_y_layout_params, get_portable_path,
    LEVER_WIDTH_DEFAULT, LEVER_HEIGHT_DEFAULT
)
from harmonica_map import (
    is_note_in_range, get_note_name, get_note_fingering_for_song
)

def resolve_resolution_and_scale(res_mode, aspect_ratio):
    """
    解像度モードと指定のアスペクト比から、エクスポートされる動画の
    最終的な物理幅 (width)、物理高さ (height)、および横幅基準スケール (scale) を正確に解決します。
    """
    if "4K" in res_mode or "3840x2160" in res_mode:
        base_h = 2160
    elif "1920x1080" in res_mode:
        base_h = 1080
    elif "1280x720" in res_mode:
        base_h = 720
    else:
        base_h = 540

    if aspect_ratio == "9:16":
        height = base_h
        width = int(base_h * 9 / 16)
        scale = width / 960.0
    elif aspect_ratio == "4:3":
        height = base_h
        width = int(base_h * 4 / 3)
        scale = width / 960.0
    else:
        height = base_h
        width = int(base_h * 16 / 9)
        scale = width / 960.0

    return width, height, scale


def get_layout_params_exporter(inst_type, scale=1.0):
    W_pitch_s = W_PITCH * scale
    
    if "16穴" in inst_type:
        visible_indices = list(range(16))
        X_start_draw = 72 * scale
        X_shift = 0.0
        X_shift_notes = 0.0
    elif "標準" in inst_type or "バス" in inst_type:
        visible_indices = list(range(4, 16)) 
        X_start_draw = 168.0 * scale
        plate_w = (12 * W_PITCH + 30) * scale
        orig_x_start = (72 + 4 * W_PITCH) * scale
        X_shift = orig_x_start - X_start_draw
        X_shift_notes = 96.0 * scale
    else:
        visible_indices = list(range(16))
        X_start_draw = 72 * scale
        X_shift = 0.0
        X_shift_notes = 0.0
        
    return visible_indices, X_start_draw, X_shift, X_shift_notes


def get_note_dest_x_exporter(note, inst_type, scale=1.0, start_tick=0):
    """video_exporter専用：指定された楽器タイプでの、最終着地X座標を正確に計算します。"""
    fingering = get_note_fingering_for_song(start_tick, note, inst_type)
    if not fingering:
        return 480 * scale
    
    _, X_start_draw, X_shift, _ = get_layout_params_exporter(inst_type, scale)
    
    hole = fingering["hole"]
    action = fingering["action"]
    lever = fingering["lever"]
    
    hole_idx = hole - 1
    W_pitch_s = W_PITCH * scale
    center_x_absolute = (72 * scale) + (hole_idx * W_pitch_s) + (W_pitch_s / 2)
    
    if hole == 16:
        pattern = 3
    elif hole in [4, 8, 12]:
        pattern = 2
    else:
        pattern = 1
        
    if pattern == 1:
        if action == "吹" and lever == "OFF": offset = -18 * scale
        elif action == "吹" and lever == "ON":  offset = -6 * scale
        elif action == "吸" and lever == "OFF": offset = 6 * scale
        elif action == "吸" and lever == "ON":  offset = 18 * scale
        else: offset = 0
    elif pattern == 2:
        if action == "吸" and lever == "OFF": offset = -18 * scale
        elif action == "吸" and lever == "ON":  offset = -6 * scale
        elif action == "吹" and lever == "OFF": offset = 6 * scale
        elif action == "吹" and lever == "ON":  offset = 18 * scale
        else: offset = 0
    elif pattern == 3:
        if action == "吸" and lever == "OFF": offset = -18 * scale
        elif action == "吹" and lever == "OFF": offset = -6 * scale
        elif action == "吹" and lever == "ON":  offset = 6 * scale
        elif action == "吸" and lever == "ON":  offset = 18 * scale
        else: offset = 0
    else:
        offset = 0
        
    dest_x = center_x_absolute + offset - X_shift
    return dest_x


def get_truetype_font(font_name, size):
    try:
        if os.name == 'nt':
            font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", font_name)
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, int(size))
        return ImageFont.truetype("arial.ttf", int(size))
    except Exception:
        return ImageFont.load_default()


def generate_metallic_texture(width, height):
    try:
        y, x = np.ogrid[:height, :width]
        grad = (x + y * 1.5) / (width + height * 1.5)
        light = np.sin(grad * np.pi * 1.5 - np.pi / 4)
        light = np.clip(light, -0.3, 0.7) + 0.3
        gray_values = 45 + light * 75
        texture_np = np.zeros((height, width, 4), dtype=np.uint8)
        texture_np[..., 0] = gray_values
        texture_np[..., 1] = texture_np[..., 2] = gray_values
        texture_np[..., 3] = 255
        return Image.fromarray(texture_np, "RGBA")
    except Exception:
        return Image.new("RGBA", (width, height), "#4e5154")


def draw_glow_ring(draw, x, y, r_max, color_rgb, max_alpha=245):
    for r in range(int(r_max), 0, -2):
        alpha = int(max_alpha * (1.0 - r / r_max) ** 1.1)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(color_rgb[0], color_rgb[1], color_rgb[2], alpha))


def draw_glow_pieslice(draw, x, y, r_max, color_rgb, max_alpha=160):
    for r in range(int(r_max), 0, -2):
        alpha = int(max_alpha * (1.0 - r / r_max) ** 1.1)
        draw.pieslice([x - r, y - r, x + r, y + r], start=180, end=360, fill=(color_rgb[0], color_rgb[1], color_rgb[2], alpha))


def draw_bordered_text_pillow(draw, position, text, text_color, font, border_width=2):
    x, y = position
    border_color = (0, 0, 0, 255)
    border_width = int(border_width)
    for dx in range(-border_width, border_width + 1):
        for dy in range(-border_width, border_width + 1):
            draw.text((x + dx, y + dy), text, fill=border_color, font=font, anchor="mm")
    draw.text((x, y), text, fill=text_color, font=font, anchor="mm")


def hex_to_rgb_exporter(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = "".join(c*2 for c in hex_str)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def draw_harmonica_pillow_frame_exporter(width, height, scale, canvas_bg_color, inst_type, lang_seg_value, 
                                         is_hole_num_on, is_legend_on, is_notes_on, is_grid_on,
                                         note_opacity_value, midi_notes=None, current_time=0.0, current_bpm=120.0, 
                                         active_pitches=None, show_glow_effect=True,
                                         color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                                         use_skin=True):
    """
    オフライン書き出し専用：Pillowの高度なレイヤー合成をフル稼働させ、基本フレームパーツのみを描画。
    外部スキン（PNG）が指定されている場合は、透過アルファチャネルを100%美しくレイヤーブレンドします。
    """
    if active_pitches is None: active_pitches = set()
    if midi_notes is None: midi_notes = []

    y_center_s, y_collide_s, y_hole_line_s, height_converge_s = get_y_layout_params(height / scale)
    y_center_s *= scale
    y_collide_s *= scale
    y_hole_line_s *= scale
    height_converge_s *= scale

    W_pitch_s = W_PITCH * scale
    D_hole_s = D_HOLE * scale

    visible_indices, X_start_draw, X_shift, X_shift_notes = get_layout_params_exporter(inst_type, scale)
    N_visible = len(visible_indices)
    total_width = N_visible * W_pitch_s

    color_blow_rgb = hex_to_rgb_exporter(color_blow_hex)
    color_draw_rgb = hex_to_rgb_exporter(color_draw_hex)

    cache_key = f"{inst_type}_{canvas_bg_color}_{is_notes_on}_{is_grid_on}_{width}_{height}"

    global _CACHE
    if _CACHE["key"] != cache_key or _CACHE["base_image"] is None:
        base_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        base_draw = ImageDraw.Draw(base_img)

        if canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00":
            base_draw.rectangle([0, 0, width, height], fill=(0, 255, 0, 255))
        elif canvas_bg_color == "ブルーバック" or canvas_bg_color == "#0000FF":
            base_draw.rectangle([0, 0, width, height], fill=(0, 0, 255, 255))
        elif canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF":
            base_draw.rectangle([0, 0, width, height], fill=(255, 0, 255, 255))
        else:
            base_draw.rectangle([0, 0, width, height], fill=(13, 13, 13, 255))

        # Pillow（エクスポート映像）のベース背景でも、ガイド線トグルがONであれば、内側等幅グリッドを完全に描画！
        if is_grid_on:
            grid_alpha = 15 if (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00" or canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF") else 25
            grid_color = (0, 0, 0, grid_alpha) if (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00" or canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF") else (255, 255, 255, grid_alpha)
            for idx in range(58):
                x_pos = (24 + idx * 16) * scale
                base_draw.line([(x_pos, 0), (x_pos, y_collide_s)], fill=grid_color, width=max(1, int(1 * scale)))

            grid_line_color = (0, 0, 0, 40) if (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00" or canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF") else (255, 255, 255, 25)
            base_draw.line([(24 * scale, 0), (24 * scale, y_collide_s)], fill=grid_line_color, width=max(1, int(1 * scale)))
            base_draw.line([(936 * scale, 0), (936 * scale, y_collide_s)], fill=grid_line_color, width=max(1, int(1 * scale)))

        _CACHE["key"] = cache_key
        _CACHE["base_image"] = base_img

    frame_img = _CACHE["base_image"].copy()
    draw_img = ImageDraw.Draw(frame_img)

    lever_pressed = False
    playing_holes_data = {}
    
    currently_active_notes = []
    if midi_notes and active_pitches:
        for note_data in midi_notes:
            n_start_time = note_data.get("start_time", 0.0)
            n_dur_time = note_data.get("duration", 0.0)
            if note_data["note"] in active_pitches and n_start_time <= current_time < (n_start_time + n_dur_time):
                currently_active_notes.append(note_data)

    for note_data in currently_active_notes:
        fingering = note_data.get("fingering") 
        if fingering:
            playing_holes_data[fingering["hole"]] = fingering["action"] 
            if fingering["lever"] == "ON": 
                lever_pressed = True

    # 動画エクスポート側でもX軸の平行移動スライドを完全廃止(移動オフセット常にゼロ)！
    lever_x_offset = 0
    # 🚀【解決】：不自然な +15px の隙間（軸離れ・ボタン浮き）を完全廃止！
    # 軸の左端（開始点）はプレートの真右端（X_start_draw + total_width）へピタッと完全吸着させます。
    lever_left = (X_start_draw + total_width)
    
    skins_dir = get_portable_path("skins")
    lever_off_path = os.path.join(skins_dir, "レバーオフ.png")
    lever_on_path = os.path.join(skins_dir, "レバーオン.png")
    face_path = os.path.join(skins_dir, "マウスピース.png")  

    has_lever_skin = use_skin and os.path.exists(lever_off_path) and os.path.exists(lever_on_path)

    # 🚀 扁平な縦長ステンレスクロームボタンをPillow上でリアルタイムに3D光源物理レンダリングする関数
    def draw_metallic_button_pil_flat_local(btn_w, btn_h, is_on=False):
        img = Image.new("RGBA", (btn_w, btn_h), (0,0,0,0))
        rx = btn_w / 2.0
        ry = btn_h / 2.0
        cx, cy = rx, ry
        pixels = img.load()
        for y_idx in range(btn_h):
            for x_idx in range(btn_w):
                dx = x_idx - cx
                dy = y_idx - cy
                dist_sq = (dx*dx)/(rx*rx) + (dy*dy)/(ry*ry)
                if dist_sq <= 1.0:
                    dz = math.sqrt(max(0.0, 1.0 - dist_sq))
                    nx, ny, nz = dx / rx, dy / ry, dz
                    n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
                    if n_len > 0:
                        nx, ny, nz = nx/n_len, ny/n_len, nz/n_len
                    
                    lx, ly, lz = -0.5, -0.5, 0.707
                    l_len = math.sqrt(lx*lx + ly*ly + lz*lz)
                    lx, ly, lz = lx/l_len, ly/l_len, lz/l_len
                    
                    dot = nx*lx + ny*ly + nz*lz
                    diff = max(0.0, dot)
                    
                    r_x = 2.0 * dot * nx - lx
                    r_y = 2.0 * dot * ny - ly
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

    if has_lever_skin:
        try:
            target_path = lever_on_path if lever_pressed else lever_off_path
            pil_lever = Image.open(target_path).convert("RGBA")
            lever_w = int(LEVER_WIDTH_DEFAULT * scale)
            lever_h = int(LEVER_HEIGHT_DEFAULT * scale)
            pil_lever_resized = pil_lever.resize((lever_w, lever_h), Image.Resampling.LANCZOS)
            
            lever_y = int(y_center_s - lever_h / 2)
            # スキン画像ペースト時は、プレート右端から +15px（マージン）の位置で変わらず完全にピッタリ重ね合わされます。
            frame_img.paste(pil_lever_resized, (int(lever_left + 15 * scale), lever_y), mask=pil_lever_resized)
        except Exception as ex:
            has_lever_skin = False
            print(f"[警告] レバースキン合成に失敗しました: {ex}")

    # 🚀【解決】：スキン不使用（use_skinオフ）のフォールバックレンダリング時でも、
    # 赤・黄を完全に全廃し、美しいステンレスカラーで、16x36pxの比率を持つ美しい扁平縦長楕円のパラパラ沈み込み描画へ一本化！
    # 軸の左端開始座標を「マウスピースプレートの真右端（隙間0）」にピタッと完全吸着させ、x1 >= x0 の逆転バグを物理的に完全根絶！
    # さらに通常（OFF）時は隙間を 22px 離し、押し込み（ON）時は 3px まで限界密着させて 19px のダイナミックストロークをビデオ側でも完全同期！
    if not has_lever_skin:
        btn_w = int(16 * scale)
        btn_h = int(36 * scale)
        if lever_pressed:
            # 🚀 押し込みON時：軸x0=プレート右端(隙間0)、軸x1=プレート右端+12*scale（逆転しない）、3Dステンレスボタン左寄せ（X=3*scaleに配置）
            draw_img.rounded_rectangle([lever_left, y_center_s - 12 * scale, lever_left + 12 * scale, y_center_s + 12 * scale], radius=int(4 * scale), fill=(58, 58, 58, 255))
            btn_img = draw_metallic_button_pil_flat_local(btn_w, btn_h, is_on=True)
            frame_img.paste(btn_img, (int(lever_left + 3 * scale), int(y_center_s - btn_h/2)), mask=btn_img)
        else:
            # 🚀 OFF通常時：軸x0=プレート右端(隙間0)、軸x1=プレート右端+24*scale、3Dステンレスボタン右寄せ（X=22*scaleに配置）
            draw_img.rounded_rectangle([lever_left, y_center_s - 12 * scale, lever_left + 24 * scale, y_center_s + 12 * scale], radius=int(4 * scale), fill=(85, 85, 85, 255))
            btn_img = draw_metallic_button_pil_flat_local(btn_w, btn_h, is_on=False)
            frame_img.paste(btn_img, (int(lever_left + 22 * scale), int(y_center_s - btn_h/2)), mask=btn_img)
            
        draw_img = ImageDraw.Draw(frame_img) # 再同期

    plate_w = int(total_width + 30 * scale)
    plate_h = int(90 * scale)
    has_face_skin = use_skin and os.path.exists(face_path)

    if has_face_skin:
        try:
            pil_face = Image.open(face_path).convert("RGBA")
            pil_face_resized = pil_face.resize((plate_w, plate_h), Image.Resampling.LANCZOS)
            frame_img.paste(pil_face_resized, (int(X_start_draw - 15 * scale), int(y_center_s - 45 * scale)), mask=pil_face_resized)
            draw_img = ImageDraw.Draw(frame_img)
        except Exception as ex:
            has_face_skin = False
            print(f"[警告] カバープレートスキン合成に失敗しました: {ex}")

    if not has_face_skin:
        metallic_plate_img = generate_metallic_texture(plate_w, plate_h)
        plate_mask = Image.new("L", (plate_w, plate_h), 0)
        plate_mask_draw = ImageDraw.Draw(plate_mask)
        plate_mask_draw.rounded_rectangle([0, 0, plate_w, plate_h], radius=int(15 * scale), fill=255)

        metallic_plate = Image.new("RGBA", (plate_w, plate_h))
        metallic_plate.paste(metallic_plate_img, (0, 0), mask=plate_mask)
        
        frame_img.paste(metallic_plate, (int(X_start_draw - 15 * scale), int(y_center_s - 45 * scale)), mask=metallic_plate)
        draw_img = ImageDraw.Draw(frame_img)

    for k, idx in enumerate(visible_indices):
        x_center = X_start_draw + k * W_pitch_s + (W_pitch_s / 2)
        draw_img.ellipse(
            [x_center - (D_hole_s/2), y_center_s - (D_hole_s/2),
             x_center + (D_hole_s/2), y_center_s + (D_hole_s/2)],
            fill="#080808", outline="#333333", width=1
        )

    if is_legend_on:
        legend_x_start = 770 * scale
        draw_img.rectangle([legend_x_start, 30 * scale, legend_x_start + 140 * scale, 75 * scale], fill=(28, 28, 28, 255), outline=(0, 0, 0, 255), width=int(2 * scale))
        draw_img.ellipse([legend_x_start + 12 * scale, 40 * scale, legend_x_start + 22 * scale, 50 * scale], fill=color_blow_rgb)
        draw_img.ellipse([legend_x_start + 12 * scale, 55 * scale, legend_x_start + 22 * scale, 65 * scale], fill=color_draw_rgb)
        
        draw_bordered_text_pillow(draw_img, (legend_x_start + 80 * scale, 45 * scale), "吹", "#FFFFFF", get_truetype_font("msgothic.ttc", 10 * scale), border_width=1.5 * scale)
        draw_bordered_text_pillow(draw_img, (legend_x_start + 80 * scale, 60 * scale), "吸", "#FFFFFF", get_truetype_font("msgothic.ttc", 10 * scale), border_width=1.5 * scale)

    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    
    for k, idx in enumerate(visible_indices):
        x_center = X_start_draw + k * W_pitch_s + (W_pitch_s / 2)
        
        visible_hole_number_absolute = visible_indices[k] + 1
        is_active = visible_hole_number_absolute in playing_holes_data

        if is_active:
            action = playing_holes_data[visible_hole_number_absolute]
            glow_color = color_blow_rgb if action == "吹" else color_draw_rgb
            draw_glow_ring(glow_draw, x_center, y_center_s, r_max=int(22 * scale), color_rgb=glow_color, max_alpha=245)
            
            if show_glow_effect:
                draw_glow_pieslice(glow_draw, x_center, y_hole_line_s, r_max=int(32 * scale), color_rgb=(255, 255, 255), max_alpha=210)

    frame_img = Image.alpha_composite(frame_img, glow_layer)
    draw_img = ImageDraw.Draw(frame_img) 

    f_num = get_truetype_font("arial.ttf", 11 * scale)
    f_note = get_truetype_font("meiryo.ttc", 11 * scale)
    
    for k, idx in enumerate(visible_indices):
        x_center = X_start_draw + k * W_pitch_s + (W_pitch_s / 2)
        hole_number = k + 1
        
        if is_hole_num_on:
            draw_bordered_text_pillow(draw_img, (x_center, y_center_s + 24 * scale), str(hole_number), "#FFFFFF", f_num, border_width=2 * scale)

        if lang_seg_value != "なし":
            active_pitches_list = list(active_pitches)
            current_note = None
            for p in active_pitches_list:
                note_start_tick = 0
                if currently_active_notes:
                    for note_data in currently_active_notes:
                        if note_data["note"] == p:
                            note_start_tick = note_data.get("start_tick", 0)
                            break
                            
                fing = get_note_fingering_for_song(note_start_tick, p, inst_type)
                visible_hole_number_absolute = visible_indices[k] + 1
                if fing and fing["hole"] == visible_hole_number_absolute:
                    current_note = p
                    break
            
            if current_note is not None:
                note_text = get_note_name(current_note, is_japanese=("ドレミ" in lang_seg_value))
                text_color = "#FFFFFF"
            else:
                blow_notes_midi = {
                    "16穴": [48, 52, 55, 60, 60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96],
                    "12穴 標準": [60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96], 
                    "12穴 バス": [24, 28, 31, 35, 36, 40, 43, 47, 48, 52, 55, 59]
                }
                mode_key = "16穴" if "16穴" in inst_type else ("12穴 標準" if "標準" in inst_type else "12穴 バス")
                note_text = get_note_name(blow_notes_midi[mode_key][k], is_japanese=("ドレミ" in lang_seg_value))
                text_color = "#000000" if (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00" or canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF") else "#AAAAAA"
                
            draw_bordered_text_pillow(draw_img, (x_center, y_center_s + 60 * scale), note_text, text_color, f_note, border_width=2 * scale)

    return frame_img


def execute_single_frame_preview(midi_notes, current_bpm, current_time,
                                 res_mode, inst_type, notation_mode, bg_color, 
                                 is_hole_num_on, is_legend_on, is_notes_on, is_grid_on, is_glow_on, note_opacity,
                                 parent_window, color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                                 aspect_ratio="16:9", use_skin=True):
    if not OPENCV_AVAILABLE:
        return

    width, height, scale = resolve_resolution_and_scale(res_mode, aspect_ratio)

    try:
        opacity_val = float(note_opacity) / 100.0
    except Exception:
        opacity_val = 0.5

    active_pitches = set()
    for note_data in midi_notes:
        start_t = note_data["start_time"]
        end_t = start_t + note_data["duration"]
        if start_t <= current_time < end_t:
            active_pitches.add(note_data["note"])

    pil_frame = draw_harmonica_pillow_frame_exporter(
        width=width,
        height=height,
        scale=scale,
        canvas_bg_color=bg_color,
        inst_type=inst_type,
        lang_seg_value=notation_mode,
        is_hole_num_on=is_hole_num_on,               
        is_legend_on=is_legend_on,                   
        is_notes_on=False,                           
        is_grid_on=is_grid_on,                       
        note_opacity_value=opacity_val,
        midi_notes=midi_notes,
        current_time=current_time,
        current_bpm=current_bpm,
        active_pitches=active_pitches,
        show_glow_effect=is_glow_on,
        color_blow_hex=color_blow_hex,                
        color_draw_hex=color_draw_hex,
        use_skin=use_skin
    )

    if aspect_ratio == "9:16":
        preview_h = 540
        preview_w = int(540 * 9 / 16)
    elif aspect_ratio == "4:3":
        preview_h = 540
        preview_w = int(540 * 4 / 3)
    else:
        preview_h = 540
        preview_w = 960

    resized_pil = pil_frame.resize((preview_w, preview_h), Image.Resampling.LANCZOS)
    
    preview_canvas = Image.new("RGB", (960, 540), (20, 20, 20))
    preview_canvas.paste(resized_pil, ((960 - preview_w)//2, (540 - preview_h)//2))

    bgr_frame = cv2.cvtColor(np.array(preview_canvas), cv2.COLOR_RGB2BGR)
    
    bgr_notes_part = cv2.cvtColor(np.array(resized_pil), cv2.COLOR_RGB2BGR)
    bgr_notes_part = apply_opencv_vector_notes_draw(
        bgr_frame=bgr_notes_part,
        width=preview_w,
        height=preview_h,
        scale=preview_w / 960.0,
        inst_type=inst_type,
        midi_notes=midi_notes,
        current_time=current_time,
        current_bpm=current_bpm,
        active_pitches=active_pitches,
        note_opacity_value=opacity_val,
        color_blow_hex=color_blow_hex,
        color_draw_hex=color_draw_hex,
        aspect_ratio=aspect_ratio
    )
    
    preview_canvas.paste(Image.fromarray(cv2.cvtColor(bgr_notes_part, cv2.COLOR_BGR2RGB)), ((960 - preview_w)//2, (540 - preview_h)//2))
    
    rgb_frame = cv2.cvtColor(cv2.cvtColor(np.array(preview_canvas), cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2RGB)
    pil_final_preview = Image.fromarray(rgb_frame)
    
    pop_win = ctk.CTkToplevel(parent_window)
    pop_win.title(f"📸 1枚絵完成プレビュー - {res_mode} ({current_time:.2f}秒)")
    pop_win.geometry(f"980x580")
    pop_win.resizable(False, False)
    
    pop_win.lift()
    pop_win.attributes("-topmost", True)
    
    # PhotoImage から customtkinter専用の CTkImage 構築へ完全移行！
    # 高解像度モニターでのボケ現象および、コンソールの警告(UserWarning)を100%完璧に根絶しました。
    ctk_img = ctk.CTkImage(light_image=pil_final_preview, size=(960, 540))
    pop_win.ctk_img = ctk_img 
    
    lbl_img = ctk.CTkLabel(pop_win, image=ctk_img, text="")
    lbl_img.pack(padx=10, pady=10)
    
    btn_close = ctk.CTkButton(pop_win, text="閉じる", fg_color="#555555", hover_color="#444444", width=100, command=pop_win.destroy)
    btn_close.pack(pady=(0, 10))


def apply_opencv_vector_notes_draw(bgr_frame, width, height, scale, inst_type, midi_notes, 
                                   current_time, current_bpm, active_pitches, note_opacity_value,
                                   color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                                   aspect_ratio="16:9"):
    """
    OpenCVの LINE_AA を用いて、斜め面取りされたソリッドでシャープな幾学多角形ノーツを合成描画。
    アスペクト比引き延ばしに応じた上空レーン伸長オフセット計算を完全に加算します。
    """
    if not midi_notes:
        return bgr_frame

    color_blow_bgr = hex_to_rgb_exporter(color_blow_hex)[::-1]
    color_draw_bgr = hex_to_rgb_exporter(color_draw_hex)[::-1]

    notes_overlay = np.zeros_like(bgr_frame)
    notes_mask = np.zeros((height, width), dtype=np.uint8)

    # 古いハードコーディング（220, 405）を完全撤廃し、config の get_y_layout_params へ切り替え！
    # これにより、消滅ライン（Y_HOLE_LINE = 445）がミリ単位で完全に同期し、ノーツがハーモニカの上端をスムーズに越え、
    # 穴の入り口フチに吸着接触して美しく消え去るタイミングが完全に復元されました。
    y_center_full, y_collide_full, y_hole_line_full, height_converge_full = get_y_layout_params(height / scale)
    y_collide_s = y_collide_full * scale
    y_hole_line_s = y_hole_line_full * scale
    height_converge_s = height_converge_full * scale

    _, _, _, X_shift_notes = get_layout_params_exporter(inst_type, scale)
    pixels_per_second = (220.0 * current_bpm) / 240.0

    for note_data in midi_notes:
        start_t = note_data["start_time"]
        end_t = start_t + note_data["duration"]
        
        y_bottom = y_hole_line_s - (start_t - current_time) * pixels_per_second * scale
        y_top = y_hole_line_s - (end_t - current_time) * pixels_per_second * scale
        
        if y_bottom >= 0 and y_top <= y_hole_line_s:
            start_tick = note_data.get("start_tick", 0)
            fing = get_note_fingering_for_song(start_tick, note_data["note"], inst_type)
            if not fing: 
                continue
            
            col_bgr = color_blow_bgr if fing["action"] == "吹" else color_draw_bgr
            
            simulated_note = note_data["note"]
            if "バス" in inst_type:
                simulated_note = note_data["note"] + 36
                
            lane_idx = simulated_note - 48
            
            lane_x_left = int((72 + lane_idx * 16) * scale - X_shift_notes)
            lane_x_right = int(lane_x_left + 16 * scale)
            
            note_in_range = is_note_in_range(note_data["note"], inst_type)
            
            v_top = max(0, y_top)
            v_bottom = min(y_collide_s, y_bottom)
            
            length = max(1.0, y_bottom - y_top)
            ch = min(int(4 * scale), int(length / 2))
            ch_slope = min(int(3 * scale), int(length / 2))

            pts_accum = []

            is_top_chamfer = (y_top >= 0 and y_top < y_collide_s)

            if v_bottom > v_top:
                if is_top_chamfer:
                    pts_accum.append([lane_x_left + ch, int(y_top)])     
                    pts_accum.append([lane_x_right - ch, int(y_top)])    
                    pts_accum.append([lane_x_right, int(y_top + ch)])    
                else:
                    pts_accum.append([lane_x_left, int(v_top)])
                    pts_accum.append([lane_x_right, int(v_top)])

            if note_in_range and y_bottom > y_collide_s:
                t_top = max(y_collide_s, y_top)
                t_bottom = min(y_hole_line_s, y_bottom)
                
                if t_bottom > t_top:
                    dest_x_center = get_note_dest_x_exporter(note_data["note"], inst_type, scale, start_tick=start_tick)
                    dest_left = dest_x_center - 6 * scale
                    dest_right = dest_x_center + 6 * scale
                    
                    ratio_top = (t_top - y_collide_s) / height_converge_s
                    ratio_bottom = (t_bottom - y_collide_s) / height_converge_s
                    
                    x_top_l = lane_x_left + (dest_left - lane_x_left) * ratio_top
                    x_top_r = lane_x_right + (dest_right - lane_x_right) * ratio_top
                    x_bot_l = lane_x_left + (dest_left - lane_x_left) * ratio_bottom
                    x_bot_r = lane_x_right + (dest_right - lane_x_right) * ratio_bottom
                    
                    if y_top >= y_collide_s:
                        pts_accum.clear() 
                        ratio_t_cap = ((y_top + ch_slope) - y_collide_s) / height_converge_s
                        x_top_l_ch = lane_x_left + (dest_left - lane_x_left) * ratio_t_cap
                        x_top_r_ch = lane_x_right + (dest_right - lane_x_right) * ratio_t_cap
                        
                        pts_accum.append([int(x_top_l + ch_slope), int(y_top)])
                        pts_accum.append([int(x_top_r - ch_slope), int(y_top)])
                        pts_accum.append([int(x_top_r_ch), int(y_top + ch_slope)])
                    else:
                        pts_accum.append([int(x_top_r), int(t_top)])

                    y_bot_clamped = min(y_hole_line_s, y_bottom)
                    if y_bottom >= y_collide_s and y_bottom <= y_hole_line_s:
                        ratio_b_cap = ((y_bot_clamped - ch_slope) - y_collide_s) / height_converge_s
                        x_bottom_l_ch = lane_x_left + (dest_left - lane_x_left) * ratio_b_cap
                        x_bottom_right_ch = lane_x_right + (dest_right - lane_x_right) * ratio_b_cap
                        
                        pts_accum.append([int(x_bottom_right_ch), int(y_bot_clamped - ch_slope)])
                        pts_accum.append([int(x_bot_r - ch_slope), int(y_bot_clamped)])
                        pts_accum.append([int(x_bot_l + ch_slope), int(y_bot_clamped)])
                        pts_accum.append([int(x_bottom_l_ch), int(y_bot_clamped - ch_slope)])
                    else:
                        pts_accum.append([int(x_bot_r), int(t_bottom)])
                        pts_accum.append([int(x_bot_l), int(t_bottom)])
                        
                    if y_top < y_collide_s:
                        pts_accum.append([int(x_top_l), int(t_top)])
                        if is_top_chamfer:
                            # 🚀【解決（バグ根治）】：デバッグプリント残骸を廃止し、左上カドの面取り座標を安全に100%配列追加！
                            # これにより、等速下落中のノーツの左上面取りエッジが歪まず、完全にシャープに描画されます。
                            pts_accum.append([lane_x_left, int(y_top + ch)])
                    else:
                        ratio_t_cap = ((y_top + ch_slope) - y_collide_s) / height_converge_s
                        x_top_l_ch = lane_x_left + (dest_left - lane_x_left) * ratio_t_cap
                        pts_accum.append([int(x_top_l_ch), int(y_top + ch_slope)])
                else:
                    is_bottom_chamfer = (v_bottom > v_top and y_bottom < y_collide_s)
                    if is_bottom_chamfer:
                        pts_accum.append([lane_x_right, int(y_bottom - ch)])
                        pts_accum.append([lane_x_right - ch, int(y_bottom)])
                        pts_accum.append([lane_x_left + ch, int(y_bottom)])
                        pts_accum.append([lane_x_left, int(y_bottom - ch)])
                    else:
                        pts_accum.append([lane_x_right, int(v_bottom)])
                        pts_accum.append([lane_x_left, int(v_bottom)])
                        
                    if is_top_chamfer:
                        pts_accum.append([lane_x_left, int(y_top + ch)])
            else:
                is_bottom_chamfer = (v_bottom > v_top and y_bottom < y_collide_s)
                if is_bottom_chamfer:
                    pts_accum.append([lane_x_right, int(y_bottom - ch)])
                    pts_accum.append([lane_x_right - ch, int(y_bottom)])
                    pts_accum.append([lane_x_left + ch, int(y_bottom)])
                    pts_accum.append([lane_x_left, int(y_bottom - ch)])
                else:
                    pts_accum.append([lane_x_right, int(v_bottom)])
                    pts_accum.append([lane_x_left, int(v_bottom)])
                    
                if is_top_chamfer:
                    pts_accum.append([lane_x_left, int(y_top + ch)])

            if len(pts_accum) >= 3:
                pts = np.array(pts_accum, dtype=np.int32)
                cv2.fillPoly(notes_overlay, [pts], col_bgr, lineType=cv2.LINE_AA)
                cv2.fillPoly(notes_mask, [pts], 255, lineType=cv2.LINE_AA)

    mask_normalized = notes_mask.astype(float) / 255.0
    mask_normalized = np.expand_dims(mask_normalized, axis=2) 

    alpha_channel = mask_normalized * note_opacity_value
    bgr_frame = (bgr_frame * (1.0 - alpha_channel) + notes_overlay * alpha_channel).astype(np.uint8)
    return bgr_frame


def execute_video_export_core(midi_notes, current_bpm, max_duration, is_count_in, is_metro,
                              res_mode, inst_type, notation_mode, bg_color, 
                              is_hole_num_on, is_legend_on, is_notes_on, is_grid_on, is_glow_on, note_opacity,
                              current_midi_path, status_label, export_btn, root_after,
                              ticks_per_beat=480, fps_mode="60 FPS",
                              color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                              aspect_ratio="16:9", use_skin=True):
    if not OPENCV_AVAILABLE:
        status_label.configure(text="エラー: OpenCVライブラリが不足しています", text_color="#ff5555")
        return

    status_label.configure(text="🎬 動画エクスポートの準備中...", text_color="#ffcc00")

    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_dir = os.path.abspath(".")

    temp_dir = os.path.join(base_dir, "temp")
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    if current_midi_path:
        midi_filename = os.path.basename(current_midi_path)
        midi_name_only, _ = os.path.splitext(midi_filename)
        out_filename = f"{midi_name_only}.mp4"
    else:
        out_filename = "chromatic_harmonica_output.mp4"

    temp_video_path = os.path.join(temp_dir, "temp_silent.mp4")
    temp_audio_path = os.path.join(temp_dir, "temp_audio.wav")
    final_output_path = os.path.join(output_dir, out_filename)

    width, height, scale = resolve_resolution_and_scale(res_mode, aspect_ratio)

    try:
        opacity_val = float(note_opacity) / 100.0
    except Exception:
        opacity_val = 0.5

    fps = 60 

    def render_worker():
        try:
            total_frames = int(max_duration * fps)
            if total_frames <= 0:
                total_frames = 600 
                
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))

            print(f"[Export] OpenCV高解像度ベクトル描画レンダリング開始: {width}x{height} (Scale: {scale}), 総フレーム: {total_frames}")

            for frame_idx in range(total_frames):
                try:
                    if getattr(status_label.master.master.master.controller, "video_export_cancelled", False):
                        print("[Export] レンダリングがユーザーによって正常に中止されました。")
                        video_writer.release()
                        if os.path.exists(temp_video_path): os.remove(temp_video_path)
                        root_after(0, lambda: status_label.master.master.master.controller.on_export_finished_or_cancelled("cancelled"))
                        return
                except Exception:
                    pass

                current_time_sec = frame_idx / fps
                
                active_pitches = set()
                for note_data in midi_notes:
                    start_t = note_data["start_time"]
                    end_t = start_t + note_data["duration"]
                    if start_t <= current_time_sec < end_t:
                        active_pitches.add(note_data["note"])

                pil_frame = draw_harmonica_pillow_frame_exporter(
                    width=width,
                    height=height,
                    scale=scale,
                    canvas_bg_color=bg_color,
                    inst_type=inst_type,
                    lang_seg_value=notation_mode,
                    is_hole_num_on=is_hole_num_on,
                    is_legend_on=is_legend_on,
                    is_notes_on=False,                  
                    is_grid_on=is_grid_on,
                    note_opacity_value=opacity_val,
                    midi_notes=midi_notes,
                    current_time=current_time_sec,
                    current_bpm=current_bpm,
                    active_pitches=active_pitches,
                    show_glow_effect=is_glow_on,
                    color_blow_hex=color_blow_hex,            
                    color_draw_hex=color_draw_hex,
                    use_skin=use_skin
                )

                rgb_frame = pil_frame.convert("RGB")
                frame_np = np.array(rgb_frame)
                bgr_frame = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
                
                if is_notes_on:
                    bgr_frame = apply_opencv_vector_notes_draw(
                        bgr_frame=bgr_frame,
                        width=width,
                        height=height,
                        scale=scale,
                        inst_type=inst_type,
                        midi_notes=midi_notes,
                        current_time=current_time_sec,
                        current_bpm=current_bpm,
                        active_pitches=active_pitches,
                        note_opacity_value=opacity_val,
                        color_blow_hex=color_blow_hex,
                        color_draw_hex=color_draw_hex,
                        aspect_ratio=aspect_ratio
                    )
                
                video_writer.write(bgr_frame)

                percent = int((frame_idx + 1) / total_frames * 100)
                root_after(0, lambda p=percent: status_label.configure(
                    text=f"🎬 映像レンダリング中... {p}%", text_color="#ffcc00"
                ))

            video_writer.release()
            print("[Export] 無音動画の生成が完了。続いて高音質WAV物理合成を開始します。")

            root_after(0, lambda: status_label.configure(
                text="🎵 高音質WAV音声を合成中...", text_color="#00ffcc"
            ))

            try:
                import sys
                app = sys.modules['__main__']
                measures_timeline_ref = status_label.master.master.master.controller.midi_engine.measures_timeline
                ticks_per_beat_ref = status_label.master.master.controller.midi_engine.ticks_per_beat
                metronome_pattern_ref = status_label.master.master.master.controller.midi_engine.metronome_pattern
            except Exception:
                measures_timeline_ref = None
                ticks_per_beat_ref = 480
                metronome_pattern_ref = "標準（頭拍強調）"

            synthesize_midi_to_wav(
                midi_notes=midi_notes,
                current_bpm=current_bpm,
                max_duration=max_duration,
                is_count_in=is_count_in,
                is_metro=is_metro,
                output_wav_path=temp_audio_path,
                time_sig_num=4,
                time_sig_den=4,
                count_in_measures=1 if is_count_in else 0,
                measures_timeline=measures_timeline_ref,
                metronome_pattern=metronome_pattern_ref,
                ticks_per_beat=ticks_per_beat_ref,
                sample_rate=44100
            )
            print("[Export] 高音質WAV物理合成完了。FFmpegによる最終音声結合を開始します。")

            root_after(0, lambda: status_label.configure(
                text="🎬 FFmpegで音声を動画へ結合中...", text_color="#a29bfe"
            ))

            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", temp_video_path,
                "-i", temp_audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                final_output_path
            ]

            print(f"[Export] FFmpeg結合キック: {' '.join(ffmpeg_cmd)}")
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            try:
                result = subprocess.run(
                    ffmpeg_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    startupinfo=startupinfo,
                    timeout=45  
                )
                
                if result.returncode == 0:
                    root_after(0, lambda: status_label.configure(
                        text=f"🎉 エクスポート成功！\n'{os.path.basename(final_output_path)}'", 
                        text_color="#2b8c54"
                    ))
                    root_after(0, lambda: status_label.master.master.master.controller.on_export_finished_or_cancelled("success"))
                else:
                    raise subprocess.CalledProcessError(result.returncode, ffmpeg_cmd)
                    
            except Exception as ffmpeg_ex:
                print(f"[FFmpeg例外防衛] 結合に失敗しました。個別書き出しフォールバックを実施します: {ffmpeg_ex}")
                try:
                    import shutil
                    fallback_video_path = os.path.join(output_dir, f"{midi_name_only}_silent_video.mp4")
                    fallback_audio_path = os.path.join(output_dir, f"{midi_name_only}_audio.wav")
                    
                    shutil.copy(temp_video_path, fallback_video_path)
                    shutil.copy(temp_audio_path, fallback_audio_path)
                    
                    root_after(0, lambda: status_label.configure(
                        text=f"⚠️ 音声結合不全のため、映像と音声を別々に出力しました。\n"
                             f"映像: '{os.path.basename(fallback_video_path)}'\n"
                             f"音声: '{os.path.basename(fallback_audio_path)}'", 
                        text_color="#e0a300"
                    ))
                    root_after(0, lambda: status_label.master.master.master.controller.on_export_finished_or_cancelled("success_split"))
                except Exception as copy_err:
                    print(f"[致命的フォールバック不全] {copy_err}")
                    root_after(0, lambda: status_label.configure(
                        text="❌ 動画の保存（フォールバック）に完全に失敗しました", text_color="#ff5555"
                    ))
                    root_after(0, lambda: status_label.master.master.master.controller.on_export_finished_or_cancelled("failed", str(copy_err)))

            try:
                if os.path.exists(temp_video_path): os.remove(temp_video_path)
                if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
            except Exception:
                pass

        except Exception as ex:
            traceback.print_exc()
            error_details = str(ex)
            root_after(0, lambda e=error_details: status_label.configure(
                text=f"❌ レンダリング失敗: {e[:30]}...", text_color="#ff5555"
            ))
            root_after(0, lambda e=error_details: status_label.master.master.master.controller.on_export_finished_or_cancelled("failed", e))

    t = threading.Thread(target=render_worker, daemon=True)
    t.start()