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
import numpy as np


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


def load_external_audio_pcm(filepath, sample_rate=44100):
    """
    外部オーディオファイル（.wav / .mp3 / .m4a / .flac / .ogg / .mp4 等）を読み込み、
    44.1kHz・16-bit・2chステレオのC連続NumPy配列 (shape=(N, 2), dtype=int16) として返します。
    """
    import subprocess
    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError(f"音源ファイルが見つかりません: {filepath}")

    # 1. FFmpegパイプによる高速デコード＆リサンプリング（MP3/WAV/M4A全対応）
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        cmd = [
            "ffmpeg", "-v", "error",
            "-i", filepath,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "2",
            "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, timeout=30)
        if res.returncode == 0 and len(res.stdout) >= 4:
            n_frames = len(res.stdout) // 4
            pcm = np.frombuffer(res.stdout[:n_frames * 4], dtype=np.int16).reshape(-1, 2).copy()
            return np.ascontiguousarray(pcm, dtype=np.int16)
    except Exception as e:
        print(f"[AudioEngine] FFmpegデコードフォールバック試行: {e}")

    # 2. フォールバック：標準waveまたはpygame.mixer経由でデコード
    try:
        import pygame
        if pygame.mixer.get_init() is not None:
            snd = pygame.mixer.Sound(filepath)
            arr = pygame.sndarray.array(snd)
            if arr.ndim == 1:
                arr = np.column_stack((arr, arr))
            elif arr.shape[1] > 2:
                arr = arr[:, :2]
            return np.ascontiguousarray(arr, dtype=np.int16)
    except Exception:
        pass

    with wave.open(filepath, 'rb') as wf:
        n_ch = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        fr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
        if sampwidth == 2:
            data = np.frombuffer(raw, dtype=np.int16)
        elif sampwidth == 1:
            data = ((np.frombuffer(raw, dtype=np.uint8).astype(np.int16) - 128) << 8)
        else:
            raise ValueError(f"未対応のサンプル幅です: {sampwidth} bytes")
        if n_ch == 1:
            stereo = np.column_stack((data, data))
        else:
            stereo = data.reshape(-1, n_ch)[:, :2]
        if fr != sample_rate and len(stereo) > 0:
            new_len = int(round(len(stereo) * sample_rate / float(fr)))
            x_old = np.linspace(0.0, 1.0, len(stereo))
            x_new = np.linspace(0.0, 1.0, new_len)
            left = np.interp(x_new, x_old, stereo[:, 0]).astype(np.int16)
            right = np.interp(x_new, x_old, stereo[:, 1]).astype(np.int16)
            stereo = np.column_stack((left, right))
        return np.ascontiguousarray(stereo, dtype=np.int16)


def synthesize_midi_to_wav(midi_notes, current_bpm, max_duration, is_count_in, is_metro, output_wav_path, 
                           time_sig_num=4, time_sig_den=4, count_in_measures=1, measures_timeline=None, 
                           metronome_pattern="標準（頭拍強調）", ticks_per_beat=480, sample_rate=44100,
                           tick_to_sec_fn=None, accompaniment_notes=None, part_play_mode="全パート再生",
                           intro_sec=0.0, ext_audio_pcm=None, ext_audio_mode="頭出し確認 (再生:両方 / 動画:外部のみ)",
                           ext_audio_offset_ms=0, ext_audio_vol_pct=100.0, sec_a_in_song=0.0, yt_limiter=True):
    """
    MIDI演奏情報および外部オーディオ（ミリ秒オフセット・音量%・YouTube上限リミッター対応）から
    高音質PCM WAVファイルを高速に物理合成して出力します。
    """
    extended_duration = max(0.5, float(max_duration)) + 0.5
    num_samples = int(extended_duration * sample_rate)
    samples = np.zeros(num_samples, dtype=np.float32)

    has_ext_audio = (ext_audio_pcm is not None and len(ext_audio_pcm) > 0 and "外部音源オフ" not in str(ext_audio_mode))
    # 「頭出し確認 (再生:両方 / 動画:外部のみ)」または「外部音源のみ」の場合は、動画書き出し時にガイド音を自動ミュート
    include_guide_synth = True
    if has_ext_audio and ("動画:外部のみ" in str(ext_audio_mode) or "外部音源のみ" in str(ext_audio_mode)):
        include_guide_synth = False

    # 1小節目の拍子
    first_time_sig_num = 4
    first_time_sig_den = 4
    if measures_timeline:
        first_time_sig_num = measures_timeline[0]['num']
        first_time_sig_den = measures_timeline[0]['den']
        
    count_in_beats = (count_in_measures * first_time_sig_num) if is_count_in else 0
    count_in_beat_duration = (60.0 / current_bpm) * (4.0 / first_time_sig_den)
    count_in_duration = count_in_beats * count_in_beat_duration if count_in_beats > 0 else 0.0

    if include_guide_synth:
        # A. カウントイン部分のクリック音合成（intro_sec分だけ後ろから開始）
        if count_in_beats > 0:
            for beat in range(count_in_beats):
                beat_time = intro_sec + beat * count_in_beat_duration
                is_strong = (beat % first_time_sig_num == 0)
                freq = 1200.0 if is_strong else 800.0
                
                click_wave = generate_metronome_click(freq, sample_rate, duration=0.05)
                
                start_sample = int(beat_time * sample_rate)
                end_sample = min(start_sample + len(click_wave), num_samples)
                if 0 <= start_sample < num_samples and end_sample > start_sample:
                    samples[start_sample:end_sample] += click_wave[:end_sample - start_sample]
                
        # B. 本編メトロノーム部分のクリック音合成
        if is_metro and measures_timeline:
            for m in measures_timeline:
                num = m['num']
                den = m['den']
                beat_len_ticks = ticks_per_beat * (4.0 / den)
                m_base_time = m.get('start_time', None)
                
                for b in range(num):
                    if m_base_time is not None:
                        sec_per_tick = 60.0 / (current_bpm * ticks_per_beat)
                        beat_time = m_base_time + (b * beat_len_ticks) * sec_per_tick
                    else:
                        beat_tick = m['start_tick'] + b * beat_len_ticks
                        if tick_to_sec_fn is not None:
                            beat_time_in_midi = tick_to_sec_fn(beat_tick) - sec_a_in_song
                        else:
                            sec_per_tick = 60.0 / (current_bpm * ticks_per_beat)
                            beat_time_in_midi = beat_tick * sec_per_tick - sec_a_in_song
                        beat_time = intro_sec + count_in_duration + beat_time_in_midi

                    if beat_time < intro_sec or beat_time >= extended_duration:
                        continue
                        
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
                        if 0 <= start_sample < num_samples and end_sample > start_sample:
                            samples[start_sample:end_sample] += click_wave[:end_sample - start_sample]
        
        # C-1. 主旋律ハーモニカ演奏音符の合成
        if part_play_mode in ("全パート再生", "主旋律ソロ") and midi_notes:
            for note_data in midi_notes:
                note = note_data['note']
                start = note_data['start_time']
                dur = note_data['duration']
                
                start_sample = max(0, int(start * sample_rate))
                end_sample = int((start + dur) * sample_rate)
                
                if start_sample >= num_samples:
                    continue
                end_sample = min(end_sample, num_samples)
                
                freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
                
                target_length = end_sample - start_sample
                if target_length > 0:
                    wave_data = generate_harmonica_tone(freq, target_length, sample_rate)
                    samples[start_sample:end_sample] += wave_data

        # C-2. 伴奏パート音符の合成
        if part_play_mode in ("全パート再生", "伴奏のみ(カラオケ)") and accompaniment_notes:
            for acc_data in accompaniment_notes:
                note = acc_data['note']
                start = acc_data.get('start_time', acc_data.get('original_start_time', 0.0) + count_in_duration + intro_sec)
                dur = acc_data.get('duration', acc_data.get('original_duration', 0.1))
                vel_scale = max(0.2, min(1.0, acc_data.get('velocity', 80) / 100.0))

                start_sample = max(0, int(start * sample_rate))
                end_sample = int((start + dur) * sample_rate)

                if start_sample >= num_samples:
                    continue
                end_sample = min(end_sample, num_samples)

                freq = 440.0 * (2.0 ** ((note - 69) / 12.0))
                target_length = end_sample - start_sample
                if target_length > 0:
                    acc_wave = generate_accompaniment_tone(freq, target_length, sample_rate) * vel_scale
                    samples[start_sample:end_sample] += acc_wave

        # ガイド音のノーマライズ（最大振幅80%）
        max_val = np.max(np.abs(samples))
        if max_val > 0.0:
            samples = (samples / max_val) * 0.8

    # D. 外部オーディオの合成（ステレオ出力）
    if has_ext_audio:
        out_stereo = np.zeros((num_samples, 2), dtype=np.float32)
        if include_guide_synth:
            out_stereo[:, 0] = samples * 0.85
            out_stereo[:, 1] = samples * 0.85

        # 動画上の本編開始時刻 (intro_sec + count_in_duration) が、原曲の sec_a_in_song に対応する
        video_song_start_sec = intro_sec + count_in_duration
        offset_sec = float(ext_audio_offset_ms) / 1000.0
        # video_t >= intro_sec において ext_pos_sec = (video_t - video_song_start_sec) + sec_a_in_song - offset_sec
        # すなわち ext_pos_sec = 0 となる video_t は:
        ext_zero_in_video_sec = video_song_start_sec - sec_a_in_song + offset_sec

        dst_min_sample = int(round(video_song_start_sec * sample_rate))
        dst_start = max(dst_min_sample, int(round(ext_zero_in_video_sec * sample_rate)))
        src_start = max(0, int(round((dst_start / float(sample_rate) - ext_zero_in_video_sec) * sample_rate)))

        avail_src = max(0, len(ext_audio_pcm) - src_start)
        avail_dst = max(0, num_samples - dst_start)
        copy_len = min(avail_src, avail_dst)

        if copy_len > 0:
            vol_gain = max(0.0, min(2.5, float(ext_audio_vol_pct) / 100.0))
            ext_slice = (ext_audio_pcm[src_start:src_start + copy_len].astype(np.float32) / 32768.0) * vol_gain
            # 切り出し境界のクリックノイズを防ぐ15msフェードイン・フェードアウト
            fi = min(int(0.015 * sample_rate), copy_len)
            fo = min(int(0.025 * sample_rate), copy_len)
            if fi > 0:
                ext_slice[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)[:, np.newaxis]
            if fo > 0:
                ext_slice[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)[:, np.newaxis]
            out_stereo[dst_start:dst_start + copy_len] += ext_slice

        # YouTube上限リミッター（True Peak -1.0 dBFS = 約0.891 超過時に自動スケーリング保護）
        peak = float(np.max(np.abs(out_stereo)))
        if yt_limiter:
            yt_ceiling = 0.89125  # -1.0 dBFS (YouTube推奨ピーク上限)
            if peak > yt_ceiling:
                out_stereo *= (yt_ceiling / peak)
        else:
            if peak > 1.0:
                out_stereo = np.clip(out_stereo, -1.0, 1.0)

        samples_16 = (out_stereo * 32767.0).astype(np.int16)
        with wave.open(output_wav_path, 'wb') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples_16.tobytes())
    else:
        if yt_limiter:
            peak = float(np.max(np.abs(samples)))
            if peak > 0.89125:
                samples *= (0.89125 / peak)
        samples_16 = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
        with wave.open(output_wav_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples_16.tobytes())