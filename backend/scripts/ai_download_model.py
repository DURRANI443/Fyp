"""Explicit one-time model artifact download; runtime inference remains local."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from huggingface_hub import snapshot_download

from app.ai.retrieval import MODEL_ID, MODEL_PATH, MODEL_REVISION


if __name__ == "__main__":
    snapshot_download(
        MODEL_ID, revision=MODEL_REVISION, local_dir=MODEL_PATH,
        allow_patterns=["*.json", "*.txt", "*.safetensors", "1_Pooling/*", "README.md"],
        ignore_patterns=["onnx/*", "openvino/*"],
    )
    (MODEL_PATH / "project-model-metadata.json").write_text(json.dumps({
        "model": MODEL_ID, "revision": MODEL_REVISION, "license": "Apache-2.0", "inference": "local CPU",
    }, indent=2), encoding="utf-8")
    print(f"Model cached at {MODEL_PATH}. Restart the backend to activate local embeddings.")
