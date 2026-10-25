# -*- coding: utf-8 -*-
# test_audio.py (即落ち防止 ＆ 実行時絶対パス安全自動解決版)
# - 【安全設計】：作業フォルダがWindowsシステムディレクトリ等になっていても、
#   スクリプト自身が存在するフォルダを基準にして安全・正確にWAVを書き出します。

import os
import sys
import traceback

def test_synthesizer():
    print("[テスト] WAV物理合成のテストを開始します...")
    
    # 自作の audio_engine から合成関数をロード
    from audio_engine import synthesize_midi_to_wav
    
    # 1. テスト用の擬似楽譜データ（ド・レ・ミ・ファ・ソ）
    test_melody = [
        {"note": 60, "start_time": 2.0, "duration": 0.8},  # ド (C4) - カウントイン2.0秒の後
        {"note": 62, "start_time": 2.8, "duration": 0.8},  # レ (D4)
        {"note": 64, "start_time": 3.6, "duration": 0.8},  # ミ (E4)
        {"note": 65, "start_time": 4.4, "duration": 0.8},  # ファ (F4)
        {"note": 67, "start_time": 5.2, "duration": 1.5},  # ソ (G4)
    ]
    
    # 2. テスト用の擬似小節タイムライン（4/4拍子、2小節分）
    test_timeline = [
        {"measure_num": 1, "start_tick": 0, "end_tick": 1920, "num": 4, "den": 4},
        {"measure_num": 2, "start_tick": 1920, "end_tick": 3840, "num": 4, "den": 4},
    ]
    
    # 🚀【解決】：スクリプト自身が置いてあるフォルダを絶対パス基準にして保存先を確定
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, "test_harmonica.wav")
    
    # 3. 物理合成レンダラーの実行 (BPM=120, カウントイン1小節=4拍)
    synthesize_midi_to_wav(
        midi_notes=test_melody,
        current_bpm=120.0,
        max_duration=6.7,
        is_count_in=True,
        is_metro=True,
        output_wav_path=output_path,
        time_sig_num=4,
        time_sig_den=4,
        count_in_measures=1,
        measures_timeline=test_timeline,
        metronome_pattern="標準（頭拍強調）",
        ticks_per_beat=480,
        sample_rate=44100
    )
    
    print("\n" + "="*60)
    print(f"[成功] テスト出力完了: '{output_path}'")
    print("="*60)
    print("上記フォルダ内に生成された 'test_harmonica.wav' を再生して、音質とタイミングをご確認ください。")

if __name__ == "__main__":
    try:
        test_synthesizer()
    except Exception as e:
        print("\n" + "="*60)
        print("[致命的エラー] テスト実行中にクラッシュしました。")
        print("="*60)
        traceback.print_exc()
        print("="*60)
    
    print("\n確認後、Enterキーを押して画面を閉じてください...")
    input()