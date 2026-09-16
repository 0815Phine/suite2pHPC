import suite2p
import sys
import os
import yaml

# load parameters from the shared config file (same directory as this script)
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# define paths
# workspace directory
datapath = sys.argv[1:][0]

# load default settings and apply the overrides from config.yaml
ops = suite2p.default_ops()
ops.update(config["suite2p"])

# path related parameters
db = {
    'data_path': [datapath],
    'save_path0': [],
}

# run suite2p
output_ops = suite2p.run_s2p(ops=ops, db=db)
