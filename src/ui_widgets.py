# -*- coding: utf-8 -*-
"""
src/ui_widgets.py
Harmonica Visualizer - 共通UIウィジェットおよびスタイルシート定義
- MODERN_DARK_STYLE: DAW仕様クラシックL型ダークモードスタイルシート
- HarmonicaSeekSlider: A-Bループ区間ハイライト描画対応カスタムシークスライダー
- MarqueeLabel: 電光掲示板風マーキー（自動スクロール）ラベル
- CollapsibleSection: アコーディオン風折りたたみセクションウィジェット
"""

import time
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QPoint, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QSlider, QLabel, QFrame, QPushButton, QVBoxLayout, QSizePolicy
)

MODERN_DARK_STYLE = f"""
QMainWindow {{
    background-color: #121215;
}}
QWidget {{
    color: #E0E0E6;
    font-family: 'Meiryo UI', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 11px;
}}
QFrame#panelFrame {{
    background-color: #18181D;
    border: 1px solid #282832;
    border-radius: 8px;
}}
QFrame#groupFrame {{
    background-color: #1C1C23;
    border: 1px solid #2A2A38;
    border-radius: 6px;
    padding: 4px;
}}
QFrame#lcdFrame {{
    background-color: #090C10;
    border: 1px solid #1E2836;
    border-radius: 6px;
    padding: 2px 8px;
}}
QLabel#lcdText {{
    color: #38BDF8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    font-weight: bold;
}}
QLabel#lcdStatus {{
    color: #34D399;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    font-weight: bold;
}}
QLabel#groupHeader {{
    color: #38BDF8;
    font-size: 11px;
    font-weight: bold;
}}
QLabel#statusMsg {{
    color: #FBBF24;
    font-size: 11px;
    font-weight: bold;
}}
QPushButton {{
    background-color: #262630;
    color: #F0F0F5;
    border: 1px solid #363645;
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #343444;
    border-color: #4A4A60;
}}
QPushButton:pressed {{
    background-color: #1C1C24;
    border-color: #00BFFF;
}}
QPushButton#playBtn {{
    background-color: #006699;
    border-color: #0099DD;
    font-size: 12px;
    padding: 4px 14px;
}}
QPushButton#playBtn:hover {{
    background-color: #0088CC;
    border-color: #33BBFF;
}}
QPushButton#stopBtn {{
    background-color: #3A2020;
    border-color: #553030;
}}
QPushButton#stopBtn:hover {{
    background-color: #552828;
    border-color: #883A3A;
}}
QPushButton#recBtn {{
    background-color: #4A1515;
    border-color: #7A2525;
    color: #FFAAAA;
}}
QPushButton#recBtn:hover {{
    background-color: #6A1D1D;
    border-color: #AA3030;
}}
QPushButton#actionBtn {{
    background-color: #1E3A5F;
    border-color: #2E5C8A;
}}
QPushButton#actionBtn:hover {{
    background-color: #28507E;
    border-color: #3E7DBA;
}}
QPushButton#futureBtn {{
    background-color: #222228;
    color: #888899;
    border: 1px dashed #444455;
}}
QPushButton#futureBtn:hover {{
    background-color: #2A2A33;
    color: #AAAAFF;
    border-color: #666688;
}}
QComboBox {{
    background-color: #22222A;
    color: #FFFFFF;
    border: 1px solid #343442;
    border-radius: 4px;
    padding: 2px 20px 2px 6px;
    min-width: 48px;
}}
QComboBox:hover {{
    border-color: #00BFFF;
}}
QComboBox:disabled {{
    background-color: #16161D;
    color: #555566;
    border-color: #262632;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #2D2D3A;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
    background-color: #1E1E26;
}}
QComboBox::drop-down:hover {{
    background-color: #282836;
}}
QComboBox::drop-down:disabled {{
    background-color: #14141A;
    border-left-color: #1E1E26;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #94A3B8;
    width: 0px;
    height: 0px;
}}
QComboBox::down-arrow:hover {{
    border-top-color: #38BDF8;
}}
QComboBox::down-arrow:disabled {{
    border-top-color: #444455;
}}
QComboBox QAbstractItemView {{
    background-color: #1A1A22;
    border: 1px solid #383848;
    selection-background-color: #0088CC;
    color: #FFFFFF;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: #22222A;
    color: #FFFFFF;
    border: 1px solid #343442;
    border-radius: 4px;
    padding: 2px 4px;
    font-weight: bold;
    font-size: 11px;
}}
QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: #00BFFF;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: #38BDF8;
    background-color: #1A1A24;
}}
QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: #16161D;
    color: #555566;
    border-color: #262632;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    width: 0px;
    height: 0px;
    border: none;
}}
QLineEdit {{
    background-color: #22222A;
    color: #FFFFFF;
    border: 1px solid #343442;
    border-radius: 4px;
    padding: 2px 6px;
}}
QLineEdit:hover {{
    border-color: #00BFFF;
}}
QLineEdit:disabled {{
    background-color: #16161D;
    color: #555566;
    border-color: #262632;
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: #252530;
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: #0099DD;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 1px solid #888888;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: #00E5FF;
    border-color: #FFFFFF;
}}
QLabel:disabled {{
    color: #555566;
}}
QCheckBox {{
    spacing: 5px;
    color: #C0C0D0;
}}
QCheckBox:disabled {{
    color: #555566;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #444455;
    background-color: #202028;
}}
QCheckBox::indicator:checked {{
    background-color: #0099DD;
    border-color: #00BFFF;
}}
QCheckBox::indicator:disabled {{
    background-color: #16161D;
    border-color: #262632;
}}
QTabWidget::pane {{
    border: 1px solid #282835;
    background-color: #16161C;
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: #202028;
    color: #A0A0B0;
    padding: 6px 12px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-weight: bold;
    font-size: 11px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: #16161C;
    color: #38BDF8;
    border-bottom: 2px solid #00BFFF;
}}
QTabBar::tab:hover:!selected {{
    background-color: #282835;
    color: #FFFFFF;
}}
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QLabel#badgeLabel {{
    background-color: #0F2A1D;
    color: #00E676;
    border: 1px solid #165338;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 10px;
}}
QToolTip {{
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #38BDF8;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}
"""


