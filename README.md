# Harmonica Visualizer (Studio Edition)

<div align="center">

![Version](https://img.shields.io/badge/version-v4.2.0-blue.svg?style=flat-square)
![License](https://img.shields.io/badge/license-GNU%20GPL%20v3-green.svg?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011%20(64--bit)-lightgrey.svg?style=flat-square)
![Framework](https://img.shields.io/badge/GUI-PyQt6%20%26%20OpenGL-orange.svg?style=flat-square)
![Audio](https://img.shields.io/badge/Sound-Windows%20gm.dls%20%7C%20Pure%20Python-red.svg?style=flat-square)

**A Next-Generation Chromatic Harmonica Practice & Video Production Studio**  
*クロマチックハーモニカのための演奏練習支援 ＆ 演奏動画制作スタジオデスクトップアプリ*

[**📥 Download Portable ZIP (v4.2.0)**](https://github.com/sayuta/harmonica-visualizer/releases/latest) • [**📖 日本語利用ガイド**](#日本語利用ガイド-japanese-guide) • [**🛠️ Developer Setup**](#for-developers)

</div>

---

## 🌟 Highlights

**Harmonica Visualizer** is a specialized desktop studio designed specifically for chromatic harmonica players, music learners, and content creators. It bridges the gap between structured practice and high-impact social media video production (YouTube Shorts, TikTok, Instagram Reels).

* **🎼 Multi-Hole Support**: Built-in interactive layouts for **12-hole, 14-hole, and 16-hole** chromatic harmonicas (C-tuning and custom keys).
* **⚡ Real-Time OpenGL Visualizer**: Falling-notes trajectory lane with dynamic hole glow and lever-action synchronization at high framerates.
* **🎬 Studio-Grade Video Production**: Render 16:9 widescreen or 9:16 vertical split-screen videos with background video/image overlays, title cards, and chromakey alpha channels powered by bundled FFmpeg.
* **🎹 Pure-Python GM-DLS Sampling Synthesizer**: Directly parses and synthesizes Windows built-in Roland GS soundset (`gm.dls`) with zero external C++ dependencies or software installations.
* **🎙️ Multi-Take Audio Recording**: Record your acoustic performance via microphone, sync with MIDI accompaniment, apply studio reverb, and manage multiple takes.

---

## 🚀 Getting Started (For Users)

No Python installation or complex setup is required. The application is distributed as a self-contained portable package.

### 1. Download & Extract
1. Go to the [**Latest Releases**](https://github.com/sayuta/harmonica-visualizer/releases/latest) page.
2. Download `HarmonicaVisualizer-v4.2.0-windows-x64.zip`.
3. Extract the ZIP archive to your preferred location (e.g., `Documents` or `Desktop`).

### 2. Launch
Double-click `HarmonicaVisualizer.exe` in the extracted folder to start playing!

> [!NOTE]
> ### 🛡️ Handling Windows SmartScreen Warning (First Launch)
> Because this is a newly released open-source executable without an expensive commercial code-signing certificate, Windows SmartScreen may show a blue popup:  
> **"Windows protected your PC" (Windows によって PC が保護されました)**.
> 
> **How to proceed safely:**
> 1. Click **"More info" (詳細情報)** on the popup.
> 2. Click the **"Run anyway" (実行)** button that appears.
> 
> *(The entire source code is 100% open under GNU GPL v3, and you can audit every line right here on GitHub!)*

---

## 🎯 Key Features Overview

| Feature | Description |
| :--- | :--- |
| **Interactive Fretboard** | Visualizes blow/draw notes, slide-in/out positions, and note pitch in real-time. |
| **Practice Tools** | Tempo scaling (20%–200%), semitone transposition, A-B loop repeat, metronome, and count-in intro. |
| **Video Production Tab** | Split-screen modes (top/bottom/center harmonica placement), background media overlay, fade-in/out titles, chromakey green-screen export. |
| **Integrated Mixer** | 3-band audio mixer (Harmonica guide synth, accompaniment tracks, microphone recording) with DSP Echo Chamber and Room reverb. |
| **Song Container Engine** | 1-folder 1-project architecture (`projects/<SongName>/`) encapsulating MIDI sources, takes, accompaniment audio, and render outputs. |

---

## 🇯🇵 日本語利用ガイド (Japanese Guide)

<details>
<summary><b>クリックして日本語の利用説明を表示する</b></summary>

### 主な機能
1. **練習モード**:
   - 12穴 / 14穴 / 16穴 クロマチックハーモニカに対応。
   - MIDIファイルを読み込むと、吹音・吸音・スライドレバーの押し引きをリアルタイムに色分け表示。
   - テンポ変更（スロー再生）、移調、A-B区間リピート、メトロノーム機能。
   - マイク録音機能（多重テイク対応・リバーブDSP・伴奏同期試聴）。
2. **動画制作スタジオモード**:
   - YouTube Shorts や TikTok 向けの **9:16 縦型動画**（上半分または下半分にハーモニカを配置し、空き領域にPV映像を配置可能）。
   - 通常の **16:9 横長動画**、動画編集ソフト用の **クロマキー（透明背景）動画** の書き出し。
   - タイトルテロップ表示（表示時間・消え方フェード調整）、FFmpeg高速パイプライン処理。
3. **高品位音源**:
   - Windows標準のサウンドフォント（`gm.dls`）を独自エンジンで直接読み込み、ピアノやドラムなどの本格的な伴奏をオフライン合成します。

### インストールと起動
- リリースページから `HarmonicaVisualizer-v4.2.0-windows-x64.zip` をダウンロードし、右クリックで「すべて展開」してください。
- フォルダ内の `HarmonicaVisualizer.exe` を実行すると起動します（インストール作業不要）。
- 初回起動時に青い画面（Windows SmartScreen）が出た場合は、**「詳細情報」➔「実行」** をクリックしてください。

</details>

---

## 🛠️ For Developers

To run or build Harmonica Visualizer from source code:

### Prerequisites
* Windows 10 / 11 (64-bit)
* Python 3.12, 3.13, or 3.14
* [FFmpeg](https://ffmpeg.org/) installed and available in PATH (or placed in the project root)

### Clone & Run
```powershell
# 1. Clone the repository
git clone https://github.com/sayuta/harmonica-visualizer.git
cd harmonica-visualizer

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the application
python src/main.py
```

### Running Automated Test Suite
```powershell
# Run comprehensive regression and unit verification suites
python tests/verify_v420_studio_complete.py
```

### Building the Distribution Package
```powershell
# Build onedir portable executable using PyInstaller
python -m PyInstaller --clean HarmonicaVisualizer.spec
```

---

## 🏛️ Architecture & Third-Party Credits

Harmonica Visualizer is built upon open technologies:

* **[PyQt6](https://riverbankcomputing.com/software/pyqt/)** - Modern GUI application framework and OpenGL rendering context. (Licensed under GNU GPL v3)
* **[FFmpeg](https://ffmpeg.org/)** - High-performance multimedia streaming, audio mixing, and video encoding pipeline. (Licensed under GNU GPL v3 / LGPL v2.1)
* **[pygame-ce](https://pyga.me/)** - Low-latency audio playback and SDL_mixer backend. (Licensed under GNU LGPL v2.1)
* **[NumPy](https://numpy.org/)** - Vectorized DSP processing, audio buffer manipulation, and RIFF DLS waveform extraction. (Licensed under BSD-3-Clause)
* **[Mido](https://mido.readthedocs.io/)** - MIDI parsing and timeline event compilation. (Licensed under MIT License)

### 🎵 Legal Notice Regarding Windows Soundfont (`gm.dls`)
This software incorporates an in-house RIFF DLS Level 1 parser (`GmDlsSampler`) that dynamically accesses the Microsoft / Roland General MIDI soundset file located in the user's local operating system directory (`%SystemRoot%\System32\drivers\gm.dls`). **The `gm.dls` soundfont file is NOT redistributed or bundled** with this project, in strict compliance with copyright laws and software distribution agreements.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL v3)**.  
See the [`LICENSE`](LICENSE) file for the full license text.

```text
Harmonica Visualizer (Harmonica Studio Edition)
Copyright (C) 2026 サユタ
```
