"""Ripple noise removal — Python port of MATLAB RippleNoiseRemoval.m.

Removes periodic ripple artifacts from 2-photon imaging data by detecting
bright spikes in the log-amplitude 2D FFT of each frame and zeroing them out.
"""
import numpy as np


def remove_ripple_noise(
    movie: np.ndarray,
    amplitude_threshold: float,
    win: int,
) -> np.ndarray:
    """Remove periodic ripple noise from a (T, Ly, Lx) movie.

    For each frame:
      1. 2D FFT (zero-frequency centered via fftshift)
      2. log-amplitude spectrum
      3. threshold to find ripple spikes in frequency domain
      4. mask the DC center (window of half-size ``win``)
      5. zero out spike frequencies
      6. inverse FFT, take magnitude

    Parameters:
        movie: (T, Ly, Lx) array, int16 or float.
        amplitude_threshold: log-amplitude threshold for spike detection.
        win: half-size of the DC mask window in pixels.

    Returns:
        Filtered movie, same shape and dtype as input.
    """
    T, Ly, Lx = movie.shape
    filtered = np.empty_like(movie)
    cy, cx = Ly // 2, Lx // 2

    for t in range(T):
        frame = movie[t].astype(np.float64)
        F = np.fft.fftshift(np.fft.fft2(frame))
        amplitude = np.log(np.abs(F) + 1e-12)
        spikes = amplitude > amplitude_threshold
        spikes[cy - win:cy + win + 1, cx - win:cx + win + 1] = False
        F[spikes] = 0
        filtered[t] = np.abs(np.fft.ifft2(np.fft.ifftshift(F)))

    return filtered.astype(movie.dtype)
