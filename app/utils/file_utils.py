import re
import shutil
import tempfile
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def temp_workdir():
    """Context manager that creates and auto-removes a temporary directory."""
    path = tempfile.mkdtemp(prefix="yt_slides_")
    try:
        yield Path(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


def slugify(text: str, max_len: int = 100) -> str:
    """
    Convert a video title to a safe filename.
    e.g. "Lecture 3: Intro to ML (2024)" → "Lecture_3_Intro_to_ML_2024"
    """
    text = text.strip()
    text = re.sub(r"[^\w\s-]", "", text)       # remove special chars
    text = re.sub(r"[\s-]+", "_", text)         # spaces/hyphens → underscore
    text = text.strip("_")
    return text[:max_len] or "slides"            # cap length, fallback