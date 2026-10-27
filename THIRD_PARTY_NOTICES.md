# Third-Party Software Notices and Information

Harmonica Visualizer (Ver.4.2.0 Harmonica Studio Edition)
Copyright (C) 2026 サユタ
License: GNU General Public License version 3 (GPL v3)

本ソフトウェアおよび配布バイナリパッケージ（ポータブルZIP版）には、以下のサードパーティ製ライブラリ、外部バイナリ、およびコンポーネントが含まれているか、またはそれらを利用しています。各コンポーネントの著作権およびライセンス条項は以下の通りです。

---

## 目次
1. [PyQt6 (GUIフレームワーク・Pythonバインディング)](#1-pyqt6)
2. [Qt 6 ライブラリ (GUIランタイム・共有ライブラリ)](#2-qt-6-ライブラリ)
3. [FFmpeg (動画エンコード・音声合成外部バイナリ)](#3-ffmpeg)
4. [pygame-ce 及び SDL2 関連ライブラリ](#4-pygame-ce-及び-sdl2-関連ライブラリ)
5. [NumPy 及び OpenBLAS](#5-numpy-及び-openblas)
6. [Pillow (PIL)](#6-pillow-pil)
7. [Mido (MIDIデータ解析)](#7-mido)
8. [Windows標準サウンドフォント (gm.dls) の取り扱いについて](#8-windows標準サウンドフォント-gmdls-の取り扱いについて)

---

## 1. PyQt6
* **コンポーネント名**: PyQt6 (Python bindings for Qt 6)
* **開発元 / 著作権**: Copyright (c) 2024 Riverbank Computing Limited
* **ライセンス**: GNU General Public License v3.0 (GPL v3)
* **公式サイト**: https://riverbankcomputing.com/software/pyqt/
* **概要**: Harmonica Visualizer のGUI構築、イベントハンドリング、OpenGL描画コンテキスト管理に使用されています。

---

## 2. Qt 6 ライブラリ
* **コンポーネント名**: Qt 6 Toolkit (QtCore, QtGui, QtWidgets, QtOpenGL, QtOpenGLWidgets, 関連プラットフォームプラグイン等)
* **開発元 / 著作権**: Copyright (C) 2024 The Qt Company Ltd. and other contributors.
* **ライセンス**: GNU Lesser General Public License version 3 (LGPL v3) / GNU General Public License version 3 (GPL v3)
* **公式サイト / ソースコード**: https://www.qt.io/ / https://code.qt.io/cgit/qt/qtbase.git
* **動的リンクおよびライブラリ置換について**:
  ポータブルZIP版において、Qtランタイムライブラリは `_internal/PyQt6/Qt6/bin/` および `_internal/PyQt6/Qt6/plugins/` 配下に独立した動的リンクライブラリ（DLL）として配置されています。利用者は LGPL v3 の規定に基づき、互換性のある Qt 共有ライブラリをご自身でリビルドし、同フォルダ内の DLL と差し替えて実行することが可能です。

---

## 3. FFmpeg
* **コンポーネント名**: FFmpeg (同梱実行ファイル: `ffmpeg.exe`, Gyan.FFmpeg 8.1.1-full_build)
* **開発元 / 著作権**: Copyright (c) 2000-2026 the FFmpeg developers
* **ビルド配布元**: Gyan Doshi (https://www.gyan.dev/ffmpeg/builds/)
* **ライセンス**: GNU General Public License version 3.0 (GPL v3)
  * ビルド構成: `--enable-gpl --enable-version3 --enable-static ... --enable-libx264 --enable-libx265 ...`
* **公式サイト / ソースコード**: https://ffmpeg.org/ / https://www.gyan.dev/ffmpeg/builds/
* **利用形態**:
  本ソフトウェアは、動画エクスポート（MP4 / MOV）および音声合成処理を行う際、同梱の `ffmpeg.exe` を外部プロセス（子プロセス）としてコマンドライン引数経由で独立起動（パイプライン連携）しています。FFmpeg のライブラリを静的にアプリ本体コードへ組み込んでいる構成ではありません。

---

## 4. pygame-ce 及び SDL2 関連ライブラリ
* **コンポーネント名**: pygame-ce (Python Game Engine - Community Edition)
* **開発元 / 著作権**:
  * Copyright (c) 2023-2024 pygame-ce developers
  * Copyright (c) 2000-2022 Pete Shinners, et al.
* **ライセンス**: GNU Lesser General Public License version 2.1 or later (LGPL v2.1+)
* **公式サイト**: https://pyga.me/
* **同梱の依存ライブラリ (SDL2)**:
  * SDL2 (Simple DirectMedia Layer): zlib License, Copyright (C) 1997-2024 Sam Lantinga
  * SDL2_mixer, SDL2_image, SDL2_ttf: zlib License
* **利用形態**: 低遅延音声再生およびミキサーバックエンドとして動的ライブラリ経由で利用されています。

---

## 5. NumPy 及び OpenBLAS
* **コンポーネント名**: NumPy
* **開発元 / 著作権**: Copyright (c) 2005-2024, NumPy Developers.
* **ライセンス**: BSD 3-Clause "New" or "Revised" License
* **公式サイト**: https://numpy.org/
* **同梱の依存ライブラリ (OpenBLAS)**:
  * OpenBLAS: BSD 3-Clause License, Copyright (c) 2011-2024, The OpenBLAS Project.
* **利用形態**: サウンドフォント（DLS）のPCM波形解析、高速周波数変換、DSP音声エフェクト処理に使用されています。

---

## 6. Pillow (PIL)
* **コンポーネント名**: Pillow
* **開発元 / 著作権**:
  * Copyright (c) 2010-2024 by Jeffrey A. Clark (Alex) and contributors
  * Copyright (c) 1995-2011 by Fredrik Lundh and contributors
* **ライセンス**: Historical Permission Notice and Disclaimer (HPND License)
* **公式サイト**: https://python-pillow.org/
* **利用形態**: スキン画像や背景画像のデコード・リサイズ前処理に使用されています。

---

## 7. Mido
* **コンポーネント名**: Mido (MIDI Objects for Python)
* **開発元 / 著作権**: Copyright (c) 2013-2024 Ole Martin Bjørndalen
* **ライセンス**: MIT License
* **公式サイト**: https://mido.readthedocs.io/
* **利用形態**: 標準MIDIファイル（SMF: Format 0 / 1）のトラック・テンポ・音符イベントの解析に使用されています。

---

## 8. Windows標準サウンドフォント (gm.dls) の取り扱いについて
* 本ソフトウェアの内蔵サンプラー（`GmDlsSampler`）は、実行時に利用環境の Windows OS 上に存在する `gm.dls` ファイル（`%SystemRoot%\System32\drivers\gm.dls` 等）を参照して動作します。
* `gm.dls` ファイル自体は、本ソフトウェアのソースコードおよび配布パッケージに**一切同梱・再配布していません**。
* 同ファイルの権利は各権利者に帰属し、本ソフトウェアの利用許諾によってその権利が移転または許諾されるものではありません。
* ファイルの存在や配置は利用環境によって異なる場合があります。そのため、ファイルを検出できない環境では、音源機能が利用できない、または制限される場合があります。

