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
    get_note_fingering_for_song, is_note_editable
)

_CACHE = {
    "key": None,          
    "base_image": None,   
}



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
                          use_ring=True, trajectory_mode="3段階収束 (標準)"):  
    """
    Pillowを一切経由せず、Tkinter Canvasのネイティブ命令だけで超高速描画。
    縮小フィットスケール scale および アスペクト比に応じたY軸平行移動を完全加算して描画。
    """
    if active_pitches is None: active_pitches = set()
    if midi_notes is None: midi_notes = []

    # マルチアスペクト仮想フル高さ解決
    canvas_height_full = get_canvas_height_by_ratio(aspect_ratio)
    
    # フル高さに応じた下部基準Y座標を解決（3段階収束＆垂直落下対応）
    y_center_full, y_collide_full, y_straight_full, y_hole_line_full, height_diag_full, _ = get_y_trajectory_params(canvas_height_full)

    # スケールを掛け合わせて、表示用Canvas内にパーフェクトにフィット縮小！
    y_center_s = y_center_full * scale
    y_collide_s = y_collide_full * scale
    y_straight_s = y_straight_full * scale
    y_hole_line_s = y_hole_line_full * scale
    height_diag_s = height_diag_full * scale
    is_straight_mode = ("垂直落下" in str(trajectory_mode))

    visible_indices, X_start_draw, X_shift, X_shift_notes = get_layout_params(inst_type, scale)
    N_visible = len(visible_indices)
    total_width = N_visible * W_PITCH * scale
    
    grid_line_color = "#000000" if canvas_bg_color == "#00FF00" else "#252525"
    
    note_color_blow = color_blow_hex
    note_color_draw = color_draw_hex

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

    # 1. 静的部分の描画
    if draw_mode == "all" or not canvas.find_withtag("static_plate"):
        canvas.delete("all")
        
        if hasattr(canvas, "note_pool"):
            canvas.note_pool.clear()
            
        canvas.configure(bg=canvas_bg_color)
        
        if is_grid_on:
            guide_color = "#002200" if canvas_bg_color == "#00FF00" else "#1c1c1c"
            if is_straight_mode:
                # 垂直落下モード：画面上端から穴上端まで各穴カラム境界＋穴内4分割ガイド線を描画
                for k in range(N_visible):
                    hx = X_start_draw + k * W_PITCH * scale
                    for sub in (1, 2, 3):
                        sx = hx + sub * 12 * scale
                        canvas.create_line(sx, 0, sx, y_hole_line_s, fill=guide_color, tags="static_grid")
                    canvas.create_line(hx, 0, hx, y_hole_line_s, fill=grid_line_color, tags="static_grid_border")
                canvas.create_line(X_start_draw + total_width, 0, X_start_draw + total_width, y_hole_line_s, fill=grid_line_color, tags="static_grid_border")
            else:
                # 3段階収束モード：上部60音等幅グリッド + 穴直上の垂直助走区間ガイド線
                for idx in range(58):
                    x_pos = (24 + idx * 16) * scale
                    canvas.create_line(x_pos, 0, x_pos, y_collide_s, fill=guide_color, tags="static_grid")

                canvas.create_line(24 * scale, 0, 24 * scale, y_collide_s, fill=grid_line_color, tags="static_grid_border")
                canvas.create_line(936 * scale, 0, 936 * scale, y_collide_s, fill=grid_line_color, tags="static_grid_border")

                # 穴直上の垂直落下区間 (y_straight_s 〜 y_hole_line_s) の穴境界＋穴内4分割ガイド
                canvas.create_line(X_start_draw, y_straight_s, X_start_draw + total_width, y_straight_s, fill=guide_color, tags="static_grid")
                for k in range(N_visible):
                    hx = X_start_draw + k * W_PITCH * scale
                    for sub in (1, 2, 3):
                        sx = hx + sub * 12 * scale
                        canvas.create_line(sx, y_straight_s, sx, y_hole_line_s, fill=guide_color, tags="static_grid")
                    canvas.create_line(hx, y_straight_s, hx, y_hole_line_s, fill=grid_line_color, tags="static_grid_border")
                canvas.create_line(X_start_draw + total_width, y_straight_s, X_start_draw + total_width, y_hole_line_s, fill=grid_line_color, tags="static_grid_border")

        # マウスピース外部スキン貼り付け合成
        if use_skin and canvas.skin_cache.get("face"):
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

        canvas.led_objects = []
        canvas.text_shadow_objects = []  
        canvas.text_body_objects = []    
        
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

            # 音名表示の構築位置を、外側（下端 +60px）へスライド！
            shadow_ids = []
            border_width = max(1.0, 1.5 * scale)
            f_size = max(6, int(11 * scale))
            for dx, dy in [(-border_width, -border_width), (border_width, border_width)]:
                s_id = canvas.create_text(
                    x_center + dx, y_center_s + 60 * scale + dy, text="", fill="#000000",
                    font=("Arial", f_size, "bold"), tags="cached_shadow"
                )
                shadow_ids.append(s_id)
            canvas.text_shadow_objects.append(shadow_ids)
            
            b_id = canvas.create_text(
                x_center, y_center_s + 60 * scale, text="", fill="#AAAAAA",
                font=("Arial", f_size, "bold"), tags="cached_body"
            )
            canvas.text_body_objects.append(b_id)

        # 穴番号の構築位置を、穴の下の中間点（+24px）へ内寄せ再配置！
        if is_hole_num_on:
            f_num_size = max(6, int(11 * scale))
            for k, idx in enumerate(visible_indices):
                x_center = X_start_draw + k * W_PITCH * scale + (W_PITCH * scale / 2)
                hole_number = k + 1
                draw_bordered_text_canvas(canvas, (x_center, y_center_s + 24 * scale), str(hole_number), "#FFFFFF", font=("Arial", f_num_size, "bold"), border_width=int(2*scale), tags="static_text")

        if is_legend_on:
            legend_x_start = 770 * scale
            canvas.create_rectangle(legend_x_start, 30 * scale, legend_x_start + 140 * scale, 75 * scale, fill="#1c1c1c", outline="#000000", width=max(1, int(2*scale)), tags="static_legend")
            canvas.create_oval(legend_x_start + 12 * scale, 40 * scale, legend_x_start + 22 * scale, 50 * scale, fill=note_color_blow, outline="", tags="static_legend")
            draw_bordered_text_canvas(canvas, (legend_x_start + 70 * scale, 45 * scale), "吹", "#FFFFFF", border_width=int(2*scale), tags="static_legend")
            canvas.create_oval(legend_x_start + 12 * scale, 55 * scale, legend_x_start + 22 * scale, 65 * scale, fill=note_color_draw, outline="", tags="static_legend")
            draw_bordered_text_canvas(canvas, (legend_x_start + 70 * scale, 60 * scale), "吸", "#FFFFFF", border_width=int(2*scale), tags="static_legend")

    # 2. 動的部分の描画更新
    canvas.delete("dynamic_lever")
    canvas.delete("dynamic_led")
    canvas.delete("dynamic_text")
    canvas.delete("dynamic_lever_ring")  

    lever_pressed = False
    playing_holes_data = {}
    
    currently_active_notes = []
    if midi_notes and active_pitches:
        for note_data in midi_notes:
            n_start = note_data.get("start_tick", 0)
            n_dur = note_data.get("duration_ticks", 0)
            if note_data["note"] in active_pitches and n_start <= target_tick < (n_start + n_dur):
                currently_active_notes.append(note_data)
                
    for note_data in currently_active_notes:
        fingering = note_data.get("fingering") 
        if fingering:
            playing_holes_data[fingering["hole"]] = fingering["action"]
            if fingering["lever"] == "ON": 
                lever_pressed = True

    # ON/OFF切り替え時に横揺れ（平行移動）する計算を完全に廃止（移動オフセット常にゼロ）！
    lever_x_offset = 0
    # 軸の左端開始座標を「マウスピースプレートの真右端（隙間0）」にピタッと完全吸着させ、x1 >= x0 の逆転バグを物理的に完全根絶！
    lever_x = X_start_draw + total_width

    # スライドレバー外部スキン動的差し替え合成 (サイズアップ 48x48)
    if use_skin and canvas.skin_cache.get("lever_off") and canvas.skin_cache.get("lever_on"):
        lever_img_tk = canvas.skin_cache["lever_on"] if lever_pressed else canvas.skin_cache["lever_off"]
        # スキン画像ペースト時は、プレート右端から +15px（マージン）の位置で変わらず完全にピッタリ重ね合わされます。
        canvas.create_image(
            lever_x + 15 * scale, y_center_s,
            image=lever_img_tk,
            anchor="w",
            tags="dynamic_lever"
        )
    else:
        lever_fill = "#555555"
        if lever_pressed:
            canvas.create_rectangle(
                lever_x, y_center_s - 12 * scale,
                lever_x + 6 * scale, y_center_s + 12 * scale,
                fill="#3a3a3a", outline="#3d3d3d", tags="dynamic_lever"
            )
            canvas.create_oval(
                lever_x + 3 * scale, y_center_s - 18 * scale,
                lever_x + 19 * scale, y_center_s + 18 * scale,
                fill="#A9A9A9", outline="#4d4d4d", width=1, tags="dynamic_lever"
            )
        else:
            canvas.create_rectangle(
                lever_x, y_center_s - 12 * scale,
                lever_x + 24 * scale, y_center_s + 12 * scale,
                fill=lever_fill, outline="#3d3d3d", tags="dynamic_lever"
            )
            canvas.create_oval(
                lever_x + 22 * scale, y_center_s - 18 * scale,
                lever_x + 38 * scale, y_center_s + 18 * scale,
                fill="#DCDCDC", outline="#4d4d4d", width=1, tags="dynamic_lever"
            )

    for k, idx in enumerate(visible_indices):
        x_center = X_start_draw + k * W_PITCH * scale + (W_PITCH * scale / 2)
        
        blow_notes_midi = {
            "16穴": [48, 52, 55, 60, 60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96],
            "12穴 標準": [60, 64, 67, 72, 72, 76, 79, 84, 84, 88, 91, 96], 
            "12穴 バス": [24, 28, 31, 35, 36, 40, 43, 47, 48, 52, 55, 59]
        }
        mode_key = "16穴" if "16穴" in inst_type else ("12穴 標準" if "標準" in inst_type else "12穴 バス")
        default_note_text = get_note_name(blow_notes_midi[mode_key][k], is_japanese=("ドレミ" in lang_seg_value))
        
        # 点滅LED解決
        visible_hole_number_absolute = visible_indices[k] + 1
        is_led_active = visible_hole_number_absolute in playing_holes_data

        if is_led_active:
            action = playing_holes_data[visible_hole_number_absolute]
            led_color = color_blow_hex if action == "吹" else color_draw_hex
            canvas.itemconfig(canvas.led_objects[k], fill=led_color)
            
            # 吹吸アクション（吹＝オレンジ系、吸＝シアン系）のカスタムカラーを正確に継承した「連動レバーリング」
            if use_ring and lever_pressed:
                ring_r = 21 * scale
                canvas.create_oval(
                    x_center - ring_r, y_center_s - ring_r,
                    x_center + ring_r, y_center_s + ring_r,
                    outline=led_color, width=max(2, int(3 * scale)),
                    tags=("dynamic_lever_ring")
                )

            current_note = None
            for note_data in currently_active_notes:
                p = note_data["note"]
                fing = note_data.get("fingering") 
                if fing and fing["hole"] == visible_hole_number_absolute: 
                    current_note = p
                    break
            
            if current_note is not None:
                note_text = get_note_name(current_note, is_japanese=("ドレミ" in lang_seg_value))
            else:
                note_text = default_note_text
                
            if lang_seg_value == "なし":
                note_text = ""
                
            for s_id in canvas.text_shadow_objects[k]:
                canvas.itemconfig(s_id, text=note_text)
            canvas.itemconfig(canvas.text_body_objects[k], text=note_text, fill="#FFFFFF")
        else:
            canvas.itemconfig(canvas.led_objects[k], fill="#080808")
            
            default_text_color = "#000000" if canvas_bg_color == "#00FF00" else "#AAAAAA"
            display_text = default_note_text if lang_seg_value != "なし" else ""
            
            for s_id in canvas.text_shadow_objects[k]:
                canvas.itemconfig(s_id, text=display_text)
            canvas.itemconfig(canvas.text_body_objects[k], text=display_text, fill=default_text_color)

    if not hasattr(canvas, "note_pool"):
        canvas.note_pool = {}  

    if draw_mode in ["all", "notes"]:
        if is_notes_on and midi_notes:
            px_per_tick = 120.0 / ticks_per_beat
            visible_keys = set()
            
            for note_data in midi_notes:
                note_start = note_data["start_tick"]
                note_dur = note_data["duration_ticks"]
                note_end = note_start + note_dur
                note_val = note_data["note"]
                
                # 縮小フィットスケールに対応した落下・境界線判定
                y_bottom = y_hole_line_s - (note_start - target_tick) * px_per_tick * scale
                y_top = y_hole_line_s - (note_end - target_tick) * px_per_tick * scale
                
                if y_bottom >= 0 and y_top <= y_hole_line_s:
                    fing = note_data.get("fingering") 
                    if not fing: 
                        continue
                    
                    key = (note_start, note_val)
                    visible_keys.add(key)
                    
                    is_editable = is_note_editable(note_val, inst_type)
                    
                    if edit_mode_active and is_editable:
                        col_hex = "#FF0000" 
                        edit_tag = f"note_edit_{note_start}_{note_val}"
                    else:
                        col_hex = note_color_blow if fing["action"] == "吹" else note_color_draw
                        edit_tag = "" 
                    
                    simulated_note = note_val
                    if "バス" in inst_type:
                        simulated_note = note_val + 36
                    
                    lane_idx = simulated_note - 48
                    
                    lane_x_left = (72 + lane_idx * 16) * scale - X_shift_notes
                    lane_x_right = lane_x_left + 16 * scale
                    
                    note_in_range = is_note_in_range(note_val, inst_type)
                    
                    if key not in canvas.note_pool:
                        canvas.note_pool[key] = {"rect_id": None, "poly_id": None, "lower_rect_id": None}
                    pool_item = canvas.note_pool[key]
                    if "lower_rect_id" not in pool_item:
                        pool_item["lower_rect_id"] = None
                    
                    tag_list = ["note"]
                    if edit_tag: tag_list.append(edit_tag)
                    tag_tuple = tuple(tag_list)

                    dest_x_center = get_note_dest_x(note_val, inst_type, scale=scale, start_tick=note_start)
                    dest_left = dest_x_center - 6 * scale
                    dest_right = dest_x_center + 6 * scale

                    if is_straight_mode:
                        # 垂直落下モード：画面上端 (y=0) から穴直上 (y_hole_line_s) まで目標穴の真上を垂直に落下
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
                                    pool_item["lower_rect_id"] = canvas.create_rectangle(
                                        dest_left, s_top, dest_right, s_bottom,
                                        fill=col_hex, outline="", tags=tag_tuple
                                    )
                                else:
                                    canvas.coords(pool_item["lower_rect_id"], dest_left, s_top, dest_right, s_bottom)
                                    canvas.itemconfig(pool_item["lower_rect_id"], fill=col_hex, tags=tag_tuple)
                            else:
                                if pool_item["lower_rect_id"] is not None:
                                    canvas.delete(pool_item["lower_rect_id"])
                                    pool_item["lower_rect_id"] = None
                    else:
                        # 3段階収束 (標準) モード：
                        # [第1段階] 上部60音等幅垂直レーン (0 <= y <= y_collide_s)
                        v_top = max(0.0, y_top)
                        v_bottom = min(y_collide_s, y_bottom)
                        if v_bottom > v_top:
                            if pool_item["rect_id"] is None:
                                pool_item["rect_id"] = canvas.create_rectangle(
                                    lane_x_left, v_top, lane_x_right, v_bottom,
                                    fill=col_hex, outline="", tags=tag_tuple
                                )
                            else:
                                canvas.coords(pool_item["rect_id"], lane_x_left, v_top, lane_x_right, v_bottom)
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
                                    pool_item["poly_id"] = canvas.create_polygon(
                                        x_top_left, t_top, x_top_right, t_top,
                                        x_bottom_right, t_bottom, x_bottom_left, t_bottom,
                                        fill=col_hex, outline="", tags=tag_tuple
                                    )
                                else:
                                    canvas.coords(
                                        pool_item["poly_id"],
                                        x_top_left, t_top, x_top_right, t_top,
                                        x_bottom_right, t_bottom, x_bottom_left, t_bottom
                                    )
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
                                    pool_item["lower_rect_id"] = canvas.create_rectangle(
                                        dest_left, s_top, dest_right, s_bottom,
                                        fill=col_hex, outline="", tags=tag_tuple
                                    )
                                else:
                                    canvas.coords(pool_item["lower_rect_id"], dest_left, s_top, dest_right, s_bottom)
                                    canvas.itemconfig(pool_item["lower_rect_id"], fill=col_hex, tags=tag_tuple)
                            else:
                                if pool_item["lower_rect_id"] is not None:
                                    canvas.delete(pool_item["lower_rect_id"])
                                    pool_item["lower_rect_id"] = None
                        else:
                            if pool_item["lower_rect_id"] is not None:
                                canvas.delete(pool_item["lower_rect_id"])
                                pool_item["lower_rect_id"] = None
            
            for old_key in list(canvas.note_pool.keys()):
                if old_key not in visible_keys:
                    pool_item = canvas.note_pool.pop(old_key)
                    for cid in pool_item.values():
                        if cid is not None:
                            canvas.delete(cid)
        else:
            for pool_item in canvas.note_pool.values():
                for cid in pool_item.values():
                    if cid is not None:
                        canvas.delete(cid)
            canvas.note_pool.clear()

    # 運指変更モードが有効な場合、凡例の下に「常時運指表示枠」を描画 (スケール連動)
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

    canvas.delete("static_guide_text")

    # 3. Z-Index順（重なり順）の安全絶対強制ソート
    canvas.tag_lower("static_background")
    canvas.tag_lower("static_grid")
    canvas.tag_lower("static_grid_border")
    canvas.tag_raise("dynamic_lever")
    canvas.tag_raise("static_plate")
    canvas.tag_raise("static_hole")
    canvas.tag_raise("cached_led")
    canvas.tag_raise("dynamic_lever_ring")  
    canvas.tag_raise("note")              
    canvas.tag_raise("cached_shadow")
    canvas.tag_raise("cached_body")
    canvas.tag_raise("static_text")
    canvas.tag_raise("edit_status_panel") 
    canvas.tag_raise("static_legend")