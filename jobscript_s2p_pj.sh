#!/bin/bash
#SBATCH --job-name=Suite2P_Analysis_JT
#SBATCH --output=Log_%j.out
#SBATCH --time=0:20:00
#SBATCH --partition=intelsr_short
#SBATCH --mem=250G
#SBATCH --account=ag_ukb_ieecr_beck
#SBATCH --ntasks=1 --nodes=1
#SBATCH --array=0-13

# read paths from the shared config file
CONFIG_FILE="parameters/config.yaml"
get_config() {
    grep -E "^$1:" "$CONFIG_FILE" | head -n1 | sed -E "s/^$1:[[:space:]]*//; s/[[:space:]]*#.*//; s/[[:space:]]*$//"
}
CLUSTER_DATA_PATH=$(get_config cluster_data_path)
CONDA_ENV_PATH=$(get_config conda_env_path)

# create a path list — only sessions that don't have finished results yet.
# spks.npy is the last output written by the pipeline, so a session with it is
# considered done; re-submitting the job then only analyzes new or previously
# failed sessions, and old results are never overwritten.
find "$CLUSTER_DATA_PATH" -mindepth 1 -maxdepth 1 -type d | while read -r d; do
    [ -f "$d/suite2p/plane0/spks.npy" ] || printf '%s\n' "$d"
done > dirs.txt
echo "Found $(wc -l < dirs.txt) session(s) without finished results"

# start environment
source ~/.bashrc
conda activate "$CONDA_ENV_PATH"

# pick this task's session
DIR=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" dirs.txt)
if [ -z "$DIR" ]; then
    echo "No session for task ID $SLURM_ARRAY_TASK_ID (dirs.txt has fewer entries)"
    exit 0
fi

# run python script
python run_cluster.py "$DIR"
