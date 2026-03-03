"""
Core slide-extraction pipeline.
All heavy work lives here; the worker calls this with progress callbacks.
"""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import yt_dlp
from PIL import Image
from reportlab.lib.pagesizes import landscape
from reportlab.pdfgen import canvas
from skimage.metrics import structural_similarity as ssim

log = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]   # (pct, stage_name)


# ── 1. Download ──────────────────────────────────────────────────────────────

def download_video(url: str, work_dir: Path, on_progress: ProgressCallback) -> tuple[Path, str]:
    on_progress(0, "download")
    log.info("Downloading %s", url)

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=720]/best[ext=mp4]/best",
        "outtmpl": str(work_dir / "lecture.%(ext)s"),
        "quiet": True,
        "progress_hooks": [lambda d: _ydl_hook(d, on_progress)],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        ext = info.get("ext", "mp4")
        title = info.get("title", "slides")          # ← capture title

    video_path = work_dir / f"lecture.{ext}"
    if not video_path.exists():
        raise FileNotFoundError(f"Downloaded video missing: {video_path}")

    log.info("Download complete: %s | title: %s", video_path, title)
    on_progress(25, "download")
    return video_path, title                          # ← return tuple

def _ydl_hook(d: dict, cb: ProgressCallback) -> None:
    if d.get("status") == "downloading":
        pct_str = d.get("_percent_str", "0%").strip().rstrip("%")
        try:
            raw = min(float(pct_str), 100.0)
            cb(int(raw * 0.25), "download")   # download = 0–25 % of total
        except ValueError:
            pass


# ── 2. Extract frames ────────────────────────────────────────────────────────

def extract_frames(video_path: Path, work_dir: Path,
                   interval_sec: float, on_progress: ProgressCallback) -> list[Path]:
    on_progress(25, "extracting_frames")
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    step = max(1, int(fps * interval_sec))

    saved: list[Path] = []
    idx = 0
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            break
        p = frames_dir / f"frame_{idx:08d}.jpg"
        cv2.imwrite(str(p), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        saved.append(p)
        # progress 25–55 %
        on_progress(25 + int((idx / total_frames) * 30), "extracting_frames")
        idx += step

    cap.release()
    log.info("Extracted %d frames", len(saved))
    on_progress(55, "extracting_frames")
    return sorted(saved)


# ── 3. Detect slides ─────────────────────────────────────────────────────────

def _ssim_similar(a: np.ndarray, b: np.ndarray, threshold: float) -> bool:
    h, w = 180, 320
    ga = cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (w, h))
    gb = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (w, h))
    score, _ = ssim(ga, gb, full=True)
    return float(score) >= threshold


def _is_slide_like(img: np.ndarray) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if float(gray.mean()) < 30:
        return False
    edges = cv2.Canny(gray, 50, 150)
    return (np.count_nonzero(edges) / edges.size) < 0.15


def detect_slides(frame_paths: list[Path], threshold: float,
                  min_run: int, on_progress: ProgressCallback) -> list[Path]:
    on_progress(55, "detecting_slides")
    if not frame_paths:
        return []

    slides: list[Path] = []
    prev = cv2.imread(str(frame_paths[0]))
    run_start = 0
    n = len(frame_paths)

    for i, path in enumerate(frame_paths[1:], start=1):
        curr = cv2.imread(str(path))
        if curr is None:
            continue
        if not _ssim_similar(prev, curr, threshold):
            run_len = i - run_start
            if run_len >= min_run:
                mid = frame_paths[(run_start + i) // 2]
                mid_img = cv2.imread(str(mid))
                if mid_img is not None and _is_slide_like(mid_img):
                    slides.append(mid)
                    log.debug("Slide %d at frame index %d", len(slides), run_start)
            run_start = i
        prev = curr
        on_progress(55 + int((i / n) * 30), "detecting_slides")

    # Final run
    if n - run_start >= min_run:
        mid = frame_paths[(run_start + n) // 2]
        mid_img = cv2.imread(str(mid))
        if mid_img is not None and _is_slide_like(mid_img):
            slides.append(mid)

    log.info("Detected %d unique slides", len(slides))
    on_progress(85, "detecting_slides")
    return slides


# ── 4. Build PDF ─────────────────────────────────────────────────────────────

def build_pdf(slide_paths: list[Path], output_pdf: Path,
              on_progress: ProgressCallback) -> int:
    on_progress(85, "building_pdf")
    if not slide_paths:
        log.warning("No slides to write.")
        return 0

    pw, ph = landscape((1280, 720))
    c = canvas.Canvas(str(output_pdf), pagesize=(pw, ph))
    total = len(slide_paths)

    for n, path in enumerate(slide_paths, 1):
        img = Image.open(str(path)).convert("RGB")
        iw, ih = img.size
        scale = min(pw / iw, ph / ih)
        dw, dh = iw * scale, ih * scale
        c.drawImage(str(path), (pw - dw) / 2, (ph - dh) / 2, width=dw, height=dh)
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(6, 5, f"Slide {n} / {total}")
        c.showPage()
        on_progress(85 + int((n / total) * 14), "building_pdf")

    c.save()
    mb = output_pdf.stat().st_size / 1_048_576
    log.info("PDF saved: %s (%.1f MB, %d slides)", output_pdf, mb, total)
    on_progress(100, "building_pdf")
    return total