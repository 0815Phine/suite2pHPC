"""Compatibility shim for running the Treadwall pipeline on the refactored suite2p.

Two things changed in the updated suite2p that broke the pipeline:

1. Readers now use the signature ``fn(dbs, settings, reg_file, reg_file_chan2)`` and write
   into pre-opened file handles, but the installed ``io.nd2_to_binary`` still has the old
   single-argument signature (so ``input_format="nd2"`` raises ``TypeError`` and the GUI
   dropped the nd2 option). ``nd2_to_binary`` below re-implements it against the new contract,
   counting ``nframes`` ONCE per frame so two-channel data is not double-counted.
2. ``run_s2p`` now takes ``(db, settings)`` with a nested ``settings`` dict instead of a flat
   ``ops``. ``run`` migrates the flat ``config.yaml`` overrides into that structure using
   suite2p's own ``convert_settings_orig`` and launches the pipeline.
"""
import gc
import glob
import importlib
import os
import time

import numpy as np
import nd2
import yaml
from suite2p import default_db, default_settings

# NB: `import suite2p.run_s2p as s2p` would bind the *function* run_s2p, because
# suite2p/__init__.py rebinds the `run_s2p` attribute. Import the module explicitly.
s2p = importlib.import_module("suite2p.run_s2p")


def _compute_mid_frequency_fraction(pc1_spatial, r_low_frac=0.03, r_high_frac=0.25):
    """Compute fraction of power in the mid-frequency band of a 2D pattern.

    Mid frequencies capture periodic artifacts (resonant scanning stripes)
    while excluding DC and very low frequencies (smooth structures: blobs, gradients).

    Parameters:
        pc1_spatial: 2D array (Ly, Lx)
        r_low_frac: lower radius bound as fraction of min(Ly, Lx) (default 0.03)
        r_high_frac: upper radius bound as fraction of min(Ly, Lx) (default 0.25)

    Returns:
        Fraction of total power in the mid-frequency band (0.0 to 1.0).
        Stripes ~1.0, blobs/gradients ~0.0-0.5, random noise ~0.2-0.8.
    """
    Ly, Lx = pc1_spatial.shape
    fft = np.fft.fft2(pc1_spatial.astype(np.float64))
    power = np.abs(fft) ** 2
    power_shifted = np.fft.fftshift(power)

    h, w = power_shifted.shape
    cy, cx = h // 2, w // 2

    yy, xx = np.meshgrid(np.arange(h) - cy, np.arange(w) - cx, indexing="ij")
    dist = np.sqrt(xx**2 + yy**2)

    r_low = r_low_frac * min(Ly, Lx)
    r_high = r_high_frac * min(Ly, Lx)

    total_power = power_shifted.sum()
    if total_power == 0:
        return 0.0

    mid_mask = (dist >= r_low) & (dist < r_high)
    mid_power = power_shifted[mid_mask].sum()

    return mid_power / total_power


def _remove_pc1_noise(im_func, n_sample=500, mid_freq_threshold=0.8):
    """Conditionally remove PC1 from a (T, Y, X) movie.

    Returns (denoised_movie, pc1_removed, mid_freq_fraction, variance_explained).
    PC1 is removed if its spatial component has high mid-frequency power fraction,
    indicating a periodic artifact (resonant scanning stripes).
    On any error, returns the original movie unchanged.
    """
    T, Ly, Lx = im_func.shape
    try:
        from sklearn.decomposition import PCA
        idx = np.linspace(0, T - 1, min(n_sample, T)).astype(int)
        sample = im_func[idx].reshape(len(idx), -1).astype(np.float64)

        sample_centered = sample - sample.mean(axis=0)
        pca = PCA(n_components=1, svd_solver="randomized", random_state=0)
        pca.fit(sample_centered)

        var_explained = pca.explained_variance_ratio_[0]
        pc1_spatial = pca.components_[0].reshape(Ly, Lx)

        mid_frac = _compute_mid_frequency_fraction(pc1_spatial)

        if mid_frac <= mid_freq_threshold:
            return im_func, False, mid_frac, var_explained

        # Remove PC1 from ALL frames
        pc1 = pca.components_[0]
        mean = sample.mean(axis=0)
        full = im_func.reshape(T, -1).astype(np.float64)
        full_centered = full - mean
        full_denoised = full_centered - np.outer(full_centered @ pc1, pc1)
        full_denoised += mean

        denoised = np.clip(full_denoised, -32768, 32767).astype(np.int16).reshape(T, Ly, Lx)
        return denoised, True, mid_frac, var_explained
    except Exception as e:
        print(f"  preprocess warning: PC1 removal failed ({e}), keeping original data",
              flush=True)
        return im_func, False, 0.0, 0.0


