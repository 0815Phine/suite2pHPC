"""Run the suite2p pipeline on the cluster (SLURM) for one recording folder.

Launched by jobscript_s2p_pj.sh, which passes one recording folder per array task
as the first argument. Must run inside the suite2p conda env:

    python run_cluster.py <RECORDING_DIR>
"""
import os
import sys

# the pipeline source module (s2p_nd2) lives in src/ next to this script
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import s2p_nd2

# cluster entry point: one recording folder is passed as the first argument
# (see jobscript_s2p_pj.sh, which runs this once per directory in a SLURM array).
config = s2p_nd2.load_config()

datapath = sys.argv[1]
s2p_nd2.run_folder(datapath, config["suite2p"], preprocess=config.get("preprocess"))
