"""One-time public model download; recording jobs themselves run offline."""
import argparse
from pathlib import Path
from huggingface_hub import snapshot_download

parser = argparse.ArgumentParser()
parser.add_argument("--model", choices=["tiny", "base", "small", "medium", "large-v3"], default="small")
parser.add_argument("--directory", required=True)
args = parser.parse_args()
path = Path(args.directory).resolve()
snapshot_download("Systran/faster-whisper-" + args.model, local_dir=str(path),
                  allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.*", "preprocessor_config.json"])
print("Local model ready:", path)
