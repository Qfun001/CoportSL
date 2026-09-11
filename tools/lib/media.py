"""Generate videos and puzzles from existing images."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .cancel import throw_if_cancelled


def make_video(
    *,
    images: list[Path],
    output: Path,
    fps: float = 30.0,
    max_size: tuple[int, int] | None = None,
    canvas_size: tuple[int, int] | None = None,
    cancel_file: Path | None = None,
) -> Path:
    """Encoding video; the original image can be put into a fixed canvas in equal proportions without cropping or stretching."""
    try:
        import cv2
    except ImportError as exc:
        raise ImportError("Video output requires opencv-python.") from exc

    paths = [Path(path) for path in images]
    output = Path(output)
    if not paths:
        raise ValueError("No images provided for video.")
    if not output.is_absolute() or any(not path.is_absolute() for path in paths):
        raise ValueError("Video input and output paths must be absolute.")
    if fps <= 0.0:
        raise ValueError("fps must be greater than zero.")
    if max_size is not None and (max_size[0] <= 0 or max_size[1] <= 0):
        raise ValueError("max_size values must be greater than zero.")
    if canvas_size is not None and (
            canvas_size[0] <= 0 or canvas_size[1] <= 0):
        raise ValueError("canvas_size values must be greater than zero.")

    throw_if_cancelled(cancel_file)
    first = cv2.imread(str(paths[0]))
    if first is None:
        raise ValueError(f"Cannot read video frame: {paths[0]}")
    height, width = first.shape[:2]
    if canvas_size is not None:
        target = (
            max(2, int(canvas_size[0]) // 2 * 2),
            max(2, int(canvas_size[1]) // 2 * 2),
        )
    elif max_size is None:
        scale = 1.0
        target = (
            max(2, int(width * scale) // 2 * 2),
            max(2, int(height * scale) // 2 * 2),
        )
    else:
        scale = min(max_size[0] / width, max_size[1] / height, 1.0)
        target = (
            max(2, int(width * scale) // 2 * 2),
            max(2, int(height * scale) // 2 * 2),
        )

    suffix = output.suffix.lower()
    if suffix == ".mp4":
        codec = cv2.VideoWriter_fourcc(*"mp4v")
    elif suffix == ".avi":
        codec = cv2.VideoWriter_fourcc(*"XVID")
    else:
        raise ValueError("Video output must end in .mp4 or .avi")

    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), codec, fps, target)
    if not writer.isOpened():
        raise RuntimeError(f"Cannot create video: {output}")
    try:
        for path in paths:
            throw_if_cancelled(cancel_file)
            image = cv2.imread(str(path))
            if image is None:
                raise ValueError(f"Cannot read video frame: {path}")
            size = (image.shape[1], image.shape[0])
            if max_size is None and canvas_size is None and \
                    size != (width, height):
                raise ValueError(f"Video image size does not match first image: {path}")
            if canvas_size is not None:
                scale = min(target[0] / size[0], target[1] / size[1])
                fitted = (
                    max(2, int(size[0] * scale) // 2 * 2),
                    max(2, int(size[1] * scale) // 2 * 2),
                )
                if size != fitted:
                    interpolation = cv2.INTER_AREA if scale < 1.0 \
                        else cv2.INTER_CUBIC
                    image = cv2.resize(
                        image, fitted, interpolation=interpolation)
                canvas = np.zeros((target[1], target[0], 3), dtype=np.uint8)
                x0 = (target[0] - fitted[0]) // 2
                y0 = (target[1] - fitted[1]) // 2
                canvas[y0:y0 + fitted[1], x0:x0 + fitted[0]] = image
                image = canvas
            elif size != target:
                image = cv2.resize(image, target, interpolation=cv2.INTER_AREA)
            writer.write(image)
    finally:
        writer.release()
    throw_if_cancelled(cancel_file)
    return output


def make_montage(
    *,
    images: list[Path],
    output: Path,
    columns: int,
    labels: list[str] | None = None,
    dpi: int = 300,
) -> Path:
    """Arrange existing figures in a regular grid."""
    paths = [Path(path) for path in images]
    output = Path(output)
    if not paths:
        raise ValueError("No images provided for montage.")
    if not output.is_absolute() or any(not path.is_absolute() for path in paths):
        raise ValueError("Montage input and output paths must be absolute.")
    if columns <= 0:
        raise ValueError("Montage column count must be greater than zero.")
    if labels is not None and len(labels) != len(paths):
        raise ValueError("Montage labels must match the number of images.")

    rows = (len(paths) + columns - 1) // columns
    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(6.0 * columns, 6.0 * rows),
        dpi=dpi,
        squeeze=False,
    )
    for index, axis in enumerate(axes.ravel()):
        axis.axis("off")
        if index >= len(paths):
            continue
        axis.imshow(plt.imread(paths[index]))
        if labels is not None:
            axis.set_title(labels[index], fontsize=14)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    plt.close(figure)
    return output
