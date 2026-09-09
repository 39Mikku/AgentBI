import hashlib
import os
from pathlib import Path


def get_instance_id() -> str:
    """Identify a checkout using its canonical path without returning the path."""
    root = str(Path(__file__).resolve().parents[2]).replace("\\", "/").rstrip("/")
    if os.name == "nt":
        root = root.lower()
    return "sha256:" + hashlib.sha256(root.encode("utf-8")).hexdigest()


INSTANCE_ID = get_instance_id()


if __name__ == "__main__":
    print(INSTANCE_ID)
