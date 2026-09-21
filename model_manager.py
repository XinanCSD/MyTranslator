import gc
import logging
import sys

from config import MODELS, default_model_id, load_saved_model, save_model
from translator import TranslationError, TranslatorService

logger = logging.getLogger(__name__)


class ModelManager:
    """Owns the single active translation backend."""

    def __init__(self):
        self.active_model_id = None
        self.service = None

    def available_model_ids(self):
        return [
            model_id
            for model_id, info in MODELS.items()
            if sys.platform in info["platforms"]
        ]

    def initial_model_id(self):
        saved = load_saved_model()
        available = self.available_model_ids()
        if saved in available:
            return saved
        default = default_model_id()
        return default if default in available else available[0]

    def load(self, model_id):
        if self.active_model_id == model_id and self.service is not None:
            return self.service

        self.unload()
        try:
            self.service = TranslatorService(model_id)
            self.active_model_id = model_id
            save_model(model_id)
            logger.info("Active translation model: %s", model_id)
            return self.service
        except Exception:
            self.service = None
            self.active_model_id = None
            gc.collect()
            raise

    def translate_many(self, model_id, text, source_lang, targets):
        service = self.load(model_id)
        return service.translate_many(text, source_lang, targets)

    def unload(self):
        service, self.service = self.service, None
        self.active_model_id = None
        if service is not None:
            try:
                service.close()
            except Exception:
                logger.exception("Failed to close translation backend")
        gc.collect()

    def close(self):
        self.unload()
