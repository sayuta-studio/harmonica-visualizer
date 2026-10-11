# -*- coding: utf-8 -*-
# audio_engine.py (STEP 3-A: 高音質WAV物理合成 ＆ Beepシンセ ➔ 1サンプル丸め誤差根治版)
# - 【音声物理合成エンジン】：MIDIノート、変拍子クリック、カウントインを最高品質の16-bit PCMモノラルWAVファイルへ高速に物理合成。
# - 【倍音ブレンドハーモニカ音】：サイン波のみの単純音を全廃。調和倍音（第2、第3、第4倍音）を動的ブレンドし、リード楽器らしい温かみのある高音質なガイド音を実現。
# - 【完全プチノイズ根絶】：全ノートに15msアタックフェード、35msリリースフェードを標準適用。
# - 【オートノーマライズ】：和音重複による音割れ（デジタルクリッピング）を自動防止。最大振幅を安全な80%(-2.0dB)へ自動正規化スケーリング。
# - 【WAVメトロノーム不整合根治】：MidiEngineのmeasures_timelineを直射ペイント合成。
# - 🚀【解決（1サンプル丸め誤差の完全根治）】：
#   generate_harmonica_toneが秒数(dur)ではなく、ターゲットサンプル数(num_samples：整数)を直接受け取って波形生成。
#   テンポ比(bpm_ratio)の浮動小数丸め誤差による 1サンプルのズレ・形状不一致から引き起こされていた NumPy ブロードキャストエラーを100%完璧に根絶。

import os
import wave
import threading
import numpy as np

if os.name == 'nt':
    import winsound

class WindowsBeepSynth:
    def __init__(self):
        print("[MIDIフォールバック] Windows標準ビープ音(電子音)モードを起動します。")

    def note_on(self, note, velocity, duration_sec, speed=1.0):
        freq = int(440.0 * (2.0 ** ((note - 69) / 12.0)))
        freq = max(37, min(32767, freq))
        duration_ms = int((duration_sec / speed) * 900)
        duration_ms = max(50, duration_ms)

        def beep_thread():
            try:
                winsound.Beep(freq, duration_ms)
            except Exception:
                pass

        t = threading.Thread(target=beep_thread, daemon=True)
        t.start()

    def note_off(self, note):
        pass

    def all_notes_off(self):
        pass

    def close(self):
        pass


class WindowsMidiSynth:
    def __init__(self):
        self.device = None
        self.volume_factor = 0.8
        self.fallback_synth = WindowsBeepSynth()

    def note_on(self, note, velocity, duration_sec=1.0, speed=1.0):
        if self.fallback_synth:
            self.fallback_synth.note_on(note, velocity, duration_sec, speed)

    def note_off(self, note):
        if self.fallback_synth:
            self.fallback_synth.note_off(note)

    def all_notes_off(self):
        if self.fallback_synth:
            self.fallback_synth.all_notes_off()

    def close(self):
        if self.fallback_synth:
            self.fallback_synth.close()


def generate_harmonica_tone(freq, num_samples, sample_rate):
    """
    🚀【解決】：1サンプルの丸め誤差を根絶するため、ターゲットサンプル数（整数）を直接受け取って波形を生成します。
    アタックおよびリリースフェード処理により、プチプチというデジタルノイズを完全に根絶します。
    """
    t = np.arange(num_samples) / sample_rate
    if len(t) == 0:
        return np.array([], dtype=np.float32)
        
    # 調和倍音の配合ブレンド（F0, 2F0, 3F0, 4F0）
    f0 = np.sin(2.0 * np.pi * freq * t)
    f1 = np.sin(2.0 * np.pi * (2.0 * freq) * t) * 0.35  # 第2倍音（オクターブ上の豊かな倍音）
    f2 = np.sin(2.0 * np.pi * (3.0 * freq) * t) * 0.15  # 第3倍音（アコースティックな響きを付与）
    f3 = np.sin(2.0 * np.pi * (4.0 * freq) * t) * 0.05  # 第4倍音（高音域の伸び）
    
    wave_data = f0 + f1 + f2 + f3
    
    # 指数エンベロープによる自然な減衰
    dur = num_samples / sample_rate
    envelope = np.exp(-1.5 * t / dur)
    wave_data *= envelope
    
    # クリックプチノイズを防ぐアタック＆リリースフェード（アタック15ms, リリース35ms）
    fade_in_len = min(int(0.015 * sample_rate), len(wave_data))
    fade_out_len = min(int(0.035 * sample_rate), len(wave_data))
    
    if fade_in_len > 0:
        wave_data[:fade_in_len] *= np.linspace(0.0, 1.0, fade_in_len)
    if fade_out_len > 0:
        wave_data[-fade_out_len:] *= np.linspace(1.0, 0.0, fade_out_len)
        
    return wave_data


