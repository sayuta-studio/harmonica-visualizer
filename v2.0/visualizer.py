# -*- coding: utf-8 -*-
# visualizer.py (STEP 4-B: 練習モード用 Canvas レンダラー・消音マージン完全撤廃・バグ根治版)
# - 【同時点灯完全根治】：消音時の120ティック猶予マージンを完全撤廃。プリ・バインド化の完成に伴い、楽譜の演奏位置のみから一対一で正確に穴の点灯をON/OFF制御するため、高速フレーズや一時停止時に元の穴が同時に光る不整合バグを100%完全に根絶しました。
# - 🚀【マルチアスペクト・縮小フィット対応】：親ウィンドウ内に縮小スケーリング配置された Canvas に対して、内部の幾何学、ガイド線、ノーツ下落軌道を完全自動スキャンして精密にフィッティング描画します。
# - 🚀【外部スキン縮小リアルタイムペースト】：縮小スケール scale に合わせて マウスピース.png、レバー画像を動的にPillowリサイズしてTkinterキャッシュペースト。
# - 🚀【プレート内穴番号 ＆ プレート外音名】：穴番号を「穴とプレート下端の中間（+24px）」、音名を「プレートの外部（+60px）」へそれぞれ視認性向上のため入れ替えスライド。
# - 🚀【STEP 4.5 レバーサイズUP & パラパラ漫画置換】：レバースキンのサイズを 48x48px に拡大。レバーON時の座標平行スライドを完全廃止し、画像置換のみに一本化。
# - 🚀【穴周り連動レバーリング】：レバーON状態且つその穴が発音中であれば、周辺視野で察知できるネオンイエロー（#FFCC00）の連動レバーリングを自動描画。
# - 🚀【不整合修正】：ノーツ表示がオフの場合でも、ガイド線トグル単体で内側グリッドが確実に100%描画されるように修復。レバーリングへ吹吸カスタム追従カラーおよびトグルON/OFFスイッチを配備。
# - 🚀【ステンレスカチカチ押し込みレバー】：フォールバック時の赤色を廃止し美しいステンレスカラーに統一。シャフトの開始位置をプレート右端に完全吸着させ浮き隙間を解決。
# - 🚀【ベクターストローク大拡張】：スキンOFFのフォールバック表示時でもステンレス扁平楕円（16x36）を維持し、本体からの隙間を「OFF時：22px」「ON時：3px」に極端化。X移動なしで19pxの巨大沈み込みを表現！

import bisect
import math
import os
import tkinter as tk
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk

from config import (
    COLOR_BLOW_RGB, COLOR_BLOW_INNER, COLOR_DRAW_RGB, COLOR_DRAW_INNER,
    W_PITCH, D_HOLE, CANVAS_WIDTH, CANVAS_HEIGHT,
    get_canvas_height_by_ratio, get_y_layout_params, get_y_trajectory_params, get_portable_path,
    LEVER_WIDTH_DEFAULT, LEVER_HEIGHT_DEFAULT,
    get_layout_params, get_note_dest_x
)
from harmonica_map import (
    is_note_in_range, get_note_fingering, get_note_name, FINGERING_CANDIDATES,
    get_note_fingering_for_song, is_note_editable, get_hole_4_notes
)

_CACHE = {
    "key": None,          
    "base_image": None,   
}

_NOTES_INDEX_CACHE = {
    "key": None,
    "start_ticks": [],
    "max_dur_ticks": 0,
}

_BLOW_NOTES_MIDI = {
    "16穴": [48, 52, 55, 60, 60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96],
    "12穴 標準": [60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96], 
    "12穴 バス": [24, 28, 31, 35, 36, 40, 43, 47, 48, 52, 55, 59]
}


def _get_notes_index(midi_notes):
    """曲全体のノーツリストに対する二分探索用インデックスと最大長キャッシュを返します。"""
    if not midi_notes:
        return [], 0
    first_n = midi_notes[0]
    last_n = midi_notes[-1]
    cache_key = (id(midi_notes), len(midi_notes), first_n.get("start_tick", 0), last_n.get("start_tick", 0))
    if _NOTES_INDEX_CACHE["key"] != cache_key:
        _NOTES_INDEX_CACHE["key"] = cache_key
        _NOTES_INDEX_CACHE["start_ticks"] = [n.get("start_tick", 0) for n in midi_notes]
        _NOTES_INDEX_CACHE["max_dur_ticks"] = max((n.get("duration_ticks", 0) for n in midi_notes), default=0)
    return _NOTES_INDEX_CACHE["start_ticks"], _NOTES_INDEX_CACHE["max_dur_ticks"]


def draw_bordered_text_canvas(canvas, position, text, text_color, font=("Arial", 11, "bold"), border_width=2, tags="text"):
    x, y = position
    border_color = "#000000"
    for dx in range(-border_width, border_width + 1):
        for dy in range(-border_width, border_width + 1):
            if dx != 0 or dy != 0:
                canvas.create_text(x + dx, y + dy, text=text, fill=border_color, font=font, tags=tags)
    canvas.create_text(x, y, text=text, fill=text_color, font=font, tags=tags)


