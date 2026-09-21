import logging
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

from config import MODELS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def download_nllb():
    info = MODELS["nllb_600m"]
    target = Path(info["model_dir"])
    target.mkdir(parents=True, exist_ok=True)
    logging.info("Downloading/reusing NLLB model %s", info["model_id"])
    snapshot_download(repo_id=info["model_id"], local_dir=str(target), resume_download=True)


def download_translategemma():
    info = MODELS["translategemma_4b_q4km"]
    target = Path(info["model_dir"])
    target.mkdir(parents=True, exist_ok=True)
    logging.info("Downloading/reusing TranslateGemma %s", info["model_repo"])
    hf_hub_download(
        repo_id=info["model_repo"],
        filename=info["model_file"],
        local_dir=str(target),
        resume_download=True,
    )


def main():
    download_nllb()
    download_translategemma()
    logging.info("Model files are ready on disk.")


if __name__ == "__main__":
    main()