def generate_metronome_click(freq, sample_rate, duration=0.05):
    """疑似ウッドブロック調の高精度パルスクリック音波形を生成します。"""
    t = np.arange(int(duration * sample_rate)) / sample_rate
    envelope = np.exp(-35.0 * t / duration)
    click_wave = np.sin(2.0 * np.pi * freq * t) * envelope * 0.3
    return click_wave


def generate_accompaniment_tone(freq, num_samples, sample_rate):
    """
    伴奏パート用の温かみのあるソフトなエレピ／アコースティック調トーンを生成します。
    主旋律のハーモニカ音色を引き立てるよう倍音を抑えた柔らかいエンベロープにします。
    """
    t = np.arange(num_samples) / sample_rate
    if len(t) == 0:
        return np.array([], dtype=np.float32)

    f0 = np.sin(2.0 * np.pi * freq * t)
    f1 = np.sin(2.0 * np.pi * (2.0 * freq) * t) * 0.18
    wave_data = (f0 + f1) * 0.45

    dur = max(0.01, num_samples / sample_rate)
    envelope = np.exp(-2.2 * t / dur)
    wave_data *= envelope

    fade_in_len = min(int(0.012 * sample_rate), len(wave_data))
    fade_out_len = min(int(0.030 * sample_rate), len(wave_data))
    if fade_in_len > 0:
        wave_data[:fade_in_len] *= np.linspace(0.0, 1.0, fade_in_len)
    if fade_out_len > 0:
        wave_data[-fade_out_len:] *= np.linspace(1.0, 0.0, fade_out_len)
    return wave_data


