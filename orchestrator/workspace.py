"""Safe read/write of generated projects, plus zipping for delivery."""
import zipfile
from pathlib import Path

import config


def project_dir(run_id: str) -> Path:
    d = config.WORKSPACE_DIR / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_files(run_id: str, files: dict) -> None:
    root = project_dir(run_id).resolve()
    for path, content in files.items():
        target = (root / path).resolve()
        if root not in target.parents:      # block absolute paths and ../ escapes
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def make_zip(run_id: str) -> Path:
    root = project_dir(run_id)
    zip_path = config.WORKSPACE_DIR / f"{run_id}.zip"
    skip = {"__pycache__", ".pytest_cache"}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in root.rglob("*"):
            if f.is_file() and not (skip & set(f.parts)) and f.suffix != ".db":
                z.write(f, f.relative_to(root))
    return zip_path
