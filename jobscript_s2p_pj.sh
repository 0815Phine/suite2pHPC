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

# define paths
#dir_count=$(find /lustre/scratch/data/jtim_hpc-2PAnalysis -mindepth 1 -maxdepth 1 -type d | wc -l)
#paths=$(find /lustre/scratch/data/jtim_hpc-2PAnalysis -mindepth 1 -maxdepth 1 -type d)

# create a path list
find /lustre/scratch/data/jtim_hpc-2PAnalysis -mindepth 1 -maxdepth 1 -type d > dirs.txt

# load relevant module (distribution of python)
#module load Miniforge3

# start environment
source ~/.bashrc
conda activate /home/jtim_hpc/.conda/envs/suite2p

# create task IDs
DIR=$(sed -n "$((SLURM_ARRAY_TASK_ID+1))p" dirs.txt)

# run python script
python Suite2P_Pipeline.py "$DIR"
