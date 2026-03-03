import numpy as np
import pytest
from app.services.extractor import _ssim_similar, _is_slide_like


def make_gray_frame(brightness: int = 200) -> np.ndarray:
    """Create a plain BGR image with uniform brightness."""
    return np.full((720, 1280, 3), brightness, dtype=np.uint8)


def test_identical_frames_are_similar():
    img = make_gray_frame(200)
    assert _ssim_similar(img, img, threshold=0.90) is True


def test_very_different_frames_not_similar():
    white = make_gray_frame(255)
    black = make_gray_frame(0)
    assert _ssim_similar(white, black, threshold=0.90) is False


def test_dark_frame_not_slide_like():
    dark = make_gray_frame(10)
    assert _is_slide_like(dark) is False


def test_plain_bright_frame_is_slide_like():
    bright = make_gray_frame(240)
    assert _is_slide_like(bright) is True