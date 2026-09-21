import logging
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import QApplication,QHBoxLayout,QLabel,QMainWindow,QMessageBox,QPlainTextEdit,QPushButton,QStatusBar,QVBoxLayout,QWidget
from config import AUTO_TRANSLATE_MAX_CHARS,LANGUAGES,PLACEHOLDER
from language_detector import detect_language
from translator import TranslationError,TranslatorService
logger=logging.getLogger(__name__)
class TranslationWorker(QObject):
    finished=Signal(int,dict,object); failed=Signal(int,str)
    def __init__(self,service,text,source,targets,generation): super().__init__(); self.service=service; self.text=text; self.source=source; self.targets=targets; self.generation=generation
    @Slot()
    def run(self):
        try:
            if self.service is None:
                self.service = TranslatorService()
            result = self.service.translate_many(self.text,self.source,self.targets)
            self.finished.emit(self.generation,result,self.service)
        except Exception as exc:
            logger.exception("Translation worker failed")
            self.failed.emit(self.generation,str(exc))
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("MyTranslator"); self.resize(760,760); self.clipboard=QApplication.clipboard(); self.internal_clipboard_write=False; self.last_processed_clipboard_text:Optional[str]=None; self.last_detected_language=None; self.last_edited_language=None; self.translation_generation=0; self.worker_thread=None; self.worker=None; self.service=None; self._programmatic_update=False; self.edits={}
        root=QWidget(); layout=QVBoxLayout(root)
        for lang,copy_text in (("zh","复制"),("en","Copy"),("ja","コピー")):
            row=QHBoxLayout(); row.addWidget(QLabel(LANGUAGES[lang]["label"])); row.addStretch(1); b=QPushButton(copy_text); b.clicked.connect(lambda _,l=lang:self.copy_all(l)); row.addWidget(b); layout.addLayout(row)
            edit=QPlainTextEdit(); edit.setMinimumHeight(150); edit.textChanged.connect(lambda l=lang:self.on_text_changed(l)); self.edits[lang]=edit; layout.addWidget(edit)
        controls=QHBoxLayout(); self.auto_button=QPushButton("自动翻译：ON"); self.auto_button.setCheckable(True); self.auto_button.setChecked(True); self.auto_button.clicked.connect(self.on_auto_toggled); self.translate_button=QPushButton("翻译"); self.translate_button.clicked.connect(self.manual_translate); controls.addStretch(1); controls.addWidget(self.auto_button); controls.addWidget(self.translate_button); layout.addLayout(controls)
        self.setCentralWidget(root); self.status=QStatusBar(); self.setStatusBar(self.status); self.status.showMessage("状态：就绪"); self.clipboard.dataChanged.connect(self.on_clipboard_changed)
    def closeEvent(self,event): self.translation_generation+=1; self._stop_worker(True); super().closeEvent(event)
    def on_auto_toggled(self,checked): self.auto_button.setText("自动翻译：ON" if checked else "自动翻译：OFF")
    @Slot()
    def on_clipboard_changed(self):
        if self.internal_clipboard_write: self.internal_clipboard_write=False; return
        mime=self.clipboard.mimeData()
        if not mime or not mime.hasText(): return
        text=mime.text()
        if not text.strip() or text==self.last_processed_clipboard_text: return
        self.last_processed_clipboard_text=text; detection=detect_language(text,self.last_detected_language)
        logger.info("Clipboard event received (length=%d, reliable=%s, language=%s)",len(text.strip()),detection.reliable,detection.language)
        if not detection.reliable or not detection.language: self.status.showMessage("状态：无法可靠判断语言，请编辑或手动翻译"); return
        self.last_detected_language=detection.language; self.last_edited_language=detection.language; self._set_edit(detection.language,text)
        for lang in LANGUAGES:
            if lang!=detection.language:self._set_edit(lang,PLACEHOLDER)
        if self.auto_button.isChecked() and len(text.strip())<=AUTO_TRANSLATE_MAX_CHARS:self.start_translation(text,detection.language)
        else:self.status.showMessage("状态：已识别文本，等待翻译")
    def on_text_changed(self,lang):
        if self._programmatic_update:return
        self.last_edited_language=lang
        for other in LANGUAGES:
            if other!=lang:self._set_edit(other,PLACEHOLDER)
        self.status.showMessage("状态：已编辑源文本，请点击“翻译”")
    def _set_edit(self,lang,text):
        self._programmatic_update=True
        try:self.edits[lang].setPlainText(text)
        finally:self._programmatic_update=False
    def copy_all(self,lang):
        text=self.edits[lang].toPlainText(); self.internal_clipboard_write=True; self.clipboard.setText(text); self.last_processed_clipboard_text=text; self.status.showMessage(f"状态：已复制 {LANGUAGES[lang]['label']} 内容")
    def _resolve_source(self):
        if self.last_edited_language:
            text=self.edits[self.last_edited_language].toPlainText()
            if text.strip() and text.strip()!=PLACEHOLDER:return self.last_edited_language,text
        for lang in LANGUAGES:
            text=self.edits[lang].toPlainText()
            if text.strip() and text.strip()!=PLACEHOLDER:
                d=detect_language(text,self.last_detected_language)
                if d.reliable and d.language:return d.language,text
        return None,""
    def manual_translate(self):
        source,text=self._resolve_source()
        if not source or not text.strip():self.status.showMessage("状态：无法确定翻译源语言或源文本为空"); return
        self.start_translation(text,source)
    def _translation_message(self,lang):return {"zh":"中文：翻译中......","en":"translating......","ja":"日本語：翻訳中......"}[lang]
    def start_translation(self,text,source):
        self.translation_generation+=1; generation=self.translation_generation; self._stop_worker(False); targets=[l for l in LANGUAGES if l!=source]
        for target in targets:self._set_edit(target,self._translation_message(target))
        self.status.showMessage("状态：正在加载模型并翻译……" if self.service is None else "状态：正在翻译……")
        thread=QThread(self); worker=TranslationWorker(self.service,text,source,targets,generation); worker.moveToThread(thread); thread.started.connect(worker.run); worker.finished.connect(self._translation_finished); worker.failed.connect(self._translation_failed); worker.finished.connect(thread.quit); worker.failed.connect(thread.quit); thread.finished.connect(worker.deleteLater); thread.finished.connect(thread.deleteLater); thread.finished.connect(lambda t=thread:self._worker_done(t)); self.worker_thread=thread; self.worker=worker; thread.start()
    def _ensure_service(self):
        if self.service is not None:return True
        try:self.status.showMessage("状态：正在加载翻译模型……"); self.service=TranslatorService(); self.status.showMessage("状态：就绪"); return True
        except TranslationError as exc:self.status.showMessage(f"状态：{exc}"); QMessageBox.critical(self,"模型加载失败",str(exc)); return False
    @Slot(int,dict,object)
    def _translation_finished(self,generation,result,service):
        if generation!=self.translation_generation:return
        if self.service is None:
            self.service = service
        for lang,value in result.items():self._set_edit(lang,value)
        self.status.showMessage("状态：翻译完成")
    @Slot(int,str)
    def _translation_failed(self,generation,message):
        if generation!=self.translation_generation:return
        self.status.showMessage("状态：翻译失败"); QMessageBox.warning(self,"翻译失败",message)
    def _worker_done(self,thread):
        if self.worker_thread is thread:self.worker_thread=None; self.worker=None
    def _stop_worker(self,wait):
        if self.worker_thread and self.worker_thread.isRunning():
            self.translation_generation+=1; self.worker_thread.quit()
            if wait:self.worker_thread.wait(5000)
        self.worker_thread=None; self.worker=None
