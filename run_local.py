"""Run the suite2p pipeline locally on one folder of .nd2 files.

Uses the same config.yaml and nd2 shim as the cluster pipeline. Must run inside the
suite2p conda env, e.g.:

    C:/Users/TomBombadil/anaconda3/envs/suite2p/python.exe code/run_local.py [DATAPATH]

DATAPATH defaults to the local test folder when omitted.
"""
import sys

import s2p_nd2

config = s2p_nd2.load_config()

datapath = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/TomBombadil/Desktop/test"
s2p_nd2.run_folder(datapath, config["suite2p"], preprocess=config.get("preprocess"))
