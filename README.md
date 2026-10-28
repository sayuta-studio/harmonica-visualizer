# Harmonica Visualizer (Ver.4.2.1 Harmonica Studio Edition)

<div align="center">

![Version](https://img.shields.io/badge/バージョン-v4.2.1-blue.svg?style=flat-square)
![License](https://img.shields.io/badge/ライセンス-GNU%20GPL%20v3-green.svg?style=flat-square)
![Platform](https://img.shields.io/badge/対応OS-Windows%2010%20%7C%2011%20(64--bit)-lightgrey.svg?style=flat-square)
![Framework](https://img.shields.io/badge/GUI-PyQt6%20%2F%20OpenGL-orange.svg?style=flat-square)
![Audio](https://img.shields.io/badge/音源-Windows%20gm.dls%20サンプラー%20(内蔵DSP)-red.svg?style=flat-square)

**クロマチックハーモニカのための演奏練習支援 ＆ 演奏動画制作スタジオデスクトップアプリ**

[**📥 ダウンロード (最新版ポータブルZIP)**](https://github.com/sayuta-studio/harmonica-visualizer/releases/latest) • [**📖 機能一覧**](#-主な機能) • [**🛠️ 開発者向けガイド**](#-開発者向けソースコードからの実行方法) • [**⚖️ 利用上の注意**](#️-利用上の注意)

</div>

---

## 📖 概要

**Harmonica Visualizer** は、クロマチックハーモニカ（12穴 / 14穴 / 16穴）の演奏者、音楽学習者、そして動画クリエイターのために開発された Windows 向けスタジオアプリケーションです。

MIDIファイルを読み込むだけで、吹き音・吸い音・スライドレバーの押し引きをリアルタイムに美しく可視化し、日々の練習を強力にサポートします。さらに、YouTube Shorts や TikTok 向けの **9:16 縦長動画** や通常の **16:9 横長動画**、動画編集ソフト用の **クロマキー合成用動画（緑・青背景 MP4）** や **アルファチャンネル付き透過動画（ProRes 4444 MOV）** の書き出しまで、本アプリ1台で完結します。

---

## 📥 ダウンロード（ポータブル版）

Pythonのインストールや環境構築は不要です。解凍してすぐに利用できるポータブルZIPを配布しています。

1. [**Releases ページ**](https://github.com/sayuta-studio/harmonica-visualizer/releases/latest) から最新の `HarmonicaVisualizer-v4.2.1-windows-x64.zip` をダウンロードします。
2. ダウンロードした ZIP ファイルをお好きなフォルダ（「ドキュメント」や「デスクトップ」など）へ展開（すべて解凍）します。
3. フォルダ内の `HarmonicaVisualizer.exe` をダブルクリックして起動します。

> [!TIP]
> ### 🛡️ 初回起動時の Windows SmartScreen について
> 本ソフトウェアは個人開発のオープンソースアプリケーションです。コード署名（EV証明書等）を行っていない場合や、ダウンロード実績などに基づく評価が十分でない場合、初回起動時に Windows SmartScreen の警告（青い画面）が表示されることがあります。
> 
> 警告が表示されたことだけで直ちにマルウェアと判断されるわけではありません。一方、警告が表示されないことや、ソースコードが公開されていることだけで安全性が保証されるわけでもありません。
> 
> 実行する場合は、公式の配布元（本GitHubリポジトリの Releases）から入手したファイルであることを確認してください。安全性を確認できない場合は、実行しないでください。
> 
> **実行手順の例（安全性を確認した上で起動する場合）:**
> 1. 警告画面内の **「詳細情報」** をクリックします。
> 2. 発行元やアプリ名を確認し、右下に表示される **「実行」** ボタンを押します。
> 
> ※ Windowsのセキュリティ設定や組織の管理者ポリシーによっては、実行がブロックされる場合があります。  
> ※ 詳細については、[Microsoft Learn: SmartScreen の評判について](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation) をご参照ください。

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
* **フルHD 16:9 横長動画**:
  * 背景画像や背景動画のオーバーレイ合成、タイトルテロップ演出（曲名・演奏者名）に対応。
* **動画編集ソフト向け素材出力**:
  * **クロマキー合成用動画（MP4 / 単色背景）**: グリーンバック（`#00FF00`）またはブルーバック（`#0000FF`）の単色背景でH.264/AAC MP4を書き出し。動画編集ソフト（Premiere Pro, DaVinci Resolve, AviUtl等）のカラーキー／クロマキー機能で背景を抜いて合成可能。
  * **アルファチャンネル付き透過動画（QuickTime MOV）**: Apple ProRes 4444（`yuva444p10le` / リニアPCM音声）の `.mov` 動画を書き出し。アルファチャンネル対応の編集ソフトでキーイング不要でそのまま透過配置可能。
* **高速パイプライン処理**: 同梱の FFmpeg を内部で連携させ、高画質・高音質な動画を安定して書き出し。

### 3. 🎹 内蔵 GM-DLS サンプリング音源エンジン
* Windows 上に存在する `gm.dls` サウンドフォントを実行時に読み込み、外部のMIDI音源ソフトウェアを別途インストールすることなく、ピアノ、ベース、ストリングス、ドラム等の伴奏音声をオフライン合成します（NumPyによるDSP波形処理）。

### 4. 📁 楽曲プロジェクト・自己完結コンテナ
* 楽曲ごとに原本MIDI、録音テイクWAV、外部伴奏、書き出し動画、運指設定を1つのフォルダ（`projects/<曲名>/`）にカプセル化して管理。フォルダの移動やバックアップも簡単です。

---

## 🛠️ 開発者向け（ソースコードからの実行方法）

Python 環境をお持ちの方、または開発・改造に参加される方向けのセットアップ手順です。

### 動作前提環境
* Windows 10 / 11 (64-bit)  
  *(※ Windows 10 のマイクロソフトによる標準サポートは2025年10月14日に終了しています。本アプリは動作対象として確認していますが、最新のOS環境でのご利用を推奨します)*
* Python 3.12, 3.13, または 3.14
* [FFmpeg](https://ffmpeg.org/)（動画書き出し機能を利用する場合。システムPATHまたはリポジトリルートに `ffmpeg.exe` を配置）

### セットアップと起動手順
```powershell
# 1. リポジトリをクローン
git clone https://github.com/sayuta-studio/harmonica-visualizer.git
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
# 開発・検証用テストスイートの実行
python tests/verify_v420_studio_complete.py
```

> **【リリース検証実績】**  
> Ver.4.2.1 リリース検証環境（Windows 11 Pro 64-bit, Python 3.14, PyQt6 6.8.1）において、上記テストスイートの全12テストスイート・全回帰テストが PASS することを確認済みです。

### ポータブル配布パッケージのビルド
```powershell
# PyInstaller によるディレクトリ型（--onedir）ビルド
python -m PyInstaller --clean packaging/HarmonicaVisualizer.spec
```

---

## 📄 ライセンス & サードパーティ・クレジット

本ソフトウェア本体は **GNU General Public License v3.0 (GPL v3)** のもとで公開されているオープンソース・ソフトウェアです。  
詳細なライセンス条項は同封の [`LICENSE`](LICENSE) ファイルをご確認ください。

```text
Harmonica Visualizer (Ver.4.2.1 Harmonica Studio Edition)
Copyright (C) 2026 サユタ
```

### サードパーティ製ライブラリおよび外部ツール
依存ライブラリおよび同梱バイナリの詳細な著作権表示・ライセンス条項・ソースコード入手先については、[`THIRD_PARTY_NOTICES.md`](docs/THIRD_PARTY_NOTICES.md) をご参照ください。

* **[PyQt6](https://riverbankcomputing.com/software/pyqt/)** - GUIフレームワーク・OpenGL描画コンテキスト管理 (GNU GPL v3)
* **[Qt 6](https://www.qt.io/)** - GUIランタイムライブラリ (GNU LGPL v3 / GPL v3、`_internal/PyQt6/Qt6/bin/` 配下の動的リンクライブラリ)
* **[FFmpeg](https://ffmpeg.org/)** - 動画エンコード・音声合成パイプライン (GNU GPL v3 ビルド、外部プロセスとしてコマンドライン起動)
* **[pygame-ce](https://pyga.me/)** - 低遅延音声再生・SDL2バックエンド (GNU LGPL v2.1+)
* **[NumPy](https://numpy.org/)** - DSP音声処理および波形解析 (BSD-3-Clause)
* **[Pillow](https://python-pillow.org/)** - スキン・背景画像処理 (HPND License)
* **[Mido](https://mido.readthedocs.io/)** - MIDIデータ解析 (MIT License)

### 🎵 Windows標準サウンドフォント（gm.dls）の取り扱い
* 本ソフトウェアの内蔵サンプラー（`GmDlsSampler`）は、実行時に利用環境の Windows OS 上に存在する `gm.dls` ファイル（`%SystemRoot%\System32\drivers\gm.dls` 等）を参照して動作します。
* `gm.dls` ファイル自体は、本ソフトウェアのソースコードおよび配布パッケージに**一切同梱・再配布していません**。
* 同ファイルの権利は各権利者に帰属し、本ソフトウェアの利用許諾によってその権利が移転または許諾されるものではありません。
* ファイルの存在や配置は利用環境によって異なる場合があります。そのため、ファイルを検出できない環境では、音源機能が利用できない、または制限される場合があります。

---

## ⚖️ 利用上の注意

* 本ソフトウェアを使用して読み込み、録音、編集、合成または出力する MIDI ファイル、音声、画像、動画、その他の素材については、利用者自身が必要な権利や利用許諾を確認してください。
* 本ソフトウェアは、第三者の著作物の利用、複製、公衆送信、動画投稿などが法律上または契約上認められることを保証するものではありません。
* 出力した動画等を公開・配布する場合は、利用する素材および各配信プラットフォームの利用規約・著作権ルールを遵守してください。
