"""Shared normalization for production-image errors and spatial residuals."""

from __future__ import annotations

import numpy as np


def image_error_terms(
    image: np.ndarray,
    reference: np.ndarray,
) -> tuple[np.ndarray, float]:
    """Returns the four-component sum of absolute differences and the shared reference total I."""
    value = np.asarray(image, dtype=np.float64)
    target = np.asarray(reference, dtype=np.float64)
    if value.shape != target.shape or value.ndim < 1 or value.shape[0] != 4:
        raise ValueError("Stokes images must have equal shape (4, ...).")
    numerator = np.sum(
        np.abs(value - target),
        axis=tuple(range(1, value.ndim)),
    )
    denominator = float(np.sum(np.abs(target[0])))
    if (
        not np.all(np.isfinite(numerator))
        or not np.isfinite(denominator)
        or denominator <= 0.0
    ):
        raise ValueError(
            "Stokes image error terms require finite values and positive reference I.")
    return numerator, denominator


def image_error(image: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Use the reference image's total Stokes I as the shared $L_1$ denominator for I/Q/U/V."""
    numerator, denominator = image_error_terms(image, reference)
    result = numerator / denominator
    if not np.all(np.isfinite(result)):
        raise ValueError("Stokes image error is non-finite.")
    return result


def temporal_mean_std(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Calculate the arithmetic mean and sample standard deviation of frame-by-frame errors along the first axis."""
    errors = np.asarray(values, dtype=np.float64)
    if errors.ndim == 0 or errors.shape[0] == 0:
        raise ValueError("Temporal error statistics require at least one frame.")
    if not np.all(np.isfinite(errors)) or np.any(errors < 0.0):
        raise ValueError("Temporal error statistics require finite non-negative values.")
    mean = np.mean(errors, axis=0)
    if errors.shape[0] == 1:
        std = np.full_like(mean, np.nan, dtype=np.float64)
    else:
        std = np.std(errors, axis=0, ddof=1)
    return mean, std


def peak_i_residual(image: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Pixel-wise spatial residuals are normalized by the peak Stokes I of the entire reference image."""
    value = np.asarray(image, dtype=np.float64)
    target = np.asarray(reference, dtype=np.float64)
    if value.shape != target.shape or value.ndim < 1 or value.shape[0] != 4:
        raise ValueError("Stokes images must have equal shape (4, ...).")
    denominator = float(np.max(np.abs(target[0])))
    if not np.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("Reference peak Stokes I must be finite and positive.")
    result = (value - target) / denominator
    if not np.all(np.isfinite(result)):
        raise ValueError("Stokes spatial residual is non-finite.")
    return result
