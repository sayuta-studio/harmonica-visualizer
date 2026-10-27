import os
import sys
import unittest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

# モーダルブロック抑止
QMessageBox.information = staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
QMessageBox.warning = staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

from main import HarmonicaMainWindow
import harmonica_map

class TestV320Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.win = HarmonicaMainWindow()

    def test_01_orthogonal_note_naming(self):
        """Micro-Step 1: 音名直交化"""
        # lang_combo に「なし」が含まれず「ドレミ」「CDE」の2択
        items = [self.win.lang_combo.itemText(i) for i in range(self.win.lang_combo.count())]
        self.assertNotIn("なし", items)
        self.assertIn("ドレミ", items)
        self.assertIn("CDE", items)

        # combo_grid4 に「非表示」が含まれる
        grid_items = [self.win.combo_grid4.itemText(i) for i in range(self.win.combo_grid4.count())]
        self.assertIn("非表示", grid_items)

        # show_grid4 プロパティ
        self.win.combo_grid4.setCurrentText("非表示")
        self.assertEqual(self.win.gl_widget.show_grid4, "非表示")
        self.win.combo_grid4.setCurrentText("1音表示 (従来)")
        self.assertEqual(self.win.gl_widget.show_grid4, "1音表示 (従来)")

    def test_02_title_stretch(self):
        """Micro-Step 2: 曲名タイトル伸縮"""
        policy = self.win.lbl_song_title.sizePolicy()
        self.assertTrue(policy.horizontalPolicy().name == "Expanding" or self.win.lbl_song_title.maximumWidth() > 1000)

    def test_03_design_preset_sync(self):
        """Micro-Step 3: デザインタブのプリセット直結＆同期"""
        self.assertTrue(hasattr(self.win, "w_design_preset_bar"))
        self.assertTrue(hasattr(self.win, "combo_design_preset"))

        # 動画ターゲット切替で表示
        self.win.combo_visual_target.setCurrentIndex(1)  # 🎬 動画出力プリセット
        self.assertFalse(self.win.w_design_preset_bar.isHidden())

        # 練習ターゲット切替で非表示
        self.win.combo_visual_target.setCurrentIndex(0)  # 🎹 練習画面スタイル
        self.assertTrue(self.win.w_design_preset_bar.isHidden())

        # プリセット同期
        presets = [self.win.combo_design_preset.itemText(i) for i in range(self.win.combo_design_preset.count())]
        if len(presets) > 1:
            self.win.combo_design_preset.setCurrentIndex(1)
            self.assertEqual(self.win.combo_design_preset.currentText(), self.win.combo_video_preset.currentText())

    def test_04_practice_audio_switch(self):
        """Micro-Step 4: 練習時の再生音源ワンタッチ切替"""
        self.assertTrue(hasattr(self.win, "combo_prac_audio_mode"))
        self.assertTrue(hasattr(self.win, "lbl_prac_ext_status"))

        # 練習側変更 -> 外部音源側同期
        self.win.combo_prac_audio_mode.setCurrentText("ガイド音のみ (伴奏ミュート)")
        self.assertEqual(self.win.combo_ext_mode.currentText(), "ガイド音のみ (伴奏ミュート)")

        self.win.combo_ext_mode.setCurrentText("伴奏 ＋ ガイド音 (両方再生)")
        self.assertEqual(self.win.combo_prac_audio_mode.currentText(), "伴奏 ＋ ガイド音 (両方再生)")

    def test_05_record_take_selection(self):
        """Micro-Step 5: 録音テイク選択"""
        self.assertTrue(hasattr(self.win, "btn_select_rec_take"))
        self.assertTrue(hasattr(self.win, "_on_select_rec_take"))

    def test_06_rec_sync_audition(self):
        """Micro-Step 6: 録音ズレ補正＆同期試聴"""
        self.assertTrue(hasattr(self.win, "btn_rec_sync_audition"))
        self.assertTrue(hasattr(self.win, "_sync_rec_take_playback"))
        self.assertTrue(hasattr(self.win, "_on_rec_offset_adjust"))

        # 微調整
        cur_val = self.win.spin_rec_offset.value()
        self.win._on_rec_offset_adjust(10)
        self.assertEqual(self.win.spin_rec_offset.value(), cur_val + 10)
        self.win._on_rec_offset_adjust(-10)
        self.assertEqual(self.win.spin_rec_offset.value(), cur_val)

    def test_07_window_title_version(self):
        """Micro-Step 7: ウィンドウタイトル v3.2.0"""
        self.assertIn("v3.2.0", self.win.windowTitle())

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestV320Features)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
