import logging
from config import MODEL_DIR,MODEL_ID
from huggingface_hub import snapshot_download
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s: %(message)s")
def main():
 MODEL_DIR.mkdir(parents=True,exist_ok=True); logging.info("Downloading/reusing model %s",MODEL_ID); snapshot_download(repo_id=MODEL_ID,local_dir=str(MODEL_DIR),resume_download=True); logging.info("Model is ready at %s",MODEL_DIR)
if __name__=="__main__": main()
