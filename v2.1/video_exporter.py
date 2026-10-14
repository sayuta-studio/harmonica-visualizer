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
    import customtkinter as ctk
    from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageOps, ImageEnhance
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("[警告] pillow または customtkinter が見つかりません。")
OPENCV_AVAILABLE = False

import bisect

_CACHE = {
    "key": None,          
    "base_image": None,   
}
_FONT_CACHE = {}
_LABEL_STAMP_CACHE = {}
_MEASURE_STAMP_CACHE = {}
_EXP_NOTES_INDEX_CACHE = {
    "list_id": None,
    "len": 0,
    "first_start_t": None,
    "inst_type": None,
    "start_times": [],
    "max_dur": 0.0,
}

def _get_exporter_notes_index(midi_notes, inst_type=None):
    if not midi_notes:
        return [], 0.0
    lid = id(midi_notes)
    n_len = len(midi_notes)
    first_st = midi_notes[0].get("start_time", 0.0)
    need_rebind = bool(inst_type and (midi_notes[0].get("_bound_inst") != inst_type or "dest_x_base" not in midi_notes[0]))
    if (
        _EXP_NOTES_INDEX_CACHE["list_id"] != lid
        or _EXP_NOTES_INDEX_CACHE["len"] != n_len
        or _EXP_NOTES_INDEX_CACHE["first_start_t"] != first_st
        or need_rebind
    ):
        _EXP_NOTES_INDEX_CACHE["list_id"] = lid
        _EXP_NOTES_INDEX_CACHE["len"] = n_len
        _EXP_NOTES_INDEX_CACHE["first_start_t"] = first_st
        _EXP_NOTES_INDEX_CACHE["inst_type"] = inst_type
        _EXP_NOTES_INDEX_CACHE["start_times"] = [n.get("start_time", 0.0) for n in midi_notes]
        _EXP_NOTES_INDEX_CACHE["max_dur"] = max((n.get("duration", 0.0) for n in midi_notes), default=0.0)
        if inst_type:
            for n in midi_notes:
                if n.get("_bound_inst") != inst_type or "dest_x_base" not in n:
                    st_tick = n.get("start_tick", 0)
                    pitch = n["note"]
                    n["fingering"] = get_note_fingering_for_song(st_tick, pitch, inst_type)
                    n["in_range"] = is_note_in_range(pitch, inst_type)
                    n["dest_x_base"] = get_note_dest_x(pitch, inst_type, 1.0, start_tick=st_tick)
                    n["name_jp"] = get_note_name(pitch, is_japanese=True)
                    n["name_cde"] = get_note_name(pitch, is_japanese=False)
                    n["_bound_inst"] = inst_type
    return _EXP_NOTES_INDEX_CACHE["start_times"], _EXP_NOTES_INDEX_CACHE["max_dur"]