def load_config(start_dir=None):
    """Load config.yaml, looking in parameters/ (repo layout) then the script dir (flat)."""
    start_dir = start_dir or os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(start_dir, "parameters", "config.yaml"),
        os.path.join(start_dir, "config.yaml"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r") as f:
                return yaml.safe_load(f)
    raise FileNotFoundError(f"config.yaml not found in any of: {candidates}")


def nd2_to_binary(dbs, settings, reg_file, reg_file_chan2):
    """Read .nd2 files and write them into suite2p's binaries (new reader contract)."""
    t0 = time.time()
    fs = dbs[0]["file_list"]
    first_files = np.asarray(dbs[0]["first_files"])
    nplanes, nchannels = dbs[0]["nplanes"], dbs[0]["nchannels"]
    which_folder = -1

    for ifile, file in enumerate(fs):
        with nd2.ND2File(file) as f:
            dims = {k: i for i, k in enumerate(f.sizes)}
            assert set(dims) <= set("TZCYX"), f"unknown dims {set(dims)} in {file}"
            im = f.asarray().transpose([dims[x] for x in "TZCYX" if x in dims])
        for i, d in enumerate("TZC"):  # expand missing dims -> (T, Z, C, Y, X)
            if d not in dims:
                im = np.expand_dims(im, i)
        assert im.max() < 32768 and im.min() >= -32768, "image data out of int16 range"
        im = im.astype(np.int16)

        if first_files[ifile]:
            which_folder += 1
        if ifile == 0:
            Ly, Lx = im.shape[3], im.shape[4]
            for j in range(nplanes):
                dbs[j].update(Ly=Ly, Lx=Lx, nframes=0,
                              frames_per_file=np.zeros(len(fs), "int"),
                              frames_per_folder=np.zeros(int(first_files.sum()), "int"),
                              meanImg=np.zeros((Ly, Lx), "float64"))
                if nchannels > 1:
                    dbs[j]["meanImg_chan2"] = np.zeros((Ly, Lx), "float64")

        for j in range(nplanes):
            nfunc = dbs[j]["functional_chan"] - 1 if nchannels > 1 else 0
            imk = np.ascontiguousarray(im[:, j, nfunc, :, :])

            preproc = dbs[j].get("preprocess") or {}
            if preproc.get("remove_pc1", False):
                imk, removed, mid_frac, var_expl = _remove_pc1_noise(
                    imk,
                    n_sample=preproc.get("pca_sample_frames", 500),
                    mid_freq_threshold=preproc.get("pc1_mid_freq_threshold", 0.8),
                )
                threshold = preproc.get("pc1_mid_freq_threshold", 0.8)
                if removed:
                    status = f"PC1 removed (mid-freq {mid_frac:.2f} > {threshold})"
                else:
                    status = f"PC1 kept (mid-freq {mid_frac:.2f}, below {threshold})"
                print(f"  preprocess plane {j}: {status} (variance: {var_expl:.1%})", flush=True)

            reg_file[j].write(bytearray(imk))
            dbs[j]["meanImg"] += imk.sum(axis=0).astype("float64")
            dbs[j]["nframes"] += imk.shape[0]  # counted ONCE (functional channel)
            dbs[j]["frames_per_file"][ifile] += imk.shape[0]
            dbs[j]["frames_per_folder"][which_folder] += imk.shape[0]
            if nchannels > 1:
                imk2 = np.ascontiguousarray(im[:, j, 1 - nfunc, :, :])
                reg_file_chan2[j].write(bytearray(imk2))
                dbs[j]["meanImg_chan2"] += imk2.sum(axis=0).astype("float64")

        print(f"  {file}: {im.shape[0]} frames/plane ({time.time() - t0:.1f}s)", flush=True)
        del im
        gc.collect()

    for db in dbs:
        db["meanImg"] /= db["nframes"]
        if nchannels > 1:
            db["meanImg_chan2"] /= db["nframes"]
        np.save(db["db_path"], db)
        np.save(db["settings_path"], settings)
    for j in range(nplanes):
        reg_file[j].close()
        if nchannels > 1:
            reg_file_chan2[j].close()
    return dbs


def _deep_merge(base, override):
    """Recursively merge ``override`` into ``base`` (nested dicts) and return base."""
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def run(datapath, s2p_config, save_path0=None, file_list=None):
    """Patch nd2, merge the config's db/settings over suite2p defaults, and run suite2p.

    ``s2p_config`` is the ``suite2p:`` section of config.yaml, with ``db`` and ``settings``
    sub-dicts matching the suite2p 1.1.0 structure. By default every file found in
    ``datapath`` is combined into one analysis; pass ``file_list=["name.nd2"]`` to restrict
    to a single file and ``save_path0`` to place its output. Use ``run_folder`` for the
    usual "one session per file" behaviour.
    """
    s2p.files_to_binary["nd2"] = nd2_to_binary  # install the migrated nd2 reader

    db = _deep_merge(default_db(), s2p_config.get("db"))
    settings = _deep_merge(default_settings(), s2p_config.get("settings"))

    db["data_path"] = [datapath]
    db["save_path0"] = save_path0 or datapath
    if file_list is not None:
        db["file_list"] = list(file_list)
    return s2p.run_s2p(db=db, settings=settings)


def run_folder(datapath, s2p_config):
    """Analyse every input file in ``datapath`` as a SEPARATE session (never combined).

    Works for both layouts:
    - one file per folder (cluster; folders run as parallel SLURM tasks) -> output in
      ``datapath/suite2p`` (matches the existing per-recording folder convention);
    - several files in one folder (local) -> each file gets its own
      ``datapath/<filestem>/suite2p`` so different sessions stay separate.
    """
    fmt = (s2p_config.get("db") or {}).get("input_format", "nd2")
    patterns = {"nd2": ["*.nd2"], "tif": ["*.tif", "*.tiff"],
                "h5": ["*.h5", "*.hdf5"]}.get(fmt, [f"*.{fmt}"])
    files = sorted(f for p in patterns for f in glob.glob(os.path.join(datapath, p)))
    if not files:
        raise FileNotFoundError(f"no {fmt} files found in {datapath}")

    print(f"Found {len(files)} {fmt} file(s) in {datapath}; analysing each separately.",
          flush=True)
    results = []
    for f in files:
        name = os.path.basename(f)
        stem = os.path.splitext(name)[0]
        save_path0 = datapath if len(files) == 1 else os.path.join(datapath, stem)
        print(f"\n=== session {name} -> {os.path.join(save_path0, 'suite2p')} ===", flush=True)
        results.append(run(datapath, s2p_config, save_path0=save_path0, file_list=[name]))
    return results