class HarmonicaSeekSlider(QSlider):
    """A-Bループ区間ハイライト描画対応のカスタムシークスライダー"""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.loop_a_ratio = None
        self.loop_b_ratio = None
        self.loop_enabled = False

    def set_loop_range(self, a_ratio: float, b_ratio: float, enabled: bool = True):
        self.loop_a_ratio = a_ratio
        self.loop_b_ratio = b_ratio
        self.loop_enabled = enabled
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.loop_enabled and self.loop_a_ratio is not None and self.loop_b_ratio is not None:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            w = self.width()
            h = self.height()
            margin = 7
            track_w = max(1, w - margin * 2)
            xa = margin + max(0.0, min(1.0, self.loop_a_ratio)) * track_w
            xb = margin + max(0.0, min(1.0, self.loop_b_ratio)) * track_w
            if xb > xa:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(0, 229, 255, 60))
                p.drawRoundedRect(QRectF(xa, h * 0.5 - 3, xb - xa, 6), 3, 3)

                p.setPen(QPen(QColor("#00E5FF"), 2))
                p.drawLine(QPointF(xa, h * 0.5 - 7), QPointF(xa, h * 0.5 + 7))
                p.setPen(QPen(QColor("#FFD700"), 2))
                p.drawLine(QPointF(xb, h * 0.5 - 7), QPointF(xb, h * 0.5 + 7))
            p.end()


