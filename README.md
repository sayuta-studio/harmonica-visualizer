# Harmonica Visualizer (Ver.4.2.0 Harmonica Studio Edition)

<div align="center">

![Version](https://img.shields.io/badge/バージョン-v4.2.0-blue.svg?style=flat-square)
![License](https://img.shields.io/badge/ライセンス-GNU%20GPL%20v3-green.svg?style=flat-square)
![Platform](https://img.shields.io/badge/対応OS-Windows%2010%20%7C%2011%20(64--bit)-lightgrey.svg?style=flat-square)
![Framework](https://img.shields.io/badge/GUI-PyQt6%20%2F%20OpenGL-orange.svg?style=flat-square)
![Audio](https://img.shields.io/badge/音源-Windows%20gm.dls%20(Pure%20Python)-red.svg?style=flat-square)

**クロマチックハーモニカのための演奏練習支援 ＆ 演奏動画制作スタジオデスクトップアプリ**

[**📥 ダウンロード (最新版ポータブルZIP)**](https://github.com/sayuta/harmonica-visualizer/releases/latest) • [**📖 機能一覧**](#-主な機能) • [**🛠️ 開発者向けガイド**](#-開発者向けソースコードからの実行方法)

</div>

---

## 📖 概要

**Harmonica Visualizer** は、クロマチックハーモニカ（12穴 / 14穴 / 16穴）の演奏者、音楽学習者、そして動画クリエイターのために開発されたWindows向けスタジオアプリケーションです。

MIDIファイルを読み込むだけで、吹き音・吸い音・スライドレバーの押し引きをリアルタイムに美しく可視化し、日々の練習を強力にサポートします。さらに、YouTube Shorts や TikTok 向けの **9:16 縦長動画** や、通常の **16:9 横長動画**、動画編集ソフト用の **クロマキー（透明背景）動画** の書き出しまで、本アプリ1台で完結します。

---

## 📥 ダウンロード（ポータブル版）

Pythonのインストールや面倒な環境構築は一切不要です。解凍してすぐに遊べるポータブルZIPを配布しています。

1. [**Releases ページ**](https://github.com/sayuta/harmonica-visualizer/releases/latest) から最新の `HarmonicaVisualizer-v4.2.0-windows-x64.zip` をダウンロードします。
2. ダウンロードした ZIP ファイルをお好きなフォルダ（「ドキュメント」や「デスクトップ」など）へ展開（すべて解凍）します。
3. フォルダ内の `HarmonicaVisualizer.exe` をダブルクリックして起動します。

> [!TIP]
> ### 🛡️ 初回起動時の「WindowsによってPCが保護されました」について
> 本ソフトはオープンソースで個人開発された初版アプリであるため、初回起動時に Windows SmartScreen（青いポップアップ警告画面）が表示される場合があります。
> 
> **起動手順（安全に実行する方法）:**
> 1. 警告画面内の **「詳細情報」** をクリックします。
> 2. 右下に表示される **「実行」** ボタンを押します。
> 
> *(本ソフトウェアのソースコードはすべて GNU GPL v3 に基づき GitHub 上で 100% 公開されており、有害なプログラムは一切含まれていません。)*

---

## ✨ 主な機能

### 1. 🎷 練習スタジオ（リアルタイム運指可視化）
* **マルチモデル対応**: 12穴、14穴、16穴（C調・各種調子）のクロマチックハーモニカに対応。
* **OpenGL リアルタイムレーン描画**: 等速で下落するノーツ軌道、穴のリアルタイム発光、スライドレバーの連動アニメーションを高フレームレートで描画。
* **充実の練習サポートツール**:
  * スロー再生・テンポ変更（20% 〜 200%）
  * 半音単位の移調（キー変更）機能
  * 苦手な小節を反復練習できる A-B 区間リピート
  * メトロノーム機能 ＆ 前奏カウントイン機能
* **マイク録音・多重テイク管理**:
  * お手持ちのマイクで自身の演奏を録音し、伴奏と同期再生してチェック可能。
  * スタジオ品質のルーム／ホール／エコーチェンバー・リバーブ（残響DSP）を搭載。

### 2. 🎬 動画制作スタジオ（SNS・動画サイト向けエクスポート）
* **YouTube Shorts / TikTok / Reels 特化（9:16 縦長動画）**:
  * 画面の上半分または下半分に16:9比率のハーモニカ演奏画面を配置し、空いたスペースにPV映像やイラストを合成しやすいレイアウト設計。
* **フルHD 16:9 横長動画 / クロマキー透過動画**:
  * 背景画像や背景動画のオーバーレイ合成に対応。
  * 背景をグリーンバック／ブルーバックにした透過素材動画（アルファチャンネル書き出し）を出力可能。
* **タイトルテロップ演出**: 曲名や演奏者名のタイトル表示（表示秒数・カット／フェードアウト設定）。
* **高速パイプライン処理**: 同梱の FFmpeg を内部で連携させ、高画質・高音質な MP4 を安定して書き出し。

### 3. 🎹 Pure-Python GM-DLS サンプリング音源エンジン
* Windows 10 / 11 に標準搭載されている高品質な Roland GS サウンドフォント（`gm.dls`）を、外部DLLや追加ソフト不要で Pure Python（NumPy）のみで直接解析・再生。
* ピアノ、ストリングス、ベース、ドラム等の本格的な伴奏音声をオフライン合成します。

### 4. 📁 楽曲プロジェクト・自己完結コンテナ
* 楽曲ごとに原本MIDI、録音テイクWAV、外部伴奏、書き出し動画、運指設定を1つのフォルダ（`projects/<曲名>/`）にカプセル化して管理。フォルダの移動やバックアップも簡単です。

---

## 🛠️ 開発者向け（ソースコードからの実行方法）

Python 環境をお持ちの方、または開発・改造に参加される方向けのセットアップ手順です。

### 動作前提環境
* Windows 10 / 11 (64-bit)
* Python 3.12, 3.13, または 3.14
* [FFmpeg](https://ffmpeg.org/)（動画書き出し機能を利用する場合。システムPATHまたはリポジトリルートに `ffmpeg.exe` を配置）

### セットアップと起動手順
```powershell
# 1. リポジトリをクローン
git clone https://github.com/sayuta/harmonica-visualizer.git
cd harmonica-visualizer

# 2. 仮想環境を作成して有効化
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. 依存ライブラリをインストール
pip install -r requirements.txt

# 4. アプリケーションを起動
python src/main.py
```

### 自動テストスイートの実行
```powershell
# 全機能・全回帰テスト（全項目PASSを確認）
python tests/verify_v420_studio_complete.py
```

### ポータブル配布パッケージのビルド
```powershell
# PyInstaller によるディレクトリ型（--onedir）ビルド
python -m PyInstaller --clean HarmonicaVisualizer.spec
```

---

## 📄 ライセンス & サードパーティ・クレジット

本ソフトウェアは **GNU General Public License v3.0 (GPL v3)** のもとで公開されているオープンソース・ソフトウェアです。  
詳細なライセンス条項は同封の [`LICENSE`](LICENSE) ファイルをご確認ください。

```text
Harmonica Visualizer (Ver.4.2.0 Harmonica Studio Edition)
Copyright (C) 2026 サユタ
```

### サードパーティ製ライブラリ
* **[PyQt6](https://riverbankcomputing.com/software/pyqt/)** - GUIフレームワークおよびOpenGL描画コンテキスト (GNU GPL v3)
* **[FFmpeg](https://ffmpeg.org/)** - 動画エンコード・音声合成パイプライン (GNU GPL v3 / LGPL v2.1)
* **[pygame-ce](https://pyga.me/)** - 低遅延音声再生・SDL_mixerバックエンド (GNU LGPL v2.1)
* **[NumPy](https://numpy.org/)** - DSP音声処理およびDLS波形解析 (BSD-3-Clause)
* **[Mido](https://mido.readthedocs.io/)** - MIDIデータ解析 (MIT License)

### 🎵 Windows標準サウンドフォント（gm.dls）に関する法的明記
本ソフトウェアの内蔵サンプラー（`GmDlsSampler`）は、ユーザーの Windows OS 上に標準搭載されているシステムファイル（`%SystemRoot%\System32\drivers\gm.dls` 等）を実行時に動的に読み込んで利用します。**Microsoft Corporation および Roland Corporation が著作権を有する `gm.dls` ファイル自体は、再配布パッケージ内に一切同梱・含まれていません**。