from audio_engine import synthesize_midi_to_wav
from config import (
    COLOR_BLOW_RGB, COLOR_BLOW_INNER,
    COLOR_DRAW_RGB, COLOR_DRAW_INNER,
    W_PITCH, D_HOLE, CANVAS_WIDTH, CANVAS_HEIGHT,
    get_y_layout_params, get_y_trajectory_params, get_portable_path,
    LEVER_WIDTH_DEFAULT, LEVER_HEIGHT_DEFAULT,
    get_layout_params, get_note_dest_x, hex_to_rgb, draw_metallic_button_pil_flat,
    get_lever_highlight_rgb, get_lever_highlight_bgr
)
from harmonica_map import (
    is_note_in_range, get_note_name, get_note_fingering_for_song, get_hole_4_notes, BLOW_NOTES_MIDI
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


def get_truetype_font(font_name, size):
    key = (font_name, int(size))
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        if os.name == 'nt':
            font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", font_name)
            if os.path.exists(font_path):
                f = ImageFont.truetype(font_path, int(size))
                _FONT_CACHE[key] = f
                return f
        f = ImageFont.truetype("arial.ttf", int(size))
        _FONT_CACHE[key] = f
        return f
    except Exception:
        f = ImageFont.load_default()
        _FONT_CACHE[key] = f
        return f


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


def _make_premul_rgb_stamp(rgba_img, crop_bbox=True):
    """
    PIL.Image(RGBA) から高速ブレンド用の事前乗算スタンプ (premul_rgb_f32, inv_alpha_f32, bx0, by0) を生成します。
    """
    if crop_bbox:
        bbox = rgba_img.getbbox()
        if not bbox:
            return None, None, 0, 0
        bx0, by0, _, _ = bbox
        arr = np.asarray(rgba_img.crop(bbox))
    else:
        bx0, by0 = 0, 0
        arr = np.asarray(rgba_img)
    alpha = (arr[:, :, 3:4].astype(np.float32)) * (1.0 / 255.0)
    rgb = arr[:, :, :3].astype(np.float32)
    premul_rgb = rgb * alpha
    inv_alpha = 1.0 - alpha
    return premul_rgb, inv_alpha, bx0, by0

_make_premul_bgr_stamp = _make_premul_rgb_stamp


def _blend_premul_stamp_rgb(rgb_frame, stamp, x0, y0, width, height):
    """
    事前乗算スタンプ (premul_rgb, inv_alpha, bx0, by0) を rgb_frame の (x0 + bx0, y0 + by0) に高速合成します。
    """
    premul_rgb, inv_alpha, bx0, by0 = stamp
    if premul_rgb is None:
        return
    px0 = x0 + bx0
    py0 = y0 + by0
    sh, sw = premul_rgb.shape[:2]
    dx0 = max(0, px0)
    dy0 = max(0, py0)
    dx1 = min(width, px0 + sw)
    dy1 = min(height, py0 + sh)
    if dx1 > dx0 and dy1 > dy0:
        sx0 = dx0 - px0
        sy0 = dy0 - py0
        sx1 = sx0 + (dx1 - dx0)
        sy1 = sy0 + (dy1 - dy0)
        sub_bg = rgb_frame[dy0:dy1, dx0:dx1]
        rgb_frame[dy0:dy1, dx0:dx1] = (
            sub_bg.astype(np.float32) * inv_alpha[sy0:sy1, sx0:sx1] + premul_rgb[sy0:sy1, sx0:sx1]
        ).astype(np.uint8)

_blend_premul_stamp_bgr = _blend_premul_stamp_rgb


def _get_measure_label_stamp(text_str, font_size, color_rgba):
    key = (text_str, int(font_size), color_rgba[:3])
    cached = _MEASURE_STAMP_CACHE.get(key)
    if cached is not None:
        return cached
    f_m = get_truetype_font("arial.ttf", max(6, int(font_size)))
    pad_w = max(24, int(font_size * max(2, len(text_str)) + 12))
    pad_h = max(20, int(font_size * 2.2 + 12))
    ax = 4
    ay = pad_h - 4
    img = Image.new("RGBA", (pad_w, pad_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((ax, ay), text_str, fill=color_rgba, font=f_m, anchor="lb")
    bbox = img.getbbox()
    if not bbox:
        res = (None, None, 0, 0)
        _MEASURE_STAMP_CACHE[key] = res
        return res
    bx0, by0, _, _ = bbox
    arr = np.asarray(img.crop(bbox))
    alpha = (arr[:, :, 3:4].astype(np.float32)) * (1.0 / 255.0)
    bgr = arr[:, :, 2::-1].astype(np.float32)
    res = (bgr * alpha, 1.0 - alpha, bx0 - ax, by0 - ay)
    _MEASURE_STAMP_CACHE[key] = res
    return res


def draw_harmonica_pillow_frame_exporter(width, height, scale, canvas_bg_color, inst_type, lang_seg_value, 
                                         is_hole_num_on, is_legend_on, is_notes_on, is_grid_on,
                                         note_opacity_value, midi_notes=None, current_time=0.0, current_bpm=120.0, 
                                         active_pitches=None, show_glow_effect=True,
                                         color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                                         use_skin=True, trajectory_mode="3段階 (練習標準)",
                                         show_lookahead=True, show_grid4=True, measures_timeline=None,
                                         use_ring=True, note_speed_ratio=1.0,
                                         bg_image_path=None, bg_brightness=1.0,
                                         bg_fit_mode="中央トリミング (画面いっぱい)",
                                         bg_rotation="0° (自動補正)",
                                         return_bgr=False):
    """
    オフライン書き出し専用：静止パーツ（背景グリッド・カバープレート・4音グリッド64マス・レバー2状態）と
    発光スタンプ・各穴の発音状態パッチを事前/遅延キャッシュし、毎フレームはBGR NumPy配列上で高速差分合成します。
    """
    if midi_notes is None: midi_notes = []

    y_center_s, y_collide_s, y_straight_s, y_hole_line_s, height_diag_s, height_straight_s = get_y_trajectory_params(height / scale, trajectory_mode)
    y_center_s *= scale
    y_collide_s *= scale
    y_straight_s *= scale
    y_hole_line_s *= scale
    height_diag_s *= scale
    height_straight_s *= scale
    is_straight_mode = ("垂直落下" in str(trajectory_mode))

    W_pitch_s = W_PITCH * scale
    D_hole_s = D_HOLE * scale

    visible_indices, X_start_draw, X_shift, X_shift_notes = get_layout_params(inst_type, scale)
    N_visible = len(visible_indices)
    total_width = N_visible * W_pitch_s

    color_blow_rgb = hex_to_rgb(color_blow_hex)
    color_draw_rgb = hex_to_rgb(color_draw_hex)

    f_num = get_truetype_font("arial.ttf", max(6, int(11 * scale)))
    f_note = get_truetype_font("meiryo.ttc", max(6, int(11 * scale)))
    f_grid = get_truetype_font("meiryo.ttc", max(5, int(8 * scale)))
    is_jp = ("ドレミ" in lang_seg_value)

    cell_order = [
        ("吹", "OFF", 0, 0),  # 左上: 吹き（スライドなし）
        ("吸", "OFF", 0, 1),  # 右上: 吸い（スライドなし）
        ("吹", "ON", 1, 0),   # 左下: スライド有りの吹き
        ("吸", "ON", 1, 1),   # 右下: スライド有りの吸い
    ]
    grid_top = y_center_s + 47 * scale
    cell_w = 23 * scale
    cell_h = 15 * scale

    has_bg_img = bool(bg_image_path and os.path.exists(bg_image_path))
    cache_key = (
        inst_type, canvas_bg_color, lang_seg_value,
        is_hole_num_on, is_legend_on, is_notes_on, is_grid_on,
        color_blow_hex, color_draw_hex,
        use_skin, trajectory_mode, show_grid4, use_ring,
        width, height, round(scale, 5),
        bg_image_path if has_bg_img else None, round(float(bg_brightness), 3),
        bg_fit_mode if has_bg_img else None, bg_rotation if has_bg_img else None
    )

    global _CACHE
    if _CACHE.get("key") != cache_key or _CACHE.get("bgr_static_off") is None:
        base_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        base_draw = ImageDraw.Draw(base_img)

        if canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00":
            pad_rgb = (0, 255, 0)
        elif canvas_bg_color == "ブルーバック" or canvas_bg_color == "#0000FF":
            pad_rgb = (0, 0, 255)
        elif canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF":
            pad_rgb = (255, 0, 255)
        else:
            pad_rgb = (13, 13, 13)

        bg_pasted = False
        if has_bg_img:
            try:
                from visualizer import prepare_background_image
                pil_bg_fit = prepare_background_image(
                    bg_image_path=bg_image_path,
                    target_w=width,
                    target_h=height,
                    bg_brightness=bg_brightness,
                    bg_fit_mode=bg_fit_mode,
                    bg_rotation=bg_rotation,
                    pad_rgb=pad_rgb
                )
                base_img.paste(pil_bg_fit.convert("RGBA"), (0, 0))
                bg_pasted = True
            except Exception as ex:
                print(f"[警告] エクスポート用背景画像の読み込み失敗: {ex}")

        if not bg_pasted:
            base_draw.rectangle([0, 0, width, height], fill=(pad_rgb[0], pad_rgb[1], pad_rgb[2], 255))

        if is_grid_on:
            is_bright_bg = (not bg_pasted) and (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00" or canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF")
            grid_alpha = 15 if is_bright_bg else 25
            grid_color = (0, 0, 0, grid_alpha) if is_bright_bg else (255, 255, 255, grid_alpha)
            grid_line_color = (0, 0, 0, 40) if is_bright_bg else (255, 255, 255, 25)
            line_w = max(1, int(1 * scale))

            if is_straight_mode:
                for k in range(N_visible):
                    hx = X_start_draw + k * W_pitch_s
                    for sub in (1, 2, 3):
                        sx = hx + sub * 12 * scale
                        base_draw.line([(sx, 0), (sx, y_hole_line_s)], fill=grid_color, width=line_w)
                    base_draw.line([(hx, 0), (hx, y_hole_line_s)], fill=grid_line_color, width=line_w)
                base_draw.line([(X_start_draw + total_width, 0), (X_start_draw + total_width, y_hole_line_s)], fill=grid_line_color, width=line_w)
            else:
                for idx in range(58):
                    x_pos = (24 + idx * 16) * scale
                    base_draw.line([(x_pos, 0), (x_pos, y_collide_s)], fill=grid_color, width=line_w)

                base_draw.line([(24 * scale, 0), (24 * scale, y_collide_s)], fill=grid_line_color, width=line_w)
                base_draw.line([(936 * scale, 0), (936 * scale, y_collide_s)], fill=grid_line_color, width=line_w)

                if height_straight_s > 0:
                    base_draw.line([(X_start_draw, y_straight_s), (X_start_draw + total_width, y_straight_s)], fill=grid_color, width=line_w)
                    for k in range(N_visible):
                        hx = X_start_draw + k * W_pitch_s
                        for sub in (1, 2, 3):
                            sx = hx + sub * 12 * scale
                            base_draw.line([(sx, y_straight_s), (sx, y_hole_line_s)], fill=grid_color, width=line_w)
                        base_draw.line([(hx, y_straight_s), (hx, y_hole_line_s)], fill=grid_line_color, width=line_w)
                    base_draw.line([(X_start_draw + total_width, y_straight_s), (X_start_draw + total_width, y_hole_line_s)], fill=grid_line_color, width=line_w)

        lever_left = (X_start_draw + total_width)
        skins_dir = get_portable_path("skins")
        lever_off_path = os.path.join(skins_dir, "レバーオフ.png")
        lever_on_path = os.path.join(skins_dir, "レバーオン.png")
        face_path = os.path.join(skins_dir, "マウスピース.png")

        has_lever_skin = use_skin and os.path.exists(lever_off_path) and os.path.exists(lever_on_path)
        has_face_skin = use_skin and os.path.exists(face_path)

        # 透明ボディオーバーレイ（OFF / ON）の構築
        body_overlay_off = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        body_overlay_on = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        if has_lever_skin:
            try:
                lever_w = int(LEVER_WIDTH_DEFAULT * scale)
                lever_h = int(LEVER_HEIGHT_DEFAULT * scale)
                lever_y = int(y_center_s - lever_h / 2)
                lever_x = int(lever_left + 15 * scale)
                pil_l_off = Image.open(lever_off_path).convert("RGBA").resize((lever_w, lever_h), Image.Resampling.LANCZOS)
                pil_l_on = Image.open(lever_on_path).convert("RGBA").resize((lever_w, lever_h), Image.Resampling.LANCZOS)
                body_overlay_off.paste(pil_l_off, (lever_x, lever_y), mask=pil_l_off)
                body_overlay_on.paste(pil_l_on, (lever_x, lever_y), mask=pil_l_on)
            except Exception as ex:
                has_lever_skin = False
                print(f"[警告] レバースキン合成に失敗しました: {ex}")

        if not has_lever_skin:
            btn_w = max(1, int(16 * scale))
            btn_h = max(1, int(36 * scale))
            d_off = ImageDraw.Draw(body_overlay_off)
            d_off.rounded_rectangle([lever_left, y_center_s - 12 * scale, lever_left + 24 * scale, y_center_s + 12 * scale], radius=int(4 * scale), fill=(85, 85, 85, 255))
            btn_img_off = draw_metallic_button_pil_flat(btn_w, btn_h, is_on=False)
            body_overlay_off.paste(btn_img_off, (int(lever_left + 22 * scale), int(y_center_s - btn_h / 2)), mask=btn_img_off)

            d_on = ImageDraw.Draw(body_overlay_on)
            d_on.rounded_rectangle([lever_left, y_center_s - 12 * scale, lever_left + 12 * scale, y_center_s + 12 * scale], radius=int(4 * scale), fill=(58, 58, 58, 255))
            btn_img_on = draw_metallic_button_pil_flat(btn_w, btn_h, is_on=True)
            body_overlay_on.paste(btn_img_on, (int(lever_left + 3 * scale), int(y_center_s - btn_h / 2)), mask=btn_img_on)

        plate_w = int(total_width + 30 * scale)
        plate_h = int(90 * scale)
        plate_pos = (int(X_start_draw - 15 * scale), int(y_center_s - 45 * scale))
        plate_img = None

        if has_face_skin:
            try:
                plate_img = Image.open(face_path).convert("RGBA").resize((plate_w, plate_h), Image.Resampling.LANCZOS)
            except Exception as ex:
                has_face_skin = False
                print(f"[警告] カバープレートスキン合成に失敗しました: {ex}")

        if not has_face_skin or plate_img is None:
            metallic_plate_img = generate_metallic_texture(plate_w, plate_h)
            plate_mask = Image.new("L", (plate_w, plate_h), 0)
            plate_mask_draw = ImageDraw.Draw(plate_mask)
            plate_mask_draw.rounded_rectangle([0, 0, plate_w, plate_h], radius=int(15 * scale), fill=255)
            plate_img = Image.new("RGBA", (plate_w, plate_h))
            plate_img.paste(metallic_plate_img, (0, 0), mask=plate_mask)

        for ov in (body_overlay_off, body_overlay_on):
            ov.paste(plate_img, plate_pos, mask=plate_img)
            d_ov = ImageDraw.Draw(ov)
            for k, idx in enumerate(visible_indices):
                x_center = X_start_draw + k * W_pitch_s + (W_pitch_s / 2)
                d_ov.ellipse(
                    [x_center - (D_hole_s / 2), y_center_s - (D_hole_s / 2),
                     x_center + (D_hole_s / 2), y_center_s + (D_hole_s / 2)],
                    fill="#080808", outline="#333333", width=1
                )

        # 小節横線がカバープレート上部（y_center_s - 45*scale 〜 y_hole_line_s）と重なった際に上書き復元するストリップ
        strip_y0 = max(0, int(y_center_s - 46 * scale))
        strip_y1 = min(height, int(y_hole_line_s + 3 * scale))
        top_strip_off = body_overlay_off.crop((0, strip_y0, width, strip_y1))
        top_strip_on = body_overlay_on.crop((0, strip_y0, width, strip_y1))

        full_off = Image.alpha_composite(base_img, body_overlay_off)
        full_on = Image.alpha_composite(base_img, body_overlay_on)

        # 1音表示モード時、発音中の穴だけ白文字に差し替えるための背景帯バックアップ
        note_band_y0 = max(0, int(y_center_s + 44 * scale))
        note_band_y1 = min(height, int(y_center_s + 76 * scale))
        clean_note_band = full_off.crop((0, note_band_y0, width, note_band_y1))

        hole_4_maps = {}
        mode_key = "16穴" if "16穴" in inst_type else ("12穴 標準" if "標準" in inst_type else "12穴 バス")

        for full_img in (full_off, full_on):
            d_full = ImageDraw.Draw(full_img)
            if is_legend_on:
                legend_x_start = 770 * scale
                d_full.rectangle([legend_x_start, 30 * scale, legend_x_start + 140 * scale, 75 * scale], fill=(28, 28, 28, 255), outline=(0, 0, 0, 255), width=int(2 * scale))
                d_full.ellipse([legend_x_start + 12 * scale, 40 * scale, legend_x_start + 22 * scale, 50 * scale], fill=color_blow_rgb)
                d_full.ellipse([legend_x_start + 12 * scale, 55 * scale, legend_x_start + 22 * scale, 65 * scale], fill=color_draw_rgb)
                draw_bordered_text_pillow(d_full, (legend_x_start + 80 * scale, 45 * scale), "吹", "#FFFFFF", get_truetype_font("msgothic.ttc", 10 * scale), border_width=1.5 * scale)
                draw_bordered_text_pillow(d_full, (legend_x_start + 80 * scale, 60 * scale), "吸", "#FFFFFF", get_truetype_font("msgothic.ttc", 10 * scale), border_width=1.5 * scale)

            for k, idx in enumerate(visible_indices):
                x_center = X_start_draw + k * W_pitch_s + (W_pitch_s / 2)
                hole_number = k + 1
                visible_hole_number_absolute = visible_indices[k] + 1
                if is_hole_num_on:
                    draw_bordered_text_pillow(d_full, (x_center, y_center_s + 24 * scale), str(hole_number), "#FFFFFF", f_num, border_width=2 * scale)

                if show_grid4:
                    h4 = get_hole_4_notes(visible_hole_number_absolute, inst_type)
                    hole_4_maps[visible_hole_number_absolute] = h4
                    grid_left = x_center - cell_w
                    for act, lev, r_idx, c_idx in cell_order:
                        cx0 = grid_left + c_idx * cell_w
                        cy0 = grid_top + r_idx * cell_h
                        cx1 = cx0 + cell_w
                        cy1 = cy0 + cell_h
                        cell_midi = h4.get((act, lev))
                        cell_text = get_note_name(cell_midi, is_japanese=is_jp) if (cell_midi is not None and lang_seg_value != "なし") else ""
                        c_fill = (24, 24, 24, 255) if r_idx == 0 else (16, 16, 16, 255)
                        c_out = (56, 56, 56, 255) if r_idx == 0 else (44, 44, 44, 255)
                        t_fill = (204, 204, 204, 255) if r_idx == 0 else (136, 136, 136, 255)
                        d_full.rectangle([cx0, cy0, cx1, cy1], fill=c_fill, outline=c_out, width=max(1, int(1 * scale)))
                        if cell_text:
                            d_full.text(((cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0), cell_text, fill=t_fill, font=f_grid, anchor="mm")
                elif lang_seg_value != "なし":
                    note_text = get_note_name(BLOW_NOTES_MIDI[mode_key][k], is_japanese=is_jp)
                    text_color = "#000000" if (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00" or canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF") else "#AAAAAA"
                    draw_bordered_text_pillow(d_full, (x_center, y_center_s + 60 * scale), note_text, text_color, f_note, border_width=2 * scale)

        rgb_static_off = np.asarray(full_off.convert("RGB"))
        rgb_static_on = np.asarray(full_on.convert("RGB"))

        legend_patch_rgb = None
        legend_pos = (0, 0)
        if is_legend_on:
            lx0 = max(0, int(766 * scale))
            ly0 = max(0, int(26 * scale))
            lx1 = min(width, int(914 * scale))
            ly1 = min(height, int(79 * scale))
            legend_patch_rgb = rgb_static_off[ly0:ly1, lx0:lx1].copy()
            legend_pos = (lx0, ly0)

        # 発光スタンプ（Blowリング / Drawリング / 上部扇形）の事前生成
        r_ring = max(2, int(22 * scale))
        ring_pad = r_ring + 2
        ring_size = ring_pad * 2
        glow_ring_blow = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
        draw_glow_ring(ImageDraw.Draw(glow_ring_blow), ring_pad, ring_pad, r_ring, color_blow_rgb, max_alpha=245)
        glow_ring_draw = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
        draw_glow_ring(ImageDraw.Draw(glow_ring_draw), ring_pad, ring_pad, r_ring, color_draw_rgb, max_alpha=245)

        r_pie = max(2, int(32 * scale))
        pie_pad = r_pie + 2
        pie_size = pie_pad * 2
        glow_pie = Image.new("RGBA", (pie_size, pie_size), (0, 0, 0, 0))
        draw_glow_pieslice(ImageDraw.Draw(glow_pie), pie_pad, pie_pad, r_pie, (255, 255, 255), max_alpha=210)

        _CACHE["key"] = cache_key
        _CACHE["base_image"] = base_img
        _CACHE["full_static_off"] = full_off
        _CACHE["full_static_on"] = full_on
        _CACHE["bgr_static_off"] = rgb_static_off
        _CACHE["bgr_static_on"] = rgb_static_on
        _CACHE["rgb_static_off"] = rgb_static_off
        _CACHE["rgb_static_on"] = rgb_static_on
        _CACHE["top_strip_off_stamp"] = _make_premul_rgb_stamp(top_strip_off, crop_bbox=True)
        _CACHE["top_strip_on_stamp"] = _make_premul_rgb_stamp(top_strip_on, crop_bbox=True)
        _CACHE["strip_y0"] = strip_y0
        _CACHE["strip_y1"] = strip_y1
        _CACHE["legend_patch_bgr"] = legend_patch_rgb
        _CACHE["legend_patch_rgb"] = legend_patch_rgb
        _CACHE["legend_pos"] = legend_pos
        _CACHE["clean_note_band"] = clean_note_band
        _CACHE["note_band_y0"] = note_band_y0
        _CACHE["hole_4_maps"] = hole_4_maps
        _CACHE["glow_ring_blow"] = glow_ring_blow
        _CACHE["glow_ring_draw"] = glow_ring_draw
        _CACHE["ring_pad"] = ring_pad
        _CACHE["glow_pie_stamp"] = _make_premul_rgb_stamp(glow_pie, crop_bbox=True)
        _CACHE["pie_pad"] = pie_pad
        _CACHE["hole_patches"] = {}

    lever_pressed = False
    playing_holes_data = {}
    playing_hole_cells = set()
    playing_holes_note = {}
    
    currently_active_notes = []
    if midi_notes:
        start_times, max_dur = _get_exporter_notes_index(midi_notes, inst_type)
        idx_start = bisect.bisect_left(start_times, current_time - max_dur - 0.05)
        n_total = len(midi_notes)
        for i in range(idx_start, n_total):
            note_data = midi_notes[i]
            n_start_time = note_data.get("start_time", 0.0)
            if n_start_time > current_time:
                break
            n_dur_time = note_data.get("duration", 0.0)
            if n_start_time <= current_time < (n_start_time + n_dur_time):
                currently_active_notes.append(note_data)

    for note_data in currently_active_notes:
        fingering = note_data.get("fingering") 
        if not fingering:
            fingering = get_note_fingering_for_song(note_data.get("start_tick", 0), note_data["note"], inst_type)
        if fingering:
            h_num = fingering["hole"]
            playing_holes_data[h_num] = fingering["action"] 
            playing_hole_cells.add((h_num, fingering["action"], fingering["lever"]))
            if h_num not in playing_holes_note:
                playing_holes_note[h_num] = note_data["note"]
            if fingering["lever"] == "ON": 
                lever_pressed = True

    bgr_frame = (_CACHE["bgr_static_on"] if lever_pressed else _CACHE["bgr_static_off"]).copy()

    # 小節ごとの薄い横線＋左端小節番号の落下描画（ガイド線ON時）
    if is_grid_on and measures_timeline:
        is_bright_bg = (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00" or canvas_bg_color == "マゼンタ（ピンク）" or canvas_bg_color == "#FF00FF")
        m_line_rgba = (0, 51, 0, 255) if (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00") else ((50, 0, 50, 255) if is_bright_bg else (46, 46, 46, 255))
        m_txt_rgba = (0, 85, 0, 255) if (canvas_bg_color == "グリーンバック" or canvas_bg_color == "#00FF00") else ((80, 0, 80, 255) if is_bright_bg else (85, 85, 85, 255))
        m_line_rgb = m_line_rgba[:3]
        m_font_size = max(6, int(8 * scale))
        line_w = max(1, int(1 * scale))
        pixels_per_second = (220.0 * current_bpm * max(0.1, float(note_speed_ratio))) / 240.0
        if is_straight_mode:
            x_l = X_start_draw
            x_r = X_start_draw + total_width
        else:
            x_l = 24.0 * scale
            x_r = 936.0 * scale

        xl_i = max(0, int(round(x_l)))
        xr_i = min(width, int(round(x_r)) + 1)
        strip_y0 = _CACHE["strip_y0"]
        overlapped_plate = False
        overlapped_legend = False
        leg_y0 = int(26 * scale)
        leg_y1 = int(79 * scale)

        for m in measures_timeline:
            m_start_t = m.get("start_time", 0.0)
            y_m = y_hole_line_s - (m_start_t - current_time) * pixels_per_second * scale
            if y_m < 0.0:
                break
            if y_m <= y_hole_line_s:
                ym_i = int(round(y_m))
                ly0 = max(0, ym_i - line_w // 2)
                ly1 = min(height, ly0 + line_w)
                if ly1 > ly0 and xr_i > xl_i:
                    bgr_frame[ly0:ly1, xl_i:xr_i] = m_line_rgb
                m_stamp = _get_measure_label_stamp(str(m["measure_num"]), m_font_size, m_txt_rgba)
                _blend_premul_stamp_bgr(bgr_frame, m_stamp, int(round(x_l + 4 * scale)), int(round(y_m - 2 * scale)), width, height)
                if y_m >= strip_y0 - 2:
                    overlapped_plate = True
                if is_legend_on and (leg_y0 <= y_m <= leg_y1):
                    overlapped_legend = True

        if overlapped_plate:
            top_stamp = _CACHE["top_strip_on_stamp"] if lever_pressed else _CACHE["top_strip_off_stamp"]
            _blend_premul_stamp_bgr(bgr_frame, top_stamp, 0, strip_y0, width, height)
        if overlapped_legend and _CACHE["legend_patch_bgr"] is not None:
            lx0, ly0 = _CACHE["legend_pos"]
            l_patch = _CACHE["legend_patch_bgr"]
            lh, lw = l_patch.shape[:2]
            bgr_frame[ly0:ly0 + lh, lx0:lx0 + lw] = l_patch

    # 発音中の穴のみキャッシュ済みBGRパッチ＆上部扇形グロースタンプを高速差分合成
    if playing_holes_data:
        ring_pad = _CACHE["ring_pad"]
        pie_pad = _CACHE["pie_pad"]
        glow_pie_stamp = _CACHE["glow_pie_stamp"]
        hole_4_maps = _CACHE["hole_4_maps"]
        clean_note_band = _CACHE["clean_note_band"]
        note_band_y0 = _CACHE["note_band_y0"]
        hole_patches = _CACHE["hole_patches"]
        lever_ring_r = 21.0 * scale
        lever_ring_w = max(2, int(3 * scale))

        for k, idx in enumerate(visible_indices):
            visible_hole_number_absolute = visible_indices[k] + 1
            if visible_hole_number_absolute not in playing_holes_data:
                continue

            x_center = X_start_draw + k * W_pitch_s + (W_pitch_s / 2)
            action = playing_holes_data[visible_hole_number_absolute]
            if show_grid4:
                cells_mask = tuple((visible_hole_number_absolute, act, lev) in playing_hole_cells for act, lev, _, _ in cell_order)
                current_note = None
            elif lang_seg_value != "なし":
                cells_mask = None
                current_note = playing_holes_note.get(visible_hole_number_absolute)
            else:
                cells_mask = None
                current_note = None

            h_key = (k, bool(lever_pressed), action, cells_mask, current_note)
            cached_patch = hole_patches.get(h_key)
            if cached_patch is None:
                hx0 = max(0, int(x_center - W_pitch_s / 2))
                hx1 = min(width, int(math.ceil(x_center + W_pitch_s / 2)))
                hy0 = max(0, int(round(y_center_s)) - ring_pad)
                hy1 = min(height, int(math.ceil(y_center_s + 80 * scale)))
                src_full = _CACHE["full_static_on"] if lever_pressed else _CACHE["full_static_off"]
                patch_pil = src_full.crop((hx0, hy0, hx1, hy1))
                patch_draw = ImageDraw.Draw(patch_pil)

                ring_stamp = _CACHE["glow_ring_blow"] if action == "吹" else _CACHE["glow_ring_draw"]
                patch_pil.alpha_composite(ring_stamp, (int(round(x_center)) - ring_pad - hx0, int(round(y_center_s)) - ring_pad - hy0))

                if use_ring and lever_pressed:
                    l_rgb = color_blow_rgb if action == "吹" else color_draw_rgb
                    patch_draw.ellipse(
                        [x_center - lever_ring_r - hx0, y_center_s - lever_ring_r - hy0,
                         x_center + lever_ring_r - hx0, y_center_s + lever_ring_r - hy0],
                        outline=(l_rgb[0], l_rgb[1], l_rgb[2], 255),
                        width=lever_ring_w
                    )

                if is_hole_num_on:
                    draw_bordered_text_pillow(patch_draw, (x_center - hx0, y_center_s + 24 * scale - hy0), str(k + 1), "#FFFFFF", f_num, border_width=2 * scale)

                if show_grid4:
                    hole_4_map = hole_4_maps.get(visible_hole_number_absolute) or get_hole_4_notes(visible_hole_number_absolute, inst_type)
                    grid_left = x_center - cell_w - hx0
                    grid_top_rel = grid_top - hy0
                    for act, lev, r_idx, c_idx in cell_order:
                        if (visible_hole_number_absolute, act, lev) in playing_hole_cells:
                            cx0 = grid_left + c_idx * cell_w
                            cy0 = grid_top_rel + r_idx * cell_h
                            cx1 = cx0 + cell_w
                            cy1 = cy0 + cell_h
                            cell_midi = hole_4_map.get((act, lev))
                            cell_text = get_note_name(cell_midi, is_japanese=is_jp) if (cell_midi is not None and lang_seg_value != "なし") else ""
                            c_rgb = color_blow_rgb if act == "吹" else color_draw_rgb
                            patch_draw.rectangle([cx0, cy0, cx1, cy1], fill=(c_rgb[0], c_rgb[1], c_rgb[2], 255), outline=(255, 255, 255, 255), width=max(1, int(1 * scale)))
                            if cell_text:
                                patch_draw.text(((cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0), cell_text, fill=(0, 0, 0, 255), font=f_grid, anchor="mm")
                elif lang_seg_value != "なし" and current_note is not None:
                    sub_bg = clean_note_band.crop((hx0, 0, hx1, clean_note_band.height))
                    patch_pil.paste(sub_bg, (0, note_band_y0 - hy0))
                    note_text = get_note_name(current_note, is_japanese=is_jp)
                    draw_bordered_text_pillow(patch_draw, (x_center - hx0, y_center_s + 60 * scale - hy0), note_text, "#FFFFFF", f_note, border_width=2 * scale)

                patch_rgb = np.asarray(patch_pil.convert("RGB"))
                cached_patch = (hx0, hy0, hx1, hy1, patch_rgb)
                hole_patches[h_key] = cached_patch

            hx0, hy0, hx1, hy1, patch_rgb = cached_patch
            bgr_frame[hy0:hy1, hx0:hx1] = patch_rgb

            if show_glow_effect:
                _blend_premul_stamp_rgb(bgr_frame, glow_pie_stamp, int(round(x_center)) - pie_pad, int(round(y_hole_line_s)) - pie_pad, width, height)

    if return_bgr:
        return bgr_frame
    return Image.fromarray(bgr_frame).convert("RGBA")


_TITLE_STAMP_CACHE = {}


def _get_title_overlay_stamp(width, height, scale, title_text, credit_text, mode):
    """
    タイトル・クレジット表示用の透過RGBAスタンプ（bgr, alpha, x0, y0）を生成・キャッシュします。
    mode: 'intro_center' | 'top_left' | 'top_right'
    """
    key = (width, height, round(scale, 3), str(title_text), str(credit_text), mode)
    cached = _TITLE_STAMP_CACHE.get(key)
    if cached is not None:
        return cached

    t_str = str(title_text or "").strip()
    c_str = str(credit_text or "").strip()
    if not t_str and not c_str:
        res = (None, None, 0, 0)
        _TITLE_STAMP_CACHE[key] = res
        return res

    if mode == "intro_center":
        f_title = get_truetype_font("meiryo.ttc", max(16, int(34 * scale)))
        f_cred = get_truetype_font("meiryo.ttc", max(11, int(18 * scale)))
        dummy = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        d_draw = ImageDraw.Draw(dummy)
        tw = d_draw.textlength(t_str, font=f_title) if t_str else 0
        cw = d_draw.textlength(c_str, font=f_cred) if c_str else 0

        card_w = min(int(width * 0.88), max(int(360 * scale), int(max(tw, cw) + 80 * scale)))
        card_h = int((132 if (t_str and c_str) else 96) * scale)
        card_w = max(64, card_w)
        card_h = max(48, card_h)

        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r = max(6, int(12 * scale))
        draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=r, fill=(12, 16, 26, 225), outline=(0, 210, 255, 210), width=max(1, int(2 * scale)))
        # 上下のアクセントライン
        line_m = int(18 * scale)
        draw.line([(line_m, int(6 * scale)), (card_w - line_m, int(6 * scale))], fill=(255, 165, 30, 200), width=max(1, int(2 * scale)))
        draw.line([(line_m, card_h - int(7 * scale)), (card_w - line_m, card_h - int(7 * scale))], fill=(0, 210, 255, 180), width=max(1, int(2 * scale)))

        cx = card_w // 2
        if t_str and c_str:
            draw_bordered_text_pillow(draw, (cx, int(card_h * 0.38)), t_str, "#FFFFFF", f_title, border_width=max(1, int(2.5 * scale)))
            draw_bordered_text_pillow(draw, (cx, int(card_h * 0.74)), c_str, "#00e5ff", f_cred, border_width=max(1, int(1.5 * scale)))
        elif t_str:
            draw_bordered_text_pillow(draw, (cx, card_h // 2), t_str, "#FFFFFF", f_title, border_width=max(1, int(2.5 * scale)))
        else:
            draw_bordered_text_pillow(draw, (cx, card_h // 2), c_str, "#00e5ff", f_cred, border_width=max(1, int(1.5 * scale)))

        x0 = (width - card_w) // 2
        y0 = max(10, int(height * 0.24) - card_h // 2)
    else:
        f_title = get_truetype_font("meiryo.ttc", max(11, int(16 * scale)))
        f_cred = get_truetype_font("meiryo.ttc", max(9, int(11 * scale)))
        dummy = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        d_draw = ImageDraw.Draw(dummy)
        tw = d_draw.textlength(t_str, font=f_title) if t_str else 0
        cw = d_draw.textlength(c_str, font=f_cred) if c_str else 0

        pad_x = max(10, int(14 * scale))
        card_w = min(int(width * 0.65), max(int(110 * scale), int(max(tw, cw) + pad_x * 2 + 8 * scale)))
        card_h = int((52 if (t_str and c_str) else 34) * scale)
        card_w = max(48, card_w)
        card_h = max(24, card_h)

        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r = max(4, int(8 * scale))
        draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=r, fill=(14, 18, 28, 195), outline=(80, 130, 170, 170), width=max(1, int(1.2 * scale)))

        cx = card_w // 2
        if t_str and c_str:
            draw_bordered_text_pillow(draw, (cx, int(card_h * 0.36)), t_str, "#FFFFFF", f_title, border_width=max(1, int(1.5 * scale)))
            draw_bordered_text_pillow(draw, (cx, int(card_h * 0.75)), c_str, "#b2ebf2", f_cred, border_width=max(1, int(1.0 * scale)))
        elif t_str:
            draw_bordered_text_pillow(draw, (cx, card_h // 2), t_str, "#FFFFFF", f_title, border_width=max(1, int(1.5 * scale)))
        else:
            draw_bordered_text_pillow(draw, (cx, card_h // 2), c_str, "#b2ebf2", f_cred, border_width=max(1, int(1.0 * scale)))

        margin_x = max(8, int(14 * scale))
        margin_y = max(8, int(12 * scale))
        if mode == "top_right":
            x0 = max(0, width - card_w - margin_x)
        else:
            x0 = margin_x
        y0 = margin_y

    arr = np.asarray(img)
    rgb_stamp = arr[:, :, :3].astype(np.float32)
    alpha_stamp = (arr[:, :, 3:4].astype(np.float32)) / 255.0
    res = (rgb_stamp, alpha_stamp, x0, y0)
    _TITLE_STAMP_CACHE[key] = res
    return res


def apply_title_overlay_bgr(bgr_frame, width, height, scale, title_template, title_text, credit_text,
                            current_time, intro_display_dur=2.5, is_single_preview=False):
    """
    選択されたタイトル配置テンプレート（イントロ中央・左上常時・右上常時・組み合わせ）に従い、
    事前キャッシュ済みスタンプを高速ブレンドします。
    """
    tpl = str(title_template or "なし")
    if tpl == "なし":
        return bgr_frame
    if not str(title_text or "").strip() and not str(credit_text or "").strip():
        return bgr_frame

    def _blend_stamp(stamp_tuple, fade_mul=1.0):
        bgr_st, al_st, x0, y0 = stamp_tuple
        if bgr_st is None or fade_mul <= 0.01:
            return
        sh, sw = bgr_st.shape[:2]
        dx0 = max(0, x0)
        dy0 = max(0, y0)
        dx1 = min(width, x0 + sw)
        dy1 = min(height, y0 + sh)
        if dx1 > dx0 and dy1 > dy0:
            sx0 = dx0 - x0
            sy0 = dy0 - y0
            sx1 = sx0 + (dx1 - dx0)
            sy1 = sy0 + (dy1 - dy0)
            sub_bg = bgr_frame[dy0:dy1, dx0:dx1].astype(np.float32)
            sub_st = bgr_st[sy0:sy1, sx0:sx1]
            sub_al = al_st[sy0:sy1, sx0:sx1] * float(fade_mul)
            bgr_frame[dy0:dy1, dx0:dx1] = (sub_bg * (1.0 - sub_al) + sub_st * sub_al).astype(np.uint8)

    show_intro = ("イントロ中央" in tpl)
    show_left = ("左上常時" in tpl)
    show_right = ("右上常時" in tpl)

    eff_intro_dur = max(1.5, float(intro_display_dur))
    in_intro_window = is_single_preview or (current_time < eff_intro_dur)

    if show_intro and in_intro_window:
        if is_single_preview:
            fade = 1.0
        elif current_time < 0.35:
            fade = max(0.15, current_time / 0.35)
        elif current_time > eff_intro_dur - 0.45:
            fade = max(0.0, (eff_intro_dur - current_time) / 0.45)
        else:
            fade = 1.0
        st = _get_title_overlay_stamp(width, height, scale, title_text, credit_text, "intro_center")
        _blend_stamp(st, fade)

    if show_left and (not show_intro or not in_intro_window or is_single_preview):
        st = _get_title_overlay_stamp(width, height, scale, title_text, credit_text, "top_left")
        _blend_stamp(st, 1.0)
    elif show_right and (not show_intro or not in_intro_window or is_single_preview):
        st = _get_title_overlay_stamp(width, height, scale, title_text, credit_text, "top_right")
        _blend_stamp(st, 1.0)

    return bgr_frame


def execute_single_frame_preview(midi_notes, current_bpm, current_time,
                                 res_mode, inst_type, notation_mode, bg_color, 
                                 is_hole_num_on, is_legend_on, is_notes_on, is_grid_on, is_glow_on, note_opacity,
                                 parent_window, color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                                 aspect_ratio="16:9", use_skin=True, trajectory_mode="3段階 (練習標準)",
                                 show_lookahead=True, show_grid4=True, measures_timeline=None,
                                 use_ring=True, note_speed_ratio=1.0,
                                 title_template="なし", video_title="", video_credit="",
                                 bg_image_path=None, bg_brightness=1.0,
                                 bg_fit_mode="中央トリミング (画面いっぱい)",
                                 bg_rotation="0° (自動補正)"):
    if not PILLOW_AVAILABLE:
        return

    width, height, scale = resolve_resolution_and_scale(res_mode, aspect_ratio)

    try:
        opacity_val = float(note_opacity) / 100.0
    except Exception:
        opacity_val = 0.5

    bgr_base = draw_harmonica_pillow_frame_exporter(
        width=width,
        height=height,
        scale=scale,
        canvas_bg_color=bg_color,
        inst_type=inst_type,
        lang_seg_value=notation_mode,
        is_hole_num_on=is_hole_num_on,               
        is_legend_on=is_legend_on,                   
        is_notes_on=is_notes_on,                           
        is_grid_on=is_grid_on,                       
        note_opacity_value=opacity_val,
        midi_notes=midi_notes,
        current_time=current_time,
        current_bpm=current_bpm,
        active_pitches=None,
        show_glow_effect=is_glow_on,
        color_blow_hex=color_blow_hex,                
        color_draw_hex=color_draw_hex,
        use_skin=use_skin,
        trajectory_mode=trajectory_mode,
        show_lookahead=show_lookahead,
        show_grid4=show_grid4,
        measures_timeline=measures_timeline,
        use_ring=use_ring,
        note_speed_ratio=note_speed_ratio,
        bg_image_path=bg_image_path,
        bg_brightness=bg_brightness,
        bg_fit_mode=bg_fit_mode,
        bg_rotation=bg_rotation,
        return_bgr=True
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

    if (width, height) != (preview_w, preview_h):
        bgr_notes_part = np.asarray(Image.fromarray(bgr_base).resize((preview_w, preview_h), Image.Resampling.BILINEAR))
    else:
        bgr_notes_part = bgr_base

    preview_canvas = Image.new("RGB", (960, 540), (20, 20, 20))
    if is_notes_on:
        bgr_notes_part = apply_opencv_vector_notes_draw(
            bgr_frame=bgr_notes_part,
            width=preview_w,
            height=preview_h,
            scale=preview_w / 960.0,
            inst_type=inst_type,
            midi_notes=midi_notes,
            current_time=current_time,
            current_bpm=current_bpm,
            active_pitches=None,
            note_opacity_value=opacity_val,
            color_blow_hex=color_blow_hex,
            color_draw_hex=color_draw_hex,
            aspect_ratio=aspect_ratio,
            trajectory_mode=trajectory_mode,
            lang_seg_value=notation_mode,
            show_lookahead=show_lookahead,
            note_speed_ratio=note_speed_ratio
        )

    bgr_notes_part = apply_title_overlay_bgr(
        bgr_frame=bgr_notes_part,
        width=preview_w,
        height=preview_h,
        scale=preview_w / 960.0,
        title_template=title_template,
        title_text=video_title,
        credit_text=video_credit,
        current_time=current_time,
        intro_display_dur=2.5,
        is_single_preview=True
    )
    
    preview_canvas.paste(Image.fromarray(bgr_notes_part), ((960 - preview_w)//2, (540 - preview_h)//2))
    pil_final_preview = preview_canvas
    
    pop_win = ctk.CTkToplevel(parent_window)
    pop_win.title(f"📸 1枚絵完成プレビュー - {res_mode} ({current_time:.2f}秒)")
    pop_win.geometry(f"980x580")
    pop_win.resizable(False, False)
    
    pop_win.lift()
    pop_win.attributes("-topmost", True)
    
    ctk_img = ctk.CTkImage(light_image=pil_final_preview, size=(960, 540))
    pop_win.ctk_img = ctk_img 
    
    lbl_img = ctk.CTkLabel(pop_win, image=ctk_img, text="")
    lbl_img.pack(padx=10, pady=10)
    
    btn_close = ctk.CTkButton(pop_win, text="閉じる", fg_color="#555555", hover_color="#444444", width=100, command=pop_win.destroy)
    btn_close.pack(pady=(0, 10))


def _get_note_label_stamp(text_str, font_size, bw):
    key = (text_str, font_size, bw)
    cached = _LABEL_STAMP_CACHE.get(key)
    if cached is not None:
        return cached
    f_lbl = get_truetype_font("meiryo.ttc", font_size)
    pad_w = max(24, int(font_size * max(2, len(text_str)) + bw * 4 + 12))
    pad_h = max(20, int(font_size * 2.2 + bw * 4 + 12))
    cx = pad_w // 2
    cy = pad_h // 2
    img = Image.new("RGBA", (pad_w, pad_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_bordered_text_pillow(draw, (cx, cy), text_str, "#FFFFFF", f_lbl, border_width=bw)
    bbox = img.getbbox()
    if not bbox:
        res = (None, None, 0, 0)
        _LABEL_STAMP_CACHE[key] = res
        return res
    bx0, by0, bx1, by1 = bbox
    cropped = np.asarray(img.crop(bbox))
    rgb_stamp = cropped[:, :, :3].astype(np.float32)
    alpha_stamp = (cropped[:, :, 3:4].astype(np.float32)) * (1.0 / 255.0)
    premul_rgb = rgb_stamp * alpha_stamp
    inv_alpha = 1.0 - alpha_stamp
    res = (premul_rgb, inv_alpha, cx - bx0, cy - by0)
    _LABEL_STAMP_CACHE[key] = res
    return res


def apply_opencv_vector_notes_draw(bgr_frame, width, height, scale, inst_type, midi_notes, 
                                   current_time, current_bpm, active_pitches, note_opacity_value,
                                   color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                                   aspect_ratio="16:9", trajectory_mode="3段階 (練習標準)",
                                   lang_seg_value="CDE", show_lookahead=True,
                                   note_speed_ratio=1.0):
    """
    OpenCVの LINE_AA を用いて、斜め面取りされたソリッドでシャープな幾何学多角形ノーツを合成描画。
    「3段階 (練習標準)」「垂直落下 (穴直上)」「2段階 (ビジュアル)」の3モードすべてに対応。
    二分探索ウィンドウ抽出・Pillow & NumPyによる高速ROIブレンド・事前乗算音名ラベルスタンプにより高速化。
    """
    if not midi_notes:
        return bgr_frame

    color_blow_rgb = hex_to_rgb(color_blow_hex)
    color_draw_rgb = hex_to_rgb(color_draw_hex)

    y_center_full, y_collide_full, y_straight_full, y_hole_line_full, height_diag_full, height_straight_full = get_y_trajectory_params(height / scale, trajectory_mode)
    y_collide_s = y_collide_full * scale
    y_straight_s = y_straight_full * scale
    y_hole_line_s = y_hole_line_full * scale
    height_diag_s = height_diag_full * scale
    height_straight_s = height_straight_full * scale
    is_straight_mode = ("垂直落下" in str(trajectory_mode))

    _, _, _, X_shift_notes = get_layout_params(inst_type, scale)
    pixels_per_second = (220.0 * current_bpm * max(0.1, float(note_speed_ratio))) / 240.0
    px_per_sec_s = pixels_per_second * scale
    note_labels_to_draw = []
    polys_to_draw = []
    stripes_to_draw = []
    is_jp = ("ドレミ" in str(lang_seg_value))

    start_times, max_dur = _get_exporter_notes_index(midi_notes, inst_type)
    idx_start = bisect.bisect_left(start_times, current_time - max_dur - 0.05)
    max_visible_time = current_time + (y_hole_line_s / px_per_sec_s) + 0.1 if px_per_sec_s > 0 else current_time + 20.0
    n_total = len(midi_notes)

    zone_h = min(height, int(math.ceil(y_hole_line_s)) + 2)
    min_x, min_y = width, zone_h
    max_x, max_y = 0, 0

    for i in range(idx_start, n_total):
        note_data = midi_notes[i]
        start_t = note_data["start_time"]
        if start_t > max_visible_time:
            break
        end_t = start_t + note_data["duration"]
        
        y_bottom = y_hole_line_s - (start_t - current_time) * px_per_sec_s
        y_top = y_hole_line_s - (end_t - current_time) * px_per_sec_s
        
        if y_bottom >= 0 and y_top <= y_hole_line_s:
            start_tick = note_data.get("start_tick", 0)
            bound_ok = (note_data.get("_bound_inst") == inst_type)
            fing = note_data.get("fingering") if bound_ok else get_note_fingering_for_song(start_tick, note_data["note"], inst_type)
            if not fing: 
                continue
            
            col_rgb = color_blow_rgb if fing["action"] == "吹" else color_draw_rgb
            
            simulated_note = note_data["note"]
            if "バス" in inst_type:
                simulated_note = note_data["note"] + 36
                
            lane_idx = simulated_note - 48
            lane_x_left = (72.0 + lane_idx * 16.0) * scale - X_shift_notes
            lane_x_right = lane_x_left + 16.0 * scale
            
            note_in_range = note_data["in_range"] if bound_ok else is_note_in_range(note_data["note"], inst_type)
            if not note_in_range and is_straight_mode:
                continue

            dest_x_center = (note_data["dest_x_base"] * scale) if bound_ok else get_note_dest_x(note_data["note"], inst_type, scale, start_tick=start_tick)
            dest_left = dest_x_center - 6.0 * scale
            dest_right = dest_x_center + 6.0 * scale

            y_limit_bot = y_hole_line_s if note_in_range else y_collide_s
            y_vis_top = max(0.0, y_top)
            y_vis_bot = min(y_limit_bot, y_bottom)
            if y_vis_bot <= y_vis_top:
                continue

            if is_straight_mode:
                def x_left_at(yv): return dest_left
                def x_right_at(yv): return dest_right
                bend_ys = []
            else:
                def x_left_at(yv):
                    if yv <= y_collide_s:
                        return lane_x_left
                    elif yv >= y_straight_s:
                        return dest_left
                    else:
                        r = (yv - y_collide_s) / height_diag_s
                        return lane_x_left + (dest_left - lane_x_left) * r

                def x_right_at(yv):
                    if yv <= y_collide_s:
                        return lane_x_right
                    elif yv >= y_straight_s:
                        return dest_right
                    else:
                        r = (yv - y_collide_s) / height_diag_s
                        return lane_x_right + (dest_right - lane_x_right) * r

                bend_ys = [y_collide_s, y_straight_s] if note_in_range else []

            length = max(1.0, y_vis_bot - y_vis_top)
            ch_base = min(3.5 * scale, length / 3.0)
            ch_top = ch_base if (y_top >= 0.0 and y_top < y_limit_bot) else 0.0
            ch_bot = ch_base if (y_bottom > 0.0 and y_bottom <= y_limit_bot) else 0.0

            y_r_start = y_vis_top + ch_top
            y_r_end = y_vis_bot - ch_bot
            active_bends = [by for by in bend_ys if y_r_start < by < y_r_end]

            pts_accum = []
            # 上端キャップ
            if ch_top > 0.5:
                pts_accum.append([int(round(x_left_at(y_vis_top) + ch_top)), int(round(y_vis_top))])
                pts_accum.append([int(round(x_right_at(y_vis_top) - ch_top)), int(round(y_vis_top))])
                pts_accum.append([int(round(x_right_at(y_r_start))), int(round(y_r_start))])
            else:
                pts_accum.append([int(round(x_left_at(y_vis_top))), int(round(y_vis_top))])
                pts_accum.append([int(round(x_right_at(y_vis_top))), int(round(y_vis_top))])

            # 右辺の屈曲点（上から下）
            for by in active_bends:
                pts_accum.append([int(round(x_right_at(by))), int(round(by))])

            # 下端キャップ
            if ch_bot > 0.5:
                pts_accum.append([int(round(x_right_at(y_r_end))), int(round(y_r_end))])
                pts_accum.append([int(round(x_right_at(y_vis_bot) - ch_bot)), int(round(y_vis_bot))])
                pts_accum.append([int(round(x_left_at(y_vis_bot) + ch_bot)), int(round(y_vis_bot))])
                pts_accum.append([int(round(x_left_at(y_r_end))), int(round(y_r_end))])
            else:
                pts_accum.append([int(round(x_right_at(y_vis_bot))), int(round(y_vis_bot))])
                pts_accum.append([int(round(x_left_at(y_vis_bot))), int(round(y_vis_bot))])

            # 左辺の屈曲点（下から上）
            for by in reversed(active_bends):
                pts_accum.append([int(round(x_left_at(by))), int(round(by))])

            if ch_top > 0.5:
                pts_accum.append([int(round(x_left_at(y_r_start))), int(round(y_r_start))])

            if len(pts_accum) >= 3:
                pts = np.array(pts_accum, dtype=np.int32)
                polys_to_draw.append((pts, col_rgb))
                px_min = int(pts[:, 0].min()) - 2
                px_max = int(pts[:, 0].max()) + 3
                py_min = int(pts[:, 1].min()) - 2
                py_max = int(pts[:, 1].max()) + 3
                if px_min < min_x: min_x = px_min
                if px_max > max_x: max_x = px_max
                if py_min < min_y: min_y = py_min
                if py_max > max_y: max_y = py_max

                # レバーON時：右端同系色ハイライトストライプ（白のときは黒ライン）
                is_lever_on = (fing.get("lever") == "押す" or fing.get("lever") is True)
                if is_lever_on:
                    stripe_w = min(4.5 * scale, max(2.5, 3.2 * scale))
                    cur_hex = color_blow_hex if fing["action"] == "吹" else color_draw_hex
                    hi_rgb = get_lever_highlight_rgb(cur_hex)
                    stripe_accum = []
                    # 右上角（面取り開始または右上端）
                    if ch_top > 0.5:
                        stripe_accum.append([int(round(x_right_at(y_vis_top) - ch_top)), int(round(y_vis_top))])
                        stripe_accum.append([int(round(x_right_at(y_r_start))), int(round(y_r_start))])
                    else:
                        stripe_accum.append([int(round(x_right_at(y_vis_top))), int(round(y_vis_top))])

                    # 右辺の屈曲点（上から下）
                    for by in active_bends:
                        stripe_accum.append([int(round(x_right_at(by))), int(round(by))])

                    # 右下角（面取り）
                    if ch_bot > 0.5:
                        stripe_accum.append([int(round(x_right_at(y_r_end))), int(round(y_r_end))])
                        stripe_accum.append([int(round(x_right_at(y_vis_bot) - ch_bot)), int(round(y_vis_bot))])
                        stripe_accum.append([int(round(max(x_left_at(y_vis_bot) + ch_bot, x_right_at(y_vis_bot) - ch_bot - stripe_w))), int(round(y_vis_bot))])
                        stripe_accum.append([int(round(max(x_left_at(y_r_end), x_right_at(y_r_end) - stripe_w))), int(round(y_r_end))])
                    else:
                        stripe_accum.append([int(round(x_right_at(y_vis_bot))), int(round(y_vis_bot))])
                        stripe_accum.append([int(round(max(x_left_at(y_vis_bot), x_right_at(y_vis_bot) - stripe_w))), int(round(y_vis_bot))])

                    # 内側を上へ遡る（下から上）
                    for by in reversed(active_bends):
                        stripe_accum.append([int(round(max(x_left_at(by), x_right_at(by) - stripe_w))), int(round(by))])

                    # 内側上端
                    if ch_top > 0.5:
                        stripe_accum.append([int(round(max(x_left_at(y_r_start), x_right_at(y_r_start) - stripe_w))), int(round(y_r_start))])
                        stripe_accum.append([int(round(max(x_left_at(y_vis_top) + ch_top, x_right_at(y_vis_top) - ch_top - stripe_w))), int(round(y_vis_top))])
                    else:
                        stripe_accum.append([int(round(max(x_left_at(y_vis_top), x_right_at(y_vis_top) - stripe_w))), int(round(y_vis_top))])

                    if len(stripe_accum) >= 3:
                        pts_s = np.array(stripe_accum, dtype=np.int32)
                        stripes_to_draw.append((pts_s, hi_rgb))

            # 案A：落下ノーツ追従音名ラベルの座標収集
            if show_lookahead and lang_seg_value != "なし" and (y_vis_bot - y_vis_top >= 6.0 * scale) and y_vis_bot >= 8.0 * scale:
                label_y = y_vis_bot - 8.5 * scale if (y_vis_bot - y_vis_top >= 17.0 * scale) else (y_vis_top + y_vis_bot) / 2.0
                lane_cx = (lane_x_left + lane_x_right) / 2.0
                if is_straight_mode or label_y >= y_straight_s:
                    label_x = dest_x_center
                elif label_y <= y_collide_s or not note_in_range:
                    label_x = lane_cx
                else:
                    ratio_lbl = (label_y - y_collide_s) / height_diag_s if height_diag_s > 0 else 1.0
                    label_x = lane_cx + (dest_x_center - lane_cx) * ratio_lbl
                n_str = (note_data["name_jp"] if is_jp else note_data["name_cde"]) if bound_ok else get_note_name(note_data["note"], is_japanese=is_jp)
                note_labels_to_draw.append((label_x, label_y, n_str))

    if polys_to_draw and max_x > min_x and max_y > min_y:
        rx0 = max(0, min_x)
        rx1 = min(width, max_x)
        ry0 = max(0, min_y)
        ry1 = min(zone_h, max_y)
        if rx1 > rx0 and ry1 > ry0:
            op_val = max(0.0, min(1.0, float(note_opacity_value)))
            roi_w = rx1 - rx0
            roi_h = ry1 - ry0
            roi_overlay = Image.new("RGBA", (roi_w, roi_h), (0, 0, 0, 0))
            roi_draw = ImageDraw.Draw(roi_overlay)
            alpha_int = int(round(255 * op_val))

            for pts, col_rgb in polys_to_draw:
                poly_pts = [(int(p[0] - rx0), int(p[1] - ry0)) for p in pts]
                if len(poly_pts) >= 3:
                    roi_draw.polygon(poly_pts, fill=(col_rgb[0], col_rgb[1], col_rgb[2], alpha_int))

            for s_pts, s_col_rgb in stripes_to_draw:
                s_poly_pts = [(int(p[0] - rx0), int(p[1] - ry0)) for p in s_pts]
                if len(s_poly_pts) >= 3:
                    roi_draw.polygon(s_poly_pts, fill=(s_col_rgb[0], s_col_rgb[1], s_col_rgb[2], alpha_int))

            arr_overlay = np.asarray(roi_overlay)
            ov_alpha = (arr_overlay[:, :, 3:4].astype(np.float32)) * (1.0 / 255.0)
            ov_rgb = arr_overlay[:, :, :3].astype(np.float32)
            sub_bg = bgr_frame[ry0:ry1, rx0:rx1].astype(np.float32)
            bgr_frame[ry0:ry1, rx0:rx1] = (sub_bg * (1.0 - ov_alpha) + ov_rgb * ov_alpha).astype(np.uint8)

    if note_labels_to_draw:
        f_size = max(6, int(9 * scale))
        bw = max(1, int(1.5 * scale))
        for lx, ly, l_str in note_labels_to_draw:
            premul_rgb, inv_alpha, cx_off, cy_off = _get_note_label_stamp(l_str, f_size, bw)
            if premul_rgb is None:
                continue
            sh, sw = premul_rgb.shape[:2]
            x0 = int(round(lx)) - cx_off
            y0 = int(round(ly)) - cy_off
            x1 = x0 + sw
            y1 = y0 + sh
            sx0 = max(0, -x0)
            sy0 = max(0, -y0)
            dx0 = max(0, x0)
            dy0 = max(0, y0)
            dx1 = min(width, x1)
            dy1 = min(height, y1)
            if dx1 > dx0 and dy1 > dy0:
                sx1 = sx0 + (dx1 - dx0)
                sy1 = sy0 + (dy1 - dy0)
                sub_bg = bgr_frame[dy0:dy1, dx0:dx1]
                bgr_frame[dy0:dy1, dx0:dx1] = (
                    sub_bg.astype(np.float32) * inv_alpha[sy0:sy1, sx0:sx1] + premul_rgb[sy0:sy1, sx0:sx1]
                ).astype(np.uint8)

    return bgr_frame


def _build_export_timeline(midi_notes, accompaniment_notes, measures_timeline, max_duration,
                           export_range, intro_sec, outro_sec, ctrl):
    """
    動画出力範囲（全曲 / A〜B小節のみ）およびイントロ・アウトロ秒数に従い、
    練習用データを破壊せずに動画書き出し専用のタイムライン（ノーツ・伴奏・小節線・総尺・開始原曲秒）を構築します。
    """
    count_in_dur = ctrl.get_count_in_duration() if (ctrl and hasattr(ctrl, "get_count_in_duration")) else 0.0
    in_s = max(0.0, float(intro_sec))
    out_s = max(0.0, float(outro_sec))

    if export_range == "A〜B小節のみ" and measures_timeline and ctrl and hasattr(ctrl, "gui"):
        total_m = len(measures_timeline)
        try:
            val_a = max(1, min(total_m, int(ctrl.gui.loop_a_entry.get())))
        except Exception:
            val_a = 1
        try:
            val_b = max(1, min(total_m, int(ctrl.gui.loop_b_entry.get())))
        except Exception:
            val_b = total_m
        if val_a > val_b:
            val_a, val_b = 1, total_m

        start_tick_a = measures_timeline[val_a - 1]["start_tick"]
        end_tick_b = measures_timeline[val_b - 1]["end_tick"]
        sec_a_in_song = ctrl.midi_engine.tick_to_sec(start_tick_a)
        sec_b_in_song = ctrl.midi_engine.tick_to_sec(end_tick_b)

        win_start = sec_a_in_song + count_in_dur
        win_end = sec_b_in_song + count_in_dur
        time_shift = -sec_a_in_song + in_s

        exp_notes = []
        for n in (midi_notes or []):
            ns = n["start_time"]
            ne = ns + n["duration"]
            if ne > win_start + 1e-4 and ns < win_end - 1e-4:
                nc = dict(n)
                s_clamp = max(win_start, ns)
                e_clamp = min(win_end, ne)
                nc["start_time"] = s_clamp + time_shift
                nc["duration"] = max(0.02, e_clamp - s_clamp)
                exp_notes.append(nc)

        exp_acc = []
        for an in (accompaniment_notes or []):
            ans = an.get("start_time", an.get("original_start_time", 0.0) + count_in_dur)
            ane = ans + an.get("duration", an.get("original_duration", 0.1))
            if ane > win_start + 1e-4 and ans < win_end - 1e-4:
                ac = dict(an)
                s_clamp = max(win_start, ans)
                e_clamp = min(win_end, ane)
                ac["start_time"] = s_clamp + time_shift
                ac["duration"] = max(0.02, e_clamp - s_clamp)
                exp_acc.append(ac)

        exp_measures = []
        for m in measures_timeline:
            m_num = m.get("measure_num", 1)
            if val_a <= m_num <= val_b:
                mc = dict(m)
                m_orig = m.get("start_time", ctrl.midi_engine.tick_to_sec(m["start_tick"]) + count_in_dur)
                mc["start_time"] = m_orig + time_shift
                exp_measures.append(mc)

        exp_max_dur = max(0.5, (sec_b_in_song - sec_a_in_song) + count_in_dur + in_s + out_s)
        return exp_notes, exp_acc, exp_measures, exp_max_dur, sec_a_in_song, count_in_dur

    # 全曲出力
    sec_a_in_song = 0.0
    if in_s > 0.0:
        exp_notes = []
        for n in (midi_notes or []):
            nc = dict(n)
            nc["start_time"] = n["start_time"] + in_s
            exp_notes.append(nc)
        exp_acc = []
        for an in (accompaniment_notes or []):
            ac = dict(an)
            ans = an.get("start_time", an.get("original_start_time", 0.0) + count_in_dur)
            ac["start_time"] = ans + in_s
            exp_acc.append(ac)
        exp_measures = []
        for m in (measures_timeline or []):
            mc = dict(m)
            if "start_time" in m:
                mc["start_time"] = m["start_time"] + in_s
            elif ctrl and hasattr(ctrl, "midi_engine"):
                mc["start_time"] = ctrl.midi_engine.tick_to_sec(m["start_tick"]) + count_in_dur + in_s
            exp_measures.append(mc)
    else:
        exp_notes = midi_notes or []
        exp_acc = accompaniment_notes or []
        exp_measures = measures_timeline or []

    exp_max_dur = max(0.5, float(max_duration) + in_s + out_s)
    return exp_notes, exp_acc, exp_measures, exp_max_dur, sec_a_in_song, count_in_dur


def execute_video_export_core(midi_notes, current_bpm, max_duration, is_count_in, is_metro,
                              res_mode, inst_type, notation_mode, bg_color, 
                              is_hole_num_on, is_legend_on, is_notes_on, is_grid_on, is_glow_on, note_opacity,
                              current_midi_path, status_label, export_btn, root_after,
                              ticks_per_beat=480, fps_mode="60 FPS",
                              color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                              aspect_ratio="16:9", use_skin=True, controller=None,
                              trajectory_mode="3段階 (練習標準)",
                              show_lookahead=True, show_grid4=True, measures_timeline=None,
                              use_ring=True, note_speed_ratio=1.0,
                              export_range="全曲", intro_sec=0.0, outro_sec=2.0,
                              title_template="なし", video_title="", video_credit="",
                              ext_audio_pcm=None, ext_audio_mode="頭出し確認 (再生:両方 / 動画:外部のみ)",
                              ext_audio_offset_ms=0, ext_audio_vol_pct=100.0, yt_limiter=True,
                              bg_image_path=None, bg_brightness=1.0,
                              bg_fit_mode="中央トリミング (画面いっぱい)",
                              bg_rotation="0° (自動補正)",
                              fade_in=False, fade_out=False,
                              fade_in_title_mode="フェード中もタイトル表示",
                              reverb_enabled=False,
                              reverb_type="ルーム (自然な部屋鳴り)",
                              reverb_wet_pct=35):
    if not PILLOW_AVAILABLE:
        status_label.configure(text="エラー: 描画ライブラリが不足しています", text_color="#ff5555")
        return

    status_label.configure(text="🎬 動画エクスポートの準備中...", text_color="#ffcc00")

    temp_dir = get_portable_path("temp")
    output_dir = get_portable_path("output")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    if current_midi_path:
        midi_filename = os.path.basename(current_midi_path)
        midi_name_only, _ = os.path.splitext(midi_filename)
        out_filename = f"{midi_name_only}.mp4"
    else:
        midi_name_only = "chromatic_harmonica_output"
        out_filename = "chromatic_harmonica_output.mp4"

    temp_video_path = os.path.join(temp_dir, "temp_silent.mp4")
    temp_audio_path = os.path.join(temp_dir, "temp_audio.wav")
    final_output_path = os.path.join(output_dir, out_filename)

    width, height, scale = resolve_resolution_and_scale(res_mode, aspect_ratio)

    try:
        opacity_val = float(note_opacity) / 100.0
    except Exception:
        opacity_val = 0.5

    try:
        fps = int(str(fps_mode).split()[0])
    except Exception:
        fps = 60

    ctrl = controller
    if ctrl is None:
        try:
            ctrl = status_label.master.master.master.controller
        except Exception:
            ctrl = None

    raw_acc_notes = getattr(ctrl, "accompaniment_notes", None) if ctrl else None
    exp_notes, exp_acc_notes, exp_measures, exp_max_duration, sec_a_in_song, count_in_dur = _build_export_timeline(
        midi_notes=midi_notes,
        accompaniment_notes=raw_acc_notes,
        measures_timeline=measures_timeline,
        max_duration=max_duration,
        export_range=export_range,
        intro_sec=intro_sec,
        outro_sec=outro_sec,
        ctrl=ctrl
    )
    intro_display_dur = intro_sec if intro_sec > 0.0 else (count_in_dur if count_in_dur > 0.0 else 2.5)
    fade_in_dur = (float(intro_sec) if float(intro_sec) > 0.0 else min(1.5, exp_max_duration * 0.25)) if fade_in else 0.0
    fade_out_dur = (float(outro_sec) if float(outro_sec) > 0.0 else min(1.5, exp_max_duration * 0.25)) if fade_out else 0.0
    title_mode_str = str(fade_in_title_mode or "フェード中もタイトル表示")

    def render_worker():
        try:
            total_frames = int(exp_max_duration * fps)
            if total_frames <= 0:
                total_frames = 600 
                
            ffmpeg_video_cmd = [
                "ffmpeg", "-y",
                "-f", "rawvideo",
                "-vcodec", "rawvideo",
                "-s", f"{width}x{height}",
                "-pix_fmt", "rgb24",
                "-r", str(fps),
                "-i", "-",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "veryfast",
                "-crf", "18",
                temp_video_path
            ]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            video_proc = subprocess.Popen(
                ffmpeg_video_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo
            )

            print(f"[Export] 高解像度ベクトル描画レンダリング開始 (FFmpeg RawPipe): {width}x{height} (Scale: {scale}, FPS: {fps}), 総フレーム: {total_frames}")

            _get_exporter_notes_index(exp_notes, inst_type)
            last_percent = -1

            for frame_idx in range(total_frames):
                try:
                    if ctrl and getattr(ctrl, "video_export_cancelled", False):
                        print("[Export] レンダリングがユーザーによって正常に中止されました。")
                        try:
                            video_proc.kill()
                        except Exception:
                            pass
                        if os.path.exists(temp_video_path):
                            try: os.remove(temp_video_path)
                            except Exception: pass
                        root_after(0, lambda: ctrl.on_export_finished_or_cancelled("cancelled"))
                        return
                except Exception:
                    pass

                current_time_sec = frame_idx / fps

                bgr_frame = draw_harmonica_pillow_frame_exporter(
                    width=width,
                    height=height,
                    scale=scale,
                    canvas_bg_color=bg_color,
                    inst_type=inst_type,
                    lang_seg_value=notation_mode,
                    is_hole_num_on=is_hole_num_on,
                    is_legend_on=is_legend_on,
                    is_notes_on=is_notes_on,                  
                    is_grid_on=is_grid_on,
                    note_opacity_value=opacity_val,
                    midi_notes=exp_notes,
                    current_time=current_time_sec,
                    current_bpm=current_bpm,
                    active_pitches=None,
                    show_glow_effect=is_glow_on,
                    color_blow_hex=color_blow_hex,            
                    color_draw_hex=color_draw_hex,
                    use_skin=use_skin,
                    trajectory_mode=trajectory_mode,
                    show_lookahead=show_lookahead,
                    show_grid4=show_grid4,
                    measures_timeline=exp_measures,
                    use_ring=use_ring,
                    note_speed_ratio=note_speed_ratio,
                    bg_image_path=bg_image_path,
                    bg_brightness=bg_brightness,
                    bg_fit_mode=bg_fit_mode,
                    bg_rotation=bg_rotation,
                    return_bgr=True
                )
                
                if is_notes_on:
                    bgr_frame = apply_opencv_vector_notes_draw(
                        bgr_frame=bgr_frame,
                        width=width,
                        height=height,
                        scale=scale,
                        inst_type=inst_type,
                        midi_notes=exp_notes,
                        current_time=current_time_sec,
                        current_bpm=current_bpm,
                        active_pitches=None,
                        note_opacity_value=opacity_val,
                        color_blow_hex=color_blow_hex,
                        color_draw_hex=color_draw_hex,
                        aspect_ratio=aspect_ratio,
                        trajectory_mode=trajectory_mode,
                        lang_seg_value=notation_mode,
                        show_lookahead=show_lookahead,
                        note_speed_ratio=note_speed_ratio
                    )

                in_alpha = (
                    max(0.0, min(1.0, current_time_sec / fade_in_dur))
                    if (fade_in and fade_in_dur > 1e-4 and current_time_sec < fade_in_dur)
                    else 1.0
                )
                rem_sec = max(0.0, exp_max_duration - (frame_idx + 1) / fps)
                out_alpha = (
                    max(0.0, min(1.0, rem_sec / fade_out_dur))
                    if (fade_out and fade_out_dur > 1e-4 and rem_sec < fade_out_dur)
                    else 1.0
                )

                if "一緒に" in title_mode_str:
                    if title_template != "なし":
                        bgr_frame = apply_title_overlay_bgr(
                            bgr_frame=bgr_frame,
                            width=width,
                            height=height,
                            scale=scale,
                            title_template=title_template,
                            title_text=video_title,
                            credit_text=video_credit,
                            current_time=current_time_sec,
                            intro_display_dur=intro_display_dur,
                            is_single_preview=False
                        )
                    if in_alpha < 0.999:
                        np.multiply(bgr_frame, in_alpha, out=bgr_frame, casting="unsafe")
                elif "非表示" in title_mode_str:
                    if in_alpha < 0.999:
                        np.multiply(bgr_frame, in_alpha, out=bgr_frame, casting="unsafe")
                    elif title_template != "なし":
                        bgr_frame = apply_title_overlay_bgr(
                            bgr_frame=bgr_frame,
                            width=width,
                            height=height,
                            scale=scale,
                            title_template=title_template,
                            title_text=video_title,
                            credit_text=video_credit,
                            current_time=max(0.0, current_time_sec - fade_in_dur),
                            intro_display_dur=intro_display_dur,
                            is_single_preview=False
                        )
                else:
                    if in_alpha < 0.999:
                        np.multiply(bgr_frame, in_alpha, out=bgr_frame, casting="unsafe")
                    if title_template != "なし":
                        bgr_frame = apply_title_overlay_bgr(
                            bgr_frame=bgr_frame,
                            width=width,
                            height=height,
                            scale=scale,
                            title_template=title_template,
                            title_text=video_title,
                            credit_text=video_credit,
                            current_time=current_time_sec,
                            intro_display_dur=intro_display_dur,
                            is_single_preview=False
                        )

                if out_alpha < 0.999:
                    np.multiply(bgr_frame, out_alpha, out=bgr_frame, casting="unsafe")
                
                video_proc.stdin.write(bgr_frame.tobytes())

                percent = int((frame_idx + 1) / total_frames * 100)
                if percent != last_percent:
                    last_percent = percent
                    root_after(0, lambda p=percent: status_label.configure(
                        text=f"🎬 映像レンダリング中... {p}%", text_color="#ffcc00"
                    ))

            video_proc.stdin.close()
            video_proc.wait()
            print("[Export] 無音動画の生成が完了。続いて高音質WAV物理合成を開始します。")

            root_after(0, lambda: status_label.configure(
                text="🎵 高音質WAV音声を合成中...", text_color="#00ffcc"
            ))

            if ctrl and hasattr(ctrl, "midi_engine"):
                ticks_per_beat_ref = ctrl.midi_engine.ticks_per_beat
                metronome_pattern_ref = ctrl.midi_engine.metronome_pattern
                count_in_measures_ref = ctrl.midi_engine.count_in_measures if is_count_in else 0
                tick_to_sec_ref = ctrl.midi_engine.tick_to_sec
                part_play_mode_ref = getattr(ctrl.midi_engine, "part_play_mode", "全パート再生")
            else:
                ticks_per_beat_ref = ticks_per_beat
                metronome_pattern_ref = "標準（頭拍強調）"
                count_in_measures_ref = 1 if is_count_in else 0
                tick_to_sec_ref = None
                part_play_mode_ref = "全パート再生"

            synthesize_midi_to_wav(
                midi_notes=exp_notes,
                current_bpm=current_bpm,
                max_duration=exp_max_duration,
                is_count_in=is_count_in,
                is_metro=is_metro,
                output_wav_path=temp_audio_path,
                time_sig_num=4,
                time_sig_den=4,
                count_in_measures=count_in_measures_ref,
                measures_timeline=exp_measures,
                metronome_pattern=metronome_pattern_ref,
                ticks_per_beat=ticks_per_beat_ref,
                sample_rate=44100,
                tick_to_sec_fn=tick_to_sec_ref,
                accompaniment_notes=exp_acc_notes,
                part_play_mode=part_play_mode_ref,
                intro_sec=intro_sec,
                ext_audio_pcm=ext_audio_pcm,
                ext_audio_mode=ext_audio_mode,
                ext_audio_offset_ms=ext_audio_offset_ms,
                ext_audio_vol_pct=ext_audio_vol_pct,
                sec_a_in_song=sec_a_in_song,
                yt_limiter=yt_limiter
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
            ]
            if reverb_enabled and reverb_wet_pct > 0:
                from audio_engine import get_reverb_filter_arg
                af_str = get_reverb_filter_arg(reverb_type, reverb_wet_pct)
                ffmpeg_cmd.extend(["-af", af_str])
            ffmpeg_cmd.extend([
                "-map", "0:v:0",
                "-map", "1:a:0",
                final_output_path
            ])

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
                    if ctrl:
                        root_after(0, lambda: ctrl.on_export_finished_or_cancelled("success"))
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
                    if ctrl:
                        root_after(0, lambda: ctrl.on_export_finished_or_cancelled("success_split"))
                except Exception as copy_err:
                    print(f"[致命的フォールバック不全] {copy_err}")
                    root_after(0, lambda: status_label.configure(
                        text="❌ 動画の保存（フォールバック）に完全に失敗しました", text_color="#ff5555"
                    ))
                    if ctrl:
                        root_after(0, lambda: ctrl.on_export_finished_or_cancelled("failed", str(copy_err)))

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
            if ctrl:
                root_after(0, lambda e=error_details: ctrl.on_export_finished_or_cancelled("failed", e))

    t = threading.Thread(target=render_worker, daemon=True)
    t.start()
