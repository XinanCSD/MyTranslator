import logging
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QStatusBar, QVBoxLayout, QWidget,
)

from config import AUTO_TRANSLATE_MAX_CHARS, LANGUAGES, MODELS, PLACEHOLDER, save_model
from language_detector import detect_language
from model_manager import ModelManager

logger = logging.getLogger(__name__)


class TranslationWorker(QObject):
    finished = Signal(int, dict)
    failed = Signal(int, str)

    def __init__(self, manager, model_id, text, source, targets, generation):
        super().__init__()
        self.manager = manager
        self.model_id = model_id
        self.text = text
        self.source = source
        self.targets = targets
        self.generation = generation

    @Slot()
    def run(self):
        try:
            result = self.manager.translate_many(
                self.model_id, self.text, self.source, self.targets
            )
            self.finished.emit(self.generation, result)
        except Exception as exc:
            logger.exception("Translation worker failed")
            self.failed.emit(self.generation, str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyTranslator")
        self.resize(380, 380)
        self.clipboard = QApplication.clipboard()
        self.internal_clipboard_write = False
        self.last_processed_clipboard_text: Optional[str] = None
        self.last_detected_language = None
        self.last_edited_language = None
        self.translation_generation = 0
        self.worker_thread = None
        self.worker = None
        self._programmatic_update = False
        self.edits = {}
        self.model_manager = ModelManager()

        root = QWidget()
        layout = QVBoxLayout(root)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("模型："))
        self.model_combo = QComboBox()
        for model_id in self.model_manager.available_model_ids():
            self.model_combo.addItem(MODELS[model_id]["label"], model_id)
        initial = self.model_manager.initial_model_id()
        index = self.model_combo.findData(initial)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        model_row.addWidget(self.model_combo, 1)
        layout.addLayout(model_row)

        for lang, copy_text in (("zh", "复制"), ("en", "Copy"), ("ja", "コピー")):
            row = QHBoxLayout()
            row.addWidget(QLabel(LANGUAGES[lang]["label"]))
            row.addStretch(1)
            button = QPushButton(copy_text)
            button.clicked.connect(lambda _, l=lang: self.copy_all(l))
            row.addWidget(button)
            layout.addLayout(row)
            edit = QPlainTextEdit()
            edit.setMinimumHeight(50)
            edit.textChanged.connect(lambda l=lang: self.on_text_changed(l))
            self.edits[lang] = edit
            layout.addWidget(edit)

        controls = QHBoxLayout()
        self.auto_button = QPushButton("自动翻译：ON")
        self.auto_button.setCheckable(True)
        self.auto_button.setChecked(True)
        self.auto_button.clicked.connect(self.on_auto_toggled)
        self.translate_button = QPushButton("翻译")
        self.translate_button.clicked.connect(self.manual_translate)
        controls.addStretch(1)
        controls.addWidget(self.auto_button)
        controls.addWidget(self.translate_button)
        layout.addLayout(controls)

        self.setCentralWidget(root)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("状态：就绪")
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)

    def closeEvent(self, event):
        self.translation_generation += 1
        self._stop_worker(True)
        self.model_manager.close()
        super().closeEvent(event)

    def on_model_changed(self, index):
        model_id = self.model_combo.itemData(index)
        if not model_id:
            return
        self.translation_generation += 1
        self._stop_worker(True)
        self.model_manager.unload()
        save_model(model_id)
        self.status.showMessage(f"状态：已选择 {MODELS[model_id]['label']}，等待翻译")

    def on_auto_toggled(self, checked):
        self.auto_button.setText("自动翻译：ON" if checked else "自动翻译：OFF")

    @Slot()
    def on_clipboard_changed(self):
        if self.internal_clipboard_write:
            self.internal_clipboard_write = False
            return
        mime = self.clipboard.mimeData()
        if not mime or not mime.hasText():
            return
        text = mime.text()
        if not text.strip() or text == self.last_processed_clipboard_text:
            return
        self.last_processed_clipboard_text = text
        detection = detect_language(text, self.last_detected_language)
        logger.info(
            "Clipboard event received (length=%d, reliable=%s, language=%s)",
            len(text.strip()), detection.reliable, detection.language
        )
        if not detection.reliable or not detection.language:
            self.status.showMessage("状态：无法可靠判断语言，请编辑或手动翻译")
            return
        self.last_detected_language = detection.language
        self.last_edited_language = detection.language
        self._set_edit(detection.language, text)
        for lang in LANGUAGES:
            if lang != detection.language:
                self._set_edit(lang, PLACEHOLDER)
        if self.auto_button.isChecked() and len(text.strip()) <= AUTO_TRANSLATE_MAX_CHARS:
            self.start_translation(text, detection.language)
        else:
            self.status.showMessage("状态：已识别文本，等待翻译")

    def on_text_changed(self, lang):
        if self._programmatic_update:
            return
        self.last_edited_language = lang
        for other in LANGUAGES:
            if other != lang:
                self._set_edit(other, PLACEHOLDER)
        self.status.showMessage("状态：已编辑源文本，请点击“翻译”")

    def _set_edit(self, lang, text):
        self._programmatic_update = True
        try:
            self.edits[lang].setPlainText(text)
        finally:
            self._programmatic_update = False

    def copy_all(self, lang):
        text = self.edits[lang].toPlainText()
        self.internal_clipboard_write = True
        self.clipboard.setText(text)
        self.last_processed_clipboard_text = text
        self.status.showMessage(f"状态：已复制 {LANGUAGES[lang]['label']} 内容")

    def _resolve_source(self):
        if self.last_edited_language:
            text = self.edits[self.last_edited_language].toPlainText()
            if text.strip() and text.strip() != PLACEHOLDER:
                return self.last_edited_language, text
        for lang in LANGUAGES:
            text = self.edits[lang].toPlainText()
            if text.strip() and text.strip() != PLACEHOLDER:
                detection = detect_language(text, self.last_detected_language)
                if detection.reliable and detection.language:
                    return detection.language, text
        return None, ""

    def manual_translate(self):
        source, text = self._resolve_source()
        if not source or not text.strip():
            self.status.showMessage("状态：无法确定翻译源语言或源文本为空")
            return
        self.start_translation(text, source)

    def _translation_message(self, lang):
        return {
            "zh": "中文：翻译中......",
            "en": "translating......",
            "ja": "日本語：翻訳中......",
        }[lang]

    def start_translation(self, text, source):
        model_id = self.model_combo.currentData()
        if not model_id:
            self.status.showMessage("状态：未选择翻译模型")
            return
        self.translation_generation += 1
        generation = self.translation_generation
        self._stop_worker(True)
        targets = [l for l in LANGUAGES if l != source]
        for target in targets:
            self._set_edit(target, self._translation_message(target))
        self.status.showMessage(f"状态：正在加载 {MODELS[model_id]['label']} 并翻译……")

        thread = QThread(self)
        worker = TranslationWorker(
            self.model_manager, model_id, text, source, targets, generation
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._translation_finished)
        worker.failed.connect(self._translation_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda t=thread: self._worker_done(t))
        self.worker_thread = thread
        self.worker = worker
        thread.start()

    @Slot(int, dict)
    def _translation_finished(self, generation, result):
        if generation != self.translation_generation:
            return
        for lang, value in result.items():
            self._set_edit(lang, value)
        self.status.showMessage("状态：翻译完成")

    @Slot(int, str)
    def _translation_failed(self, generation, message):
        if generation != self.translation_generation:
            return
        self.status.showMessage("状态：翻译失败")
        QMessageBox.warning(self, "翻译失败", message)

    def _worker_done(self, thread):
        if self.worker_thread is thread:
            self.worker_thread = None
            self.worker = None

    def _stop_worker(self, wait):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            if wait:
                self.worker_thread.wait(5000)
        self.worker_thread = None
        self.worker = None