def synthesize_midi_to_wav(midi_notes, current_bpm, max_duration, is_count_in, is_metro, output_wav_path, 
                           time_sig_num=4, time_sig_den=4, count_in_measures=1, measures_timeline=None, 
                           metronome_pattern="標準（頭拍強調）", ticks_per_beat=480, sample_rate=44100,
                           tick_to_sec_fn=None, accompaniment_notes=None, part_play_mode="全パート再生"):
    """
    MIDI演奏情報および変拍子・曲中テンポ変化タイムライン・パート再生モードから
    16-bit PCMモノラルWAVファイルを高速に物理合成して出力します。
    """
    # 末尾に2秒の無音余韻（残響安全パディング）を強制追加
    extended_duration = max_duration + 2.0
    num_samples = int(extended_duration * sample_rate)
    samples = np.zeros(num_samples, dtype=np.float32)
    
    # 1小節目の拍子
    first_time_sig_num = 4
    first_time_sig_den = 4
    if measures_timeline:
        first_time_sig_num = measures_timeline[0]['num']
        first_time_sig_den = measures_timeline[0]['den']
        
    count_in_beats = (count_in_measures * first_time_sig_num) if is_count_in else 0
    
    # A. カウントイン部分のクリック音合成
    count_in_beat_duration = (60.0 / current_bpm) * (4.0 / first_time_sig_den)
    count_in_duration = count_in_beats * count_in_beat_duration if count_in_beats > 0 else 0.0
    
    if count_in_beats > 0:
        for beat in range(count_in_beats):
            beat_time = beat * count_in_beat_duration
            is_strong = (beat % first_time_sig_num == 0)
            freq = 1200.0 if is_strong else 800.0
            
            click_wave = generate_metronome_click(freq, sample_rate, duration=0.05)
            
            start_sample = int(beat_time * sample_rate)
            end_sample = min(start_sample + len(click_wave), num_samples)
            samples[start_sample:end_sample] += click_wave[:end_sample - start_sample]
            
    # B. 本編メトロノーム部分のクリック音合成 (MidiEngine.measures_timelineの直射ペイント)
    if is_metro and measures_timeline:
        for m in measures_timeline:
            num = m['num']
            den = m['den']
            beat_len_ticks = ticks_per_beat * (4.0 / den)
            
            for b in range(num):
                beat_tick = m['start_tick'] + b * beat_len_ticks
                
                # ティックから本編内の正確な秒数を逆算（曲中テンポ変化対応）
                if tick_to_sec_fn is not None:
                    beat_time_in_midi = tick_to_sec_fn(beat_tick)
                else:
                    sec_per_tick = 60.0 / (current_bpm * ticks_per_beat)
                    beat_time_in_midi = beat_tick * sec_per_tick
                
                # カウントイン秒数分だけ後ろにスライド
                beat_time = beat_time_in_midi + count_in_duration
                if beat_time >= extended_duration:
                    break
                    
                is_click_playable = True
                is_strong = (b == 0)
                
                if metronome_pattern == "なし":
                    is_click_playable = False
                elif metronome_pattern == "小節頭のみ":
                    if b != 0:
                        is_click_playable = False
                elif metronome_pattern == "強調なし全拍":
                    is_strong = False
                
                if is_click_playable:
                    freq = 1200.0 if is_strong else 800.0
                    click_wave = generate_metronome_click(freq, sample_rate, duration=0.05)
                    
                    start_sample = int(beat_time * sample_rate)
                    end_sample = min(start_sample + len(click_wave), num_samples)
                    if start_sample < num_samples:
                        samples[start_sample:end_sample] += click_wave[:end_sample - start_sample]
    
    # C-1. 主旋律ハーモニカ演奏音符（サイン波＋倍音ブレンドマルチボイス）の合成
    if part_play_mode in ("全パート再生", "主旋律ソロ") and midi_notes:
        for note_data in midi_notes:
            note = note_data['note']
            start = note_data['start_time']  # カウントイン加算済みの絶対秒
            dur = note_data['duration']
            
            start_sample = int(start * sample_rate)
            end_sample = int((start + dur) * sample_rate)
            
            if start_sample >= num_samples:
                continue
            end_sample = min(end_sample, num_samples)
            
            freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
            
            target_length = end_sample - start_sample
            if target_length > 0:
                wave_data = generate_harmonica_tone(freq, target_length, sample_rate)
                samples[start_sample:end_sample] += wave_data

    # C-2. 伴奏パート音符の合成（全パート再生 または 伴奏のみ(カラオケ) 選択時）
    if part_play_mode in ("全パート再生", "伴奏のみ(カラオケ)") and accompaniment_notes:
        for acc_data in accompaniment_notes:
            note = acc_data['note']
            start = acc_data.get('start_time', acc_data.get('original_start_time', 0.0) + count_in_duration)
            dur = acc_data.get('duration', acc_data.get('original_duration', 0.1))
            vel_scale = max(0.2, min(1.0, acc_data.get('velocity', 80) / 100.0))

            start_sample = int(start * sample_rate)
            end_sample = int((start + dur) * sample_rate)

            if start_sample >= num_samples:
                continue
            end_sample = min(end_sample, num_samples)

            freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
            target_length = end_sample - start_sample
            if target_length > 0:
                acc_wave = generate_accompaniment_tone(freq, target_length, sample_rate) * vel_scale
                samples[start_sample:end_sample] += acc_wave
        
    # D. 音割れ防止のための自動マスタリング（ノーマライズ）
    max_val = np.max(np.abs(samples))
    if max_val > 0.0:
        samples = (samples / max_val) * 0.8  # 最大振幅を安全な80%(-2.0dB)へ自動正規化スケーリング
        
    samples_16 = (samples * 32767).astype(np.int16)
    
    with wave.open(output_wav_path, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples_16.tobytes())