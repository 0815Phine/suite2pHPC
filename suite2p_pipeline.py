import sys

import s2p_nd2

# cluster entry point: one recording folder is passed as the first argument
# (see jobscript_s2p_pj.sh, which runs this once per directory in a SLURM array).
config = s2p_nd2.load_config()

datapath = sys.argv[1]
s2p_nd2.run_folder(datapath, config["suite2p"], preprocess=config.get("preprocess"))
