#!/bin/bash
#SBATCH --job-name=Suite2P_Analysis_JT
#SBATCH --output=Log_%j.out
#SBATCH --time=0:20:00
#SBATCH --partition=intelsr_devel
#SBATCH --mem=250G
#SBATCH --account=ag_ukb_ieecr_beck
#SBATCH --exclusive
#SBATCH --ntasks=1 --nodes=1
#SBATCH --array=0-13

# read paths from the shared config file
CONFIG_FILE="config.yaml"
get_config() {
    grep -E "^$1:" "$CONFIG_FILE" | head -n1 | sed -E "s/^$1:[[:space:]]*//; s/[[:space:]]*#.*//; s/[[:space:]]*$//"
}
CLUSTER_DATA_PATH=$(get_config cluster_data_path)
CONDA_ENV_PATH=$(get_config conda_env_path)

# create a path list
find "$CLUSTER_DATA_PATH" -mindepth 1 -maxdepth 1 -type d > dirs.txt

# start environment
source ~/.bashrc
conda activate "$CONDA_ENV_PATH"

# create task IDs
DIR=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" dirs.txt)

# run python script
python suite2p_pipeline.py "$DIR"