class MarqueeLabel(QLabel):
    """
    電光掲示板（マーキースクロール）対応ステータスラベル
    - 表示枠に収まる場合は静止表示
    - 表示枠を超える長文の場合:
      1. 先頭で約1.6秒静止
      2. 左へスムーズにスクロール
      3. 末尾で約1.2秒静止
      4. 最大2周スクロール後、先頭位置に戻って自動停止（静止）
      5. 停止中にマウスを乗せるとスクロールを再開
      6. setTextで新しい文言が設定されたら周回カウントをリセットして再判定
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = ""
        self._scroll_x = 0.0
        self._loop_count = 0
        self._max_loops = 2
        self._is_stopped = False
        self._state = "idle"
        self._pause_frames = 0
        self._padding_x = 8

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._on_tick)

        if text:
            self.setText(text)

    def setText(self, text: str):
        self._full_text = str(text) if text is not None else ""
        self._scroll_x = 0.0
        self._loop_count = 0
        self._is_stopped = False
        self._state = "pause_start"
        self._pause_frames = 55  # 55 * 30ms ≈ 1.65秒
        super().setText("")  # super側を空文字にしてQLabel既定のテキスト描画を抑止
        self.setToolTip(self._full_text)
        self._check_overflow()
        self.update()

    def text(self) -> str:
        return self._full_text

    def _check_overflow(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._full_text)
        avail_w = max(1, self.width() - self._padding_x * 2)
        if text_w > avail_w:
            if not self._is_stopped and not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self._scroll_x = 0.0
            self._state = "idle"

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._check_overflow()

    def enterEvent(self, event):
        super().enterEvent(event)
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._full_text)
        avail_w = max(1, self.width() - self._padding_x * 2)
        if text_w > avail_w:
            if self._is_stopped:
                # 2周完了して停止している場合、マウスホバーでスクロール再開！
                self._is_stopped = False
                self._loop_count = 0
                self._scroll_x = 0.0
                self._state = "pause_start"
                self._pause_frames = 20  # ホバー時は少し短めの待機
                if not self._timer.isActive():
                    self._timer.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)

    def _on_tick(self):
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self._full_text)
        avail_w = max(1, self.width() - self._padding_x * 2)

        if text_w <= avail_w:
            self._scroll_x = 0.0
            self._timer.stop()
            self._state = "idle"
            self.update()
            return

        max_scroll = text_w - avail_w + 14

        if self._state == "pause_start":
            self._pause_frames -= 1
            if self._pause_frames <= 0:
                self._state = "scrolling"

        elif self._state == "scrolling":
            self._scroll_x += 1.2
            if self._scroll_x >= max_scroll:
                self._scroll_x = max_scroll
                self._state = "pause_end"
                self._pause_frames = 40  # 末尾で約1.2秒待機

        elif self._state == "pause_end":
            self._pause_frames -= 1
            if self._pause_frames <= 0:
                self._loop_count += 1
                if self._loop_count >= self._max_loops:
                    # 2周完了：先頭に戻して停止
                    self._is_stopped = True
                    self._scroll_x = 0.0
                    self._timer.stop()
                    self._state = "idle"
                else:
                    # 2周目へ
                    self._scroll_x = 0.0
                    self._state = "pause_start"
                    self._pause_frames = 40

        self.update()

    def paintEvent(self, event):
        # スタイルシートの背景・角丸・枠線を描画
        super().paintEvent(event)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip_rect = self.rect().adjusted(self._padding_x, 1, -self._padding_x, -1)
        p.setClipRect(clip_rect)

        font = self.font()
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#FBBF24"))

        fm = p.fontMetrics()
        text_y = int((self.height() + fm.ascent() - fm.descent()) / 2)
        text_x = self._padding_x - int(self._scroll_x)

        p.drawText(text_x, text_y, self._full_text)
        p.end()


class CollapsibleSection(QFrame):
    """タイトル行クリックで中身を1行に最小化・展開できるアコーディオンフレーム"""
    def __init__(self, title: str, content_frame: QWidget, expanded: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("groupFrame")
        self.setMaximumWidth(328)
        self._title = title
        self._content = content_frame
        self._expanded = expanded

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.btn_toggle = QPushButton(self)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(expanded)
        self.btn_toggle.setFlat(True)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                color: #E2E8F0;
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #38BDF8;
            }
        """)
        self.btn_toggle.toggled.connect(self._on_toggled)
        layout.addWidget(self.btn_toggle)

        # 内部フレームの二重枠線を消してスッキリ収容
        self._content.setStyleSheet("QFrame#groupFrame { border: none; background: transparent; }")
        layout.addWidget(self._content)
        self._on_toggled(expanded)

    def _on_toggled(self, checked: bool):
        self._expanded = checked
        arrow = "▼" if checked else "▶"
        self.btn_toggle.setText(f"{arrow}  {self._title}")
        self._content.setVisible(checked)