def draw_harmonica_canvas(canvas, canvas_bg_color, inst_type, lang_seg_value, 
                          is_hole_num_on, is_legend_on, is_notes_on, is_grid_on,
                          midi_notes=None, current_time=0.0, current_bpm=120.0, 
                          active_pitches=None, draw_mode="all", target_tick=0, ticks_per_beat=480,
                          color_blow_hex="#FF9900", color_draw_hex="#00FFFF",
                          edit_mode_active=False,
                          last_edit_note=None, last_edit_fing=None,
                          use_skin=True, scale=1.0, aspect_ratio="16:9",
                          use_ring=True, trajectory_mode="3段階 (練習標準)",
                          show_lookahead=True, show_grid4=True,
                          measures_timeline=None):  
    """
    Pillowを一切経由せず、Tkinter Canvasのネイティブ命令と差分キャッシュで超高速描画。
    変化した要素のみを更新し、落下中ノーツは座標移動(coords)のみで60fps安定動作を実現します。
    """
    if active_pitches is None: active_pitches = set()
    if midi_notes is None: midi_notes = []

    # マルチアスペクト仮想フル高さ解決
    canvas_height_full = get_canvas_height_by_ratio(aspect_ratio)
    
    # フル高さ・軌道モードに応じた下部基準Y座標を解決（3段階練習標準 / 垂直落下 / 2段階ビジュアル対応）
    y_center_full, y_collide_full, y_straight_full, y_hole_line_full, height_diag_full, height_straight_full = get_y_trajectory_params(canvas_height_full, trajectory_mode)

    # スケールを掛け合わせて、表示用Canvas内にパーフェクトにフィット縮小！
    y_center_s = y_center_full * scale
    y_collide_s = y_collide_full * scale
    y_straight_s = y_straight_full * scale
    y_hole_line_s = y_hole_line_full * scale
    height_diag_s = height_diag_full * scale
    height_straight_s = height_straight_full * scale
    is_straight_mode = ("垂直落下" in str(trajectory_mode))

    visible_indices, X_start_draw, X_shift, X_shift_notes = get_layout_params(inst_type, scale)
    N_visible = len(visible_indices)
    total_width = N_visible * W_PITCH * scale
    
    grid_line_color = "#000000" if canvas_bg_color == "#00FF00" else "#252525"
    
    note_color_blow = color_blow_hex
    note_color_draw = color_draw_hex
    is_jp = ("ドレミ" in lang_seg_value)
    mode_key = "16穴" if "16穴" in inst_type else ("12穴 標準" if "標準" in inst_type else "12穴 バス")

    # 外部スキン画像ロード ＆ 動的スケールリサイズキャッシュ
    if use_skin:
        skins_dir = get_portable_path("skins")
        face_path = os.path.join(skins_dir, "マウスピース.png")  
        lever_off_path = os.path.join(skins_dir, "レバーオフ.png")
        lever_on_path = os.path.join(skins_dir, "レバーオン.png")

        if not hasattr(canvas, "skin_cache"):
            canvas.skin_cache = {}

        cache_key = f"{inst_type}_{scale}_{aspect_ratio}"
        if canvas.skin_cache.get("key") != cache_key:
            canvas.skin_cache.clear()
            canvas.skin_cache["key"] = cache_key
            
            plate_w = int(total_width + 30 * scale)
            plate_h = int(90 * scale)
            lever_w = int(LEVER_WIDTH_DEFAULT * scale)
            lever_h = int(LEVER_HEIGHT_DEFAULT * scale)

            try:
                if os.path.exists(face_path):
                    pil_face = Image.open(face_path).convert("RGBA")
                    pil_face_resized = pil_face.resize((plate_w, plate_h), Image.Resampling.LANCZOS)
                    canvas.skin_cache["face"] = ImageTk.PhotoImage(pil_face_resized)
                else:
                    canvas.skin_cache["face"] = None

                if os.path.exists(lever_off_path):
                    pil_lo = Image.open(lever_off_path).convert("RGBA")
                    pil_lo_resized = pil_lo.resize((lever_w, lever_h), Image.Resampling.LANCZOS)
                    canvas.skin_cache["lever_off"] = ImageTk.PhotoImage(pil_lo_resized)
                else:
                    canvas.skin_cache["lever_off"] = None

                if os.path.exists(lever_on_path):
                    pil_lon = Image.open(lever_on_path).convert("RGBA")
                    pil_lon_resized = pil_lon.resize((lever_w, lever_h), Image.Resampling.LANCZOS)
                    canvas.skin_cache["lever_on"] = ImageTk.PhotoImage(pil_lon_resized)
                else:
                    canvas.skin_cache["lever_on"] = None
            except Exception as ex:
                print(f"[警告] スキン画像スキャン失敗: {ex}")
                canvas.skin_cache["face"] = None
                canvas.skin_cache["lever_off"] = None
                canvas.skin_cache["lever_on"] = None

    static_state_key = (
        canvas_bg_color, inst_type, lang_seg_value,
        is_hole_num_on, is_legend_on, is_grid_on,
        color_blow_hex, color_draw_hex,
        use_skin, round(scale, 4), aspect_ratio,
        trajectory_mode, show_grid4
    )

    # 1. 静的部分および常駐キャッシュオブジェクトの初期構築（設定変更時・初回のみ実行）
    if draw_mode == "all" or getattr(canvas, "_static_state_key", None) != static_state_key or not canvas.find_withtag("static_plate"):
        canvas._static_state_key = static_state_key
        canvas.delete("all")
        
        if hasattr(canvas, "note_pool"):
            canvas.note_pool.clear()
        else:
            canvas.note_pool = {}

        if hasattr(canvas, "measure_pool"):
            canvas.measure_pool.clear()
        else:
            canvas.measure_pool = {}

        canvas._led_state_cache = {}
        canvas._grid4_hole_cache = {}
        canvas._body_text_state_cache = {}
        canvas._lever_state_cache = None
        canvas._edit_panel_state_cache = None
            
        canvas.configure(bg=canvas_bg_color)
        
        # [レイヤー1] ガイド線・グリッド
        if is_grid_on:
            guide_color = "#002200" if canvas_bg_color == "#00FF00" else "#1c1c1c"
            if is_straight_mode:
                for k in range(N_visible):
                    hx = X_start_draw + k * W_PITCH * scale
                    for sub in (1, 2, 3):
                        sx = hx + sub * 12 * scale
                        canvas.create_line(sx, 0, sx, y_hole_line_s, fill=guide_color, tags="static_grid")
                    canvas.create_line(hx, 0, hx, y_hole_line_s, fill=grid_line_color, tags="static_grid_border")
                canvas.create_line(X_start_draw + total_width, 0, X_start_draw + total_width, y_hole_line_s, fill=grid_line_color, tags="static_grid_border")
            else:
                for idx in range(58):
                    x_pos = (24 + idx * 16) * scale
                    canvas.create_line(x_pos, 0, x_pos, y_collide_s, fill=guide_color, tags="static_grid")

                canvas.create_line(24 * scale, 0, 24 * scale, y_collide_s, fill=grid_line_color, tags="static_grid_border")
                canvas.create_line(936 * scale, 0, 936 * scale, y_collide_s, fill=grid_line_color, tags="static_grid_border")

                if height_straight_s > 0:
                    canvas.create_line(X_start_draw, y_straight_s, X_start_draw + total_width, y_straight_s, fill=guide_color, tags="static_grid")
                    for k in range(N_visible):
                        hx = X_start_draw + k * W_PITCH * scale
                        for sub in (1, 2, 3):
                            sx = hx + sub * 12 * scale
                            canvas.create_line(sx, y_straight_s, sx, y_hole_line_s, fill=guide_color, tags="static_grid")
                        canvas.create_line(hx, y_straight_s, hx, y_hole_line_s, fill=grid_line_color, tags="static_grid_border")
                    canvas.create_line(X_start_draw + total_width, y_straight_s, X_start_draw + total_width, y_hole_line_s, fill=grid_line_color, tags="static_grid_border")

        # [レイヤー1.5] 落下する小節横線・小節番号のアンカー（背景グリッドの直上、ノーツやプレートの背面）
        canvas.create_line(0, 0, 0, 0, state="hidden", tags="anchor_measure_lines_top")

        # [レイヤー2] スライドレバー（プレートの背面に常駐させ、ON/OFF変化時のみ差し替え）
        lever_x = X_start_draw + total_width
        canvas.lever_skin_id = None
        canvas.lever_shaft_id = None
        canvas.lever_knob_id = None
        if use_skin and hasattr(canvas, "skin_cache") and canvas.skin_cache.get("lever_off") and canvas.skin_cache.get("lever_on"):
            canvas.lever_skin_id = canvas.create_image(
                lever_x + 15 * scale, y_center_s,
                image=canvas.skin_cache["lever_off"],
                anchor="w",
                tags="dynamic_lever"
            )
        else:
            canvas.lever_shaft_id = canvas.create_rectangle(
                lever_x, y_center_s - 12 * scale,
                lever_x + 24 * scale, y_center_s + 12 * scale,
                fill="#555555", outline="#3d3d3d", tags="dynamic_lever"
            )
            canvas.lever_knob_id = canvas.create_oval(
                lever_x + 22 * scale, y_center_s - 18 * scale,
                lever_x + 38 * scale, y_center_s + 18 * scale,
                fill="#DCDCDC", outline="#4d4d4d", width=1, tags="dynamic_lever"
            )
        canvas._lever_state_cache = False

        # [レイヤー3] マウスピースプレート
        if use_skin and hasattr(canvas, "skin_cache") and canvas.skin_cache.get("face"):
            plate_center_x = X_start_draw + total_width / 2
            canvas.create_image(
                plate_center_x, y_center_s,
                image=canvas.skin_cache["face"],
                tags="static_plate"
            )
        else:
            canvas.create_rectangle(
                X_start_draw - 15 * scale, y_center_s - 45 * scale, X_start_draw + total_width + 15 * scale, y_center_s + 45 * scale,
                fill="#26282a", outline="#4d4d4d", width=max(1, int(2 * scale)), tags="static_plate"
            )

        # [レイヤー4〜6] 穴・LED・連動レバーリングの常駐オブジェクト構築
        canvas.led_objects = []
        canvas.ring_objects = []
        canvas.text_shadow_objects = []  
        canvas.text_body_objects = []    
        canvas.grid4_objects = []

        ring_r = 21 * scale
        for k, idx in enumerate(visible_indices):
            x_center = X_start_draw + k * W_PITCH * scale + (W_PITCH * scale / 2)
            
            canvas.create_oval(
                x_center - (D_HOLE * scale / 2), y_center_s - (D_HOLE * scale / 2),
                x_center + (D_HOLE * scale / 2), y_center_s + (D_HOLE * scale / 2),
                fill="#080808", outline="#4d4d4d", width=1, tags="static_hole"
            )
            
            led_id = canvas.create_oval(
                x_center - 15 * scale, y_center_s - 15 * scale, x_center + 15 * scale, y_center_s + 15 * scale,
                fill="#080808", outline="", width=0, tags="cached_led"
            )
            canvas.led_objects.append(led_id)

            ring_id = canvas.create_oval(
                x_center - ring_r, y_center_s - ring_r,
                x_center + ring_r, y_center_s + ring_r,
                outline=color_blow_hex, width=max(2, int(3 * scale)),
                state="hidden", tags="dynamic_lever_ring"
            )
            canvas.ring_objects.append(ring_id)

        # [レイヤー7〜8] 落下ノーツおよびノーツ音名ラベル用の重なり順アンカー（毎フレームのtag_raiseを不要にするO(1)アンカー）
        canvas.create_line(0, 0, 0, 0, state="hidden", tags="anchor_notes_top")
        canvas.create_line(0, 0, 0, 0, state="hidden", tags="anchor_labels_top")

        # [レイヤー9] 穴の下側表示（4音グリッド / 1音表示）の常駐オブジェクト構築（文字も初回にセット）
        cell_order = [
            ("吹", "OFF", 0, 0),  # 左上: 吹き（スライドなし）
            ("吸", "OFF", 0, 1),  # 右上: 吸い（スライドなし）
            ("吹", "ON", 1, 0),   # 左下: スライド有りの吹き
            ("吸", "ON", 1, 1),   # 右下: スライド有りの吸い
        ]
        grid_top = y_center_s + 47 * scale
        cell_w = 23 * scale
        cell_h = 15 * scale
        f_grid_size = max(5, int(7 * scale))
        default_text_color = "#000000" if canvas_bg_color == "#00FF00" else "#AAAAAA"

        for k, idx in enumerate(visible_indices):
            x_center = X_start_draw + k * W_PITCH * scale + (W_PITCH * scale / 2)
            visible_hole_number_absolute = idx + 1
            default_note_text = get_note_name(_BLOW_NOTES_MIDI[mode_key][k], is_japanese=is_jp)

            hole_cells = {}
            if show_grid4:
                hole_4_map = get_hole_4_notes(visible_hole_number_absolute, inst_type)
                grid_left = x_center - cell_w
                for act, lev, r_idx, c_idx in cell_order:
                    cx0 = grid_left + c_idx * cell_w
                    cy0 = grid_top + r_idx * cell_h
                    cx1 = cx0 + cell_w
                    cy1 = cy0 + cell_h
                    cell_midi = hole_4_map.get((act, lev))
                    cell_text = get_note_name(cell_midi, is_japanese=is_jp) if (cell_midi is not None and lang_seg_value != "なし") else ""
                    c_rect = canvas.create_rectangle(
                        cx0, cy0, cx1, cy1,
                        fill="#181818" if r_idx == 0 else "#101010",
                        outline="#383838" if r_idx == 0 else "#2c2c2c",
                        width=1, tags="cached_grid4"
                    )
                    c_txt = canvas.create_text(
                        (cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0,
                        text=cell_text, fill="#CCCCCC" if r_idx == 0 else "#888888",
                        font=("Meiryo UI", f_grid_size, "bold"), tags="cached_grid4"
                    )
                    hole_cells[(act, lev)] = (c_rect, c_txt, r_idx)
                canvas._grid4_hole_cache[k] = frozenset()
            canvas.grid4_objects.append(hole_cells)

            shadow_ids = []
            border_width = max(1.0, 1.5 * scale)
            f_size = max(6, int(11 * scale))
            init_1note_txt = "" if (show_grid4 or lang_seg_value == "なし") else default_note_text
            for dx, dy in [(-border_width, -border_width), (border_width, border_width)]:
                s_id = canvas.create_text(
                    x_center + dx, y_center_s + 60 * scale + dy, text=init_1note_txt, fill="#000000",
                    font=("Arial", f_size, "bold"), tags="cached_shadow"
                )
                shadow_ids.append(s_id)
            canvas.text_shadow_objects.append(shadow_ids)
            
            b_id = canvas.create_text(
                x_center, y_center_s + 60 * scale, text=init_1note_txt, fill=default_text_color,
                font=("Arial", f_size, "bold"), tags="cached_body"
            )
            canvas.text_body_objects.append(b_id)
            canvas._body_text_state_cache[k] = (False, None)

        # [レイヤー10] 穴番号
        if is_hole_num_on:
            f_num_size = max(6, int(11 * scale))
            for k, idx in enumerate(visible_indices):
                x_center = X_start_draw + k * W_PITCH * scale + (W_PITCH * scale / 2)
                hole_number = k + 1
                draw_bordered_text_canvas(canvas, (x_center, y_center_s + 24 * scale), str(hole_number), "#FFFFFF", font=("Arial", f_num_size, "bold"), border_width=int(2*scale), tags="static_text")

        # [レイヤー11] 凡例
        if is_legend_on:
            legend_x_start = 770 * scale
            canvas.create_rectangle(legend_x_start, 30 * scale, legend_x_start + 140 * scale, 75 * scale, fill="#1c1c1c", outline="#000000", width=max(1, int(2*scale)), tags="static_legend")
            canvas.create_oval(legend_x_start + 12 * scale, 40 * scale, legend_x_start + 22 * scale, 50 * scale, fill=note_color_blow, outline="", tags="static_legend")
            draw_bordered_text_canvas(canvas, (legend_x_start + 70 * scale, 45 * scale), "吹", "#FFFFFF", border_width=int(2*scale), tags="static_legend")
            canvas.create_oval(legend_x_start + 12 * scale, 55 * scale, legend_x_start + 22 * scale, 65 * scale, fill=note_color_draw, outline="", tags="static_legend")
            draw_bordered_text_canvas(canvas, (legend_x_start + 70 * scale, 60 * scale), "吸", "#FFFFFF", border_width=int(2*scale), tags="static_legend")

    # 2. 二分探索による高速アクティブ範囲特定
    start_ticks, max_dur_ticks = _get_notes_index(midi_notes)
    search_start_idx = bisect.bisect_left(start_ticks, target_tick - max_dur_ticks) if start_ticks else 0

    lever_pressed = False
    playing_holes_data = {}
    playing_hole_cells_by_hole = {}
    playing_holes_note = {}
    
    if midi_notes and active_pitches:
        n_total = len(midi_notes)
        for i in range(search_start_idx, n_total):
            note_data = midi_notes[i]
            n_start = note_data.get("start_tick", 0)
            if n_start > target_tick:
                break
            n_dur = note_data.get("duration_ticks", 0)
            if note_data["note"] in active_pitches and n_start <= target_tick < (n_start + n_dur):
                fingering = note_data.get("fingering")
                if fingering:
                    h_num = fingering["hole"]
                    act = fingering["action"]
                    lev = fingering["lever"]
                    playing_holes_data[h_num] = act
                    if h_num not in playing_hole_cells_by_hole:
                        playing_hole_cells_by_hole[h_num] = set()
                    playing_hole_cells_by_hole[h_num].add((act, lev))
                    if h_num not in playing_holes_note:
                        playing_holes_note[h_num] = note_data["note"]
                    if lev == "ON":
                        lever_pressed = True

    # 3. スライドレバーの差分更新（ON/OFFが切り替わったフレームのみ通信）
    if getattr(canvas, "_lever_state_cache", None) != lever_pressed:
        canvas._lever_state_cache = lever_pressed
        lever_x = X_start_draw + total_width
        if getattr(canvas, "lever_skin_id", None) is not None:
            lever_img_tk = canvas.skin_cache["lever_on"] if lever_pressed else canvas.skin_cache["lever_off"]
            canvas.itemconfig(canvas.lever_skin_id, image=lever_img_tk)
        elif getattr(canvas, "lever_shaft_id", None) is not None and getattr(canvas, "lever_knob_id", None) is not None:
            if lever_pressed:
                canvas.coords(canvas.lever_shaft_id, lever_x, y_center_s - 12 * scale, lever_x + 6 * scale, y_center_s + 12 * scale)
                canvas.itemconfig(canvas.lever_shaft_id, fill="#3a3a3a")
                canvas.coords(canvas.lever_knob_id, lever_x + 3 * scale, y_center_s - 18 * scale, lever_x + 19 * scale, y_center_s + 18 * scale)
                canvas.itemconfig(canvas.lever_knob_id, fill="#A9A9A9")
            else:
                canvas.coords(canvas.lever_shaft_id, lever_x, y_center_s - 12 * scale, lever_x + 24 * scale, y_center_s + 12 * scale)
                canvas.itemconfig(canvas.lever_shaft_id, fill="#555555")
                canvas.coords(canvas.lever_knob_id, lever_x + 22 * scale, y_center_s - 18 * scale, lever_x + 38 * scale, y_center_s + 18 * scale)
                canvas.itemconfig(canvas.lever_knob_id, fill="#DCDCDC")

    # 4. 各穴のLED・連動リング・4音グリッド/1音表示の差分更新（状態が変わった穴だけ通信）
    for k, idx in enumerate(visible_indices):
        visible_hole_number_absolute = idx + 1
        action = playing_holes_data.get(visible_hole_number_absolute)
        is_led_active = (action is not None)
        ring_visible = bool(is_led_active and use_ring and lever_pressed)

        # LED・連動リング差分判定
        new_led_state = (action, ring_visible)
        if canvas._led_state_cache.get(k) != new_led_state:
            canvas._led_state_cache[k] = new_led_state
            if is_led_active:
                led_color = color_blow_hex if action == "吹" else color_draw_hex
                canvas.itemconfig(canvas.led_objects[k], fill=led_color)
                if ring_visible:
                    canvas.itemconfig(canvas.ring_objects[k], state="normal", outline=led_color)
                else:
                    canvas.itemconfig(canvas.ring_objects[k], state="hidden")
            else:
                canvas.itemconfig(canvas.led_objects[k], fill="#080808")
                canvas.itemconfig(canvas.ring_objects[k], state="hidden")

        # 穴下表示（4音グリッド or 1音表示）の差分判定
        if show_grid4:
            active_cells_set = frozenset(playing_hole_cells_by_hole.get(visible_hole_number_absolute, ()))
            if canvas._grid4_hole_cache.get(k) != active_cells_set:
                canvas._grid4_hole_cache[k] = active_cells_set
                for (act, lev), (c_rect, c_txt, r_idx) in canvas.grid4_objects[k].items():
                    if (act, lev) in active_cells_set:
                        c_fill = color_blow_hex if act == "吹" else color_draw_hex
                        canvas.itemconfig(c_rect, fill=c_fill, outline="#FFFFFF")
                        canvas.itemconfig(c_txt, fill="#000000")
                    else:
                        c_fill = "#181818" if r_idx == 0 else "#101010"
                        c_out = "#383838" if r_idx == 0 else "#2c2c2c"
                        t_fill = "#CCCCCC" if r_idx == 0 else "#888888"
                        canvas.itemconfig(c_rect, fill=c_fill, outline=c_out)
                        canvas.itemconfig(c_txt, fill=t_fill)
        else:
            cur_note = playing_holes_note.get(visible_hole_number_absolute) if is_led_active else None
            new_body_state = (is_led_active, cur_note)
            if canvas._body_text_state_cache.get(k) != new_body_state:
                canvas._body_text_state_cache[k] = new_body_state
                default_note_text = get_note_name(_BLOW_NOTES_MIDI[mode_key][k], is_japanese=is_jp)
                if is_led_active:
                    note_text = get_note_name(cur_note, is_japanese=is_jp) if cur_note is not None else default_note_text
                    if lang_seg_value == "なし":
                        note_text = ""
                    for s_id in canvas.text_shadow_objects[k]:
                        canvas.itemconfig(s_id, text=note_text)
                    canvas.itemconfig(canvas.text_body_objects[k], text=note_text, fill="#FFFFFF")
                else:
                    default_text_color = "#000000" if canvas_bg_color == "#00FF00" else "#AAAAAA"
                    display_text = default_note_text if lang_seg_value != "なし" else ""
                    for s_id in canvas.text_shadow_objects[k]:
                        canvas.itemconfig(s_id, text=display_text)
                    canvas.itemconfig(canvas.text_body_objects[k], text=display_text, fill=default_text_color)

    # 5. 小節横線（＋小節番号）および落下ノーツ＆追従音名ラベルの描画更新
    if draw_mode in ["all", "notes"]:
        px_per_tick = 120.0 / ticks_per_beat
        px_per_tick_s = px_per_tick * scale

        # 5-A. 小節ごとの薄い横線＋左端小節番号の落下更新（ガイド線ON時）
        if not hasattr(canvas, "measure_pool"):
            canvas.measure_pool = {}
        if is_grid_on and measures_timeline and px_per_tick_s > 0:
            visible_measures = set()
            m_line_color = "#003300" if canvas_bg_color == "#00FF00" else "#2e2e2e"
            m_txt_color = "#005500" if canvas_bg_color == "#00FF00" else "#555555"
            f_m_size = max(6, int(8 * scale))
            upper_left = 24.0 * scale
            upper_right = 936.0 * scale
            lower_left = X_start_draw
            lower_right = X_start_draw + total_width

            for m in measures_timeline:
                m_tick = m["start_tick"]
                y_m = y_hole_line_s - (m_tick - target_tick) * px_per_tick_s
                if y_m < 0.0:
                    break
                if y_m <= y_hole_line_s:
                    m_num = m["measure_num"]
                    visible_measures.add(m_num)
                    if is_straight_mode or y_m >= y_straight_s or height_diag_s <= 0:
                        x_l, x_r = lower_left, lower_right
                    elif y_m <= y_collide_s:
                        x_l, x_r = upper_left, upper_right
                    else:
                        ratio_m = (y_m - y_collide_s) / height_diag_s
                        x_l = upper_left + (lower_left - upper_left) * ratio_m
                        x_r = upper_right + (lower_right - upper_right) * ratio_m

                    m_item = canvas.measure_pool.get(m_num)
                    if m_item is None:
                        lid = canvas.create_line(
                            x_l, y_m, x_r, y_m,
                            fill=m_line_color, width=1, tags="measure_line"
                        )
                        tid = canvas.create_text(
                            x_l + 4 * scale, y_m - 2 * scale,
                            text=str(m_num), fill=m_txt_color, anchor="sw",
                            font=("Arial", f_m_size, "bold"), tags="measure_line"
                        )
                        canvas.tag_lower(lid, "anchor_measure_lines_top")
                        canvas.tag_lower(tid, "anchor_measure_lines_top")
                        canvas.measure_pool[m_num] = (lid, tid)
                    else:
                        lid, tid = m_item
                        canvas.coords(lid, x_l, y_m, x_r, y_m)
                        canvas.coords(tid, x_l + 4 * scale, y_m - 2 * scale)

            if len(canvas.measure_pool) > len(visible_measures):
                for old_m in list(canvas.measure_pool.keys()):
                    if old_m not in visible_measures:
                        lid, tid = canvas.measure_pool.pop(old_m)
                        canvas.delete(lid)
                        canvas.delete(tid)
        elif canvas.measure_pool:
            for lid, tid in canvas.measure_pool.values():
                canvas.delete(lid)
                canvas.delete(tid)
            canvas.measure_pool.clear()

        # 5-B. 落下ノーツ＆追従音名ラベルの描画更新
        if is_notes_on and midi_notes:
            max_visible_tick = target_tick + (y_hole_line_s / px_per_tick_s) + 10.0 if px_per_tick_s > 0 else target_tick + 10000

            visible_keys = set()
            f_lbl_size = max(6, int(8.5 * scale))
            lbl_bw = max(1.0, 1.5 * scale)
            n_total = len(midi_notes)
            
            for i in range(search_start_idx, n_total):
                note_data = midi_notes[i]
                note_start = note_data["start_tick"]
                if note_start > max_visible_tick:
                    break
                note_dur = note_data["duration_ticks"]
                note_end = note_start + note_dur
                note_val = note_data["note"]
                
                y_bottom = y_hole_line_s - (note_start - target_tick) * px_per_tick_s
                y_top = y_hole_line_s - (note_end - target_tick) * px_per_tick_s
                
                if y_bottom >= 0 and y_top <= y_hole_line_s:
                    fing = note_data.get("fingering") 
                    if not fing: 
                        continue
                    
                    key = (note_start, note_val)
                    visible_keys.add(key)
                    
                    bound_ok = (note_data.get("_bound_inst") == inst_type)
                    is_editable = note_data["is_editable"] if bound_ok else is_note_editable(note_val, inst_type)
                    
                    if edit_mode_active and is_editable:
                        col_hex = "#FF0000" 
                        edit_tag = f"note_edit_{note_start}_{note_val}"
                    else:
                        col_hex = note_color_blow if fing["action"] == "吹" else note_color_draw
                        edit_tag = "" 
                    
                    simulated_note = note_val + 36 if "バス" in inst_type else note_val
                    lane_idx = simulated_note - 48
                    lane_x_left = (72 + lane_idx * 16) * scale - X_shift_notes
                    lane_x_right = lane_x_left + 16 * scale
                    
                    note_in_range = note_data["in_range"] if bound_ok else is_note_in_range(note_val, inst_type)
                    dest_x_center = (note_data["dest_x_base"] * scale) if bound_ok else get_note_dest_x(note_val, inst_type, scale=scale, start_tick=note_start)
                    dest_left = dest_x_center - 6 * scale
                    dest_right = dest_x_center + 6 * scale

                    lbl_str = (note_data["name_jp"] if is_jp else note_data["name_cde"]) if bound_ok else get_note_name(note_val, is_japanese=is_jp)
                    style_key = (col_hex, edit_tag, lbl_str, f_lbl_size)
                    
                    pool_item = canvas.note_pool.get(key)
                    if pool_item is None:
                        pool_item = {
                            "rect_id": None, "poly_id": None, "lower_rect_id": None,
                            "lbl_s1_id": None, "lbl_s2_id": None, "lbl_txt_id": None,
                            "style_key": style_key
                        }
                        canvas.note_pool[key] = pool_item
                        style_changed = False
                    else:
                        style_changed = (pool_item.get("style_key") != style_key)
                        if style_changed:
                            pool_item["style_key"] = style_key
                    
                    tag_tuple = ("note", edit_tag) if edit_tag else ("note",)

                    if is_straight_mode:
                        if pool_item["rect_id"] is not None:
                            canvas.delete(pool_item["rect_id"])
                            pool_item["rect_id"] = None
                        if pool_item["poly_id"] is not None:
                            canvas.delete(pool_item["poly_id"])
                            pool_item["poly_id"] = None

                        if note_in_range:
                            s_top = max(0.0, y_top)
                            s_bottom = min(y_hole_line_s, y_bottom)
                            if s_bottom > s_top:
                                if pool_item["lower_rect_id"] is None:
                                    cid = canvas.create_rectangle(
                                        dest_left, s_top, dest_right, s_bottom,
                                        fill=col_hex, outline="", tags=tag_tuple
                                    )
                                    canvas.tag_lower(cid, "anchor_notes_top")
                                    pool_item["lower_rect_id"] = cid
                                else:
                                    canvas.coords(pool_item["lower_rect_id"], dest_left, s_top, dest_right, s_bottom)
                                    if style_changed:
                                        canvas.itemconfig(pool_item["lower_rect_id"], fill=col_hex, tags=tag_tuple)
                            else:
                                if pool_item["lower_rect_id"] is not None:
                                    canvas.delete(pool_item["lower_rect_id"])
                                    pool_item["lower_rect_id"] = None
                    else:
                        # [第1段階] 上部60音等幅垂直レーン (0 <= y <= y_collide_s)
                        v_top = max(0.0, y_top)
                        v_bottom = min(y_collide_s, y_bottom)
                        if v_bottom > v_top:
                            if pool_item["rect_id"] is None:
                                cid = canvas.create_rectangle(
                                    lane_x_left, v_top, lane_x_right, v_bottom,
                                    fill=col_hex, outline="", tags=tag_tuple
                                )
                                canvas.tag_lower(cid, "anchor_notes_top")
                                pool_item["rect_id"] = cid
                            else:
                                canvas.coords(pool_item["rect_id"], lane_x_left, v_top, lane_x_right, v_bottom)
                                if style_changed:
                                    canvas.itemconfig(pool_item["rect_id"], fill=col_hex, tags=tag_tuple)
                        else:
                            if pool_item["rect_id"] is not None:
                                canvas.delete(pool_item["rect_id"])
                                pool_item["rect_id"] = None

                        # [第2段階] 斜め収束区間 (y_collide_s <= y <= y_straight_s)
                        if note_in_range and y_bottom > y_collide_s and y_top < y_straight_s:
                            t_top = max(y_collide_s, y_top)
                            t_bottom = min(y_straight_s, y_bottom)
                            
                            if t_bottom > t_top:
                                ratio_top = (t_top - y_collide_s) / height_diag_s if t_top > y_collide_s else 0.0
                                ratio_bottom = (t_bottom - y_collide_s) / height_diag_s
                                
                                x_top_left = lane_x_left + (dest_left - lane_x_left) * ratio_top
                                x_top_right = lane_x_right + (dest_right - lane_x_right) * ratio_top
                                x_bottom_left = lane_x_left + (dest_left - lane_x_left) * ratio_bottom
                                x_bottom_right = lane_x_right + (dest_right - lane_x_right) * ratio_bottom
                                
                                if pool_item["poly_id"] is None:
                                    cid = canvas.create_polygon(
                                        x_top_left, t_top, x_top_right, t_top,
                                        x_bottom_right, t_bottom, x_bottom_left, t_bottom,
                                        fill=col_hex, outline="", tags=tag_tuple
                                    )
                                    canvas.tag_lower(cid, "anchor_notes_top")
                                    pool_item["poly_id"] = cid
                                else:
                                    canvas.coords(
                                        pool_item["poly_id"],
                                        x_top_left, t_top, x_top_right, t_top,
                                        x_bottom_right, t_bottom, x_bottom_left, t_bottom
                                    )
                                    if style_changed:
                                        canvas.itemconfig(pool_item["poly_id"], fill=col_hex, tags=tag_tuple)
                            else:
                                if pool_item["poly_id"] is not None:
                                    canvas.delete(pool_item["poly_id"])
                                    pool_item["poly_id"] = None
                        else:
                            if pool_item["poly_id"] is not None:
                                canvas.delete(pool_item["poly_id"])
                                pool_item["poly_id"] = None

                        # [第3段階] 穴直上の垂直落下区間 (y_straight_s <= y <= y_hole_line_s)
                        if note_in_range and y_bottom > y_straight_s:
                            s_top = max(y_straight_s, y_top)
                            s_bottom = min(y_hole_line_s, y_bottom)
                            if s_bottom > s_top:
                                if pool_item["lower_rect_id"] is None:
                                    cid = canvas.create_rectangle(
                                        dest_left, s_top, dest_right, s_bottom,
                                        fill=col_hex, outline="", tags=tag_tuple
                                    )
                                    canvas.tag_lower(cid, "anchor_notes_top")
                                    pool_item["lower_rect_id"] = cid
                                else:
                                    canvas.coords(pool_item["lower_rect_id"], dest_left, s_top, dest_right, s_bottom)
                                    if style_changed:
                                        canvas.itemconfig(pool_item["lower_rect_id"], fill=col_hex, tags=tag_tuple)
                            else:
                                if pool_item["lower_rect_id"] is not None:
                                    canvas.delete(pool_item["lower_rect_id"])
                                    pool_item["lower_rect_id"] = None
                        else:
                            if pool_item["lower_rect_id"] is not None:
                                canvas.delete(pool_item["lower_rect_id"])
                                pool_item["lower_rect_id"] = None

                    # 落下ノーツ追従音名ラベル（生成時のみ属性設定、落下中はcoords移動のみ）
                    y_limit_bot = y_hole_line_s if note_in_range else y_collide_s
                    y_vis_top = max(0.0, y_top)
                    y_vis_bot = min(y_limit_bot, y_bottom)
                    show_note_label = bool(
                        show_lookahead and lang_seg_value != "なし"
                        and (not is_straight_mode or note_in_range)
                        and (y_vis_bot - y_vis_top >= 6.0 * scale)
                        and y_vis_bot >= 8.0 * scale
                    )
                    if show_note_label:
                        label_y = y_vis_bot - 8.5 * scale if (y_vis_bot - y_vis_top >= 17.0 * scale) else (y_vis_top + y_vis_bot) / 2.0
                        lane_cx = (lane_x_left + lane_x_right) / 2.0
                        if is_straight_mode or label_y >= y_straight_s:
                            label_x = dest_x_center
                        elif label_y <= y_collide_s or not note_in_range:
                            label_x = lane_cx
                        else:
                            ratio_lbl = (label_y - y_collide_s) / height_diag_s if height_diag_s > 0 else 1.0
                            label_x = lane_cx + (dest_x_center - lane_cx) * ratio_lbl

                        lbl_tags = ("note_label", edit_tag) if edit_tag else ("note_label",)
                        if pool_item["lbl_s1_id"] is None:
                            s1 = canvas.create_text(
                                label_x - lbl_bw, label_y - lbl_bw, text=lbl_str, fill="#000000",
                                font=("Meiryo UI", f_lbl_size, "bold"), tags=lbl_tags
                            )
                            s2 = canvas.create_text(
                                label_x + lbl_bw, label_y + lbl_bw, text=lbl_str, fill="#000000",
                                font=("Meiryo UI", f_lbl_size, "bold"), tags=lbl_tags
                            )
                            txt = canvas.create_text(
                                label_x, label_y, text=lbl_str, fill="#FFFFFF",
                                font=("Meiryo UI", f_lbl_size, "bold"), tags=lbl_tags
                            )
                            canvas.tag_lower(s1, "anchor_labels_top")
                            canvas.tag_lower(s2, "anchor_labels_top")
                            canvas.tag_lower(txt, "anchor_labels_top")
                            pool_item["lbl_s1_id"] = s1
                            pool_item["lbl_s2_id"] = s2
                            pool_item["lbl_txt_id"] = txt
                        else:
                            canvas.coords(pool_item["lbl_s1_id"], label_x - lbl_bw, label_y - lbl_bw)
                            canvas.coords(pool_item["lbl_s2_id"], label_x + lbl_bw, label_y + lbl_bw)
                            canvas.coords(pool_item["lbl_txt_id"], label_x, label_y)
                            if style_changed:
                                canvas.itemconfig(pool_item["lbl_s1_id"], text=lbl_str, tags=lbl_tags)
                                canvas.itemconfig(pool_item["lbl_s2_id"], text=lbl_str, tags=lbl_tags)
                                canvas.itemconfig(pool_item["lbl_txt_id"], text=lbl_str, tags=lbl_tags)
                    else:
                        for lk in ("lbl_s1_id", "lbl_s2_id", "lbl_txt_id"):
                            if pool_item[lk] is not None:
                                canvas.delete(pool_item[lk])
                                pool_item[lk] = None
            
            if len(canvas.note_pool) > len(visible_keys):
                for old_key in list(canvas.note_pool.keys()):
                    if old_key not in visible_keys:
                        pool_item = canvas.note_pool.pop(old_key)
                        for k_id, cid in pool_item.items():
                            if k_id != "style_key" and cid is not None:
                                canvas.delete(cid)
        else:
            if canvas.note_pool:
                for pool_item in canvas.note_pool.values():
                    for k_id, cid in pool_item.items():
                        if k_id != "style_key" and cid is not None:
                            canvas.delete(cid)
                canvas.note_pool.clear()

    # 6. 運指変更モード表示枠の差分更新（状態変化時のみ再描画）
    edit_panel_state = (edit_mode_active, last_edit_note, last_edit_fing, round(scale, 4))
    if getattr(canvas, "_edit_panel_state_cache", None) != edit_panel_state:
        canvas._edit_panel_state_cache = edit_panel_state
        canvas.delete("edit_status_panel")
        if edit_mode_active:
            panel_x = 770 * scale
            panel_y = 85 * scale
            canvas.create_rectangle(
                panel_x, panel_y, panel_x + 140 * scale, panel_y + 65 * scale, 
                fill="#1c1c1c", outline="#ff3333", width=max(1.0, 1.5 * scale), tags="edit_status_panel"
            )
            canvas.create_text(
                panel_x + 70 * scale, panel_y + 12 * scale, 
                text="【編集中の運指】", 
                fill="#ff3333", font=("Arial", max(6, int(9 * scale)), "bold"), tags="edit_status_panel"
            )
            if last_edit_note and last_edit_fing:
                canvas.create_text(
                    panel_x + 70 * scale, panel_y + 30 * scale, 
                    text=last_edit_note, 
                    fill="#ffffff", font=("Arial", max(6, int(11 * scale)), "bold"), tags="edit_status_panel"
                )
                canvas.create_text(
                    panel_x + 70 * scale, panel_y + 48 * scale, 
                    text=last_edit_fing, 
                    fill="#ffcc00", font=("Arial", max(6, int(11 * scale)), "bold"), tags="edit_status_panel"
                )
            else:
                canvas.create_text(
                    panel_x + 70 * scale, panel_y + 32 * scale, 
                    text="ノーツを選択...", 
                    fill="#888888", font=("Arial", max(6, int(10 * scale))), tags="edit_status_panel"
                )
            if canvas.find_withtag("static_legend"):
                canvas.tag_lower("edit_status_panel", "static_legend")