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