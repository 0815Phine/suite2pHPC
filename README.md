# Suite2P on HPC

This repository contains information on how to set up an analysis pipeline with Suite2P on Marvin.

## Setup Instructions

These instructions assume you have already:
- gained access to Marvin
- created SSH credentials (see https://wiki.hpc.uni-bonn.de/gaining_access)

### STEP 1: Initialize Anaconda in your Marvin home directory
Once logged into Marvin, perform the following three commands:

```module load Miniforge3``` (-> this is a free Anaconda clone)

```conda init``` (to initialize Anaconda)

```source ~/.bashrc``` (to tell the current bash terminal it should update to use Anaconda)

You should now see the typical conda (base) appear on the left of the current terminal line.

### STEP 2: Upload the jobscript, pipeline and config file to your Marvin home directory.
The next step is to copy the jobscript, the cluster entry point, and the two folders they read from (`src/` containing `s2p_nd2.py` and `parameters/` containing `config.yaml`) to the Marvin home directory.
1) Download the files from this repository and open a terminal in the `code/` directory.
2) Copy everything in one go — `src` and `parameters` are transferred as folders, so the structure on the cluster mirrors the repository:

```scp -r jobscript_s2p_pj.sh run_cluster.py src parameters [USERNAME]@marvin.hpc.uni-bonn.de:/home/[USERNAME]```

Now, ssh back into Marvin, check if the files are in your home directory (```ls -all```). You should see `jobscript_s2p_pj.sh`, `run_cluster.py`, `src/` and `parameters/` there.

### STEP 3: Install Suite2P in your Marvin home directory
To install Suite2P locally in your home directory you can now follow the instructions given by Suite2P ()

```conda create --name suite2p python=3.11```

```conda activate suite2p```

```python -m pip install suite2p```

Additionally you have to install the nd2 package for reading .nd2 files in the environment.
```pip install nd2```

### STEP 4: Create a workspace on the cluster to store your project data.
Still on the cluster, outside the environment create a workspace to put the imaging data that you want to analyse:

```ws_allocate NAME DURATION```

(for example: ```ws_allocate Suite2PAnalysis 90``` -> 90 means the workspace will be available for 90 days, then it will be automatically deleted. Don't worry, workspace durations can be extended and you can also just create new ones -> https://wiki.hpc.uni-bonn.de/en/marvin/workspaces)

### STEP 5: Copy the imaging files to Marvin.
For this you can use the file dataexchange.py 

### STEP 6: Run Suite2P
The SLURM job is set up to analyze all available files on the cluster in parallel. Therefore within the SLURM job the number #SBATCH --array has to be consistent with files on the cluster. For example if you have 8 imaging files on the cluster (all in their respective folder in the workspace), #SBATCH --array has to be set to 0-7.
You can also adapt the job-name and account if needed.

To start the job, within the home directory run:

```sbatch jobscript_s2p_pj.sh```

You should get the message that your SLURM job was submitted.
Once the slurm job is running, for each slurm job a log file is generated: Log_jobid.out

You can also check the status of the jobs (multiple jobs because they are running in parallel) on the cluster by running:

```squeue --me```

### STEP 7: Copy the results to your local device.
For this you can use the dataexchange.py

## General Tip

Your home directory might get a bit cluttered if you do not delete the .out files after the jobs are done. Each file that you analyze will generate one of these, so they add up quickly.
To delete the files, run:

```rm Log*```

This command will remove all files that begin with the Log.

## Troubleshooting

### Config file not found on the cluster

If the job fails with an error about `config.yaml` not being found, the script is looking in the wrong directory. The job script must `cd` to its own directory and reference `parameters/config.yaml`:

```bash
cd "$(dirname "$0")"
CONFIG_FILE="parameters/config.yaml"
```

### ImportError: libxcb.so.1 / libGL.so.1: cannot open shared object file

These errors mean `opencv-python` (the GUI build) is installed but the cluster lacks X11/OpenGL system libraries. Suite2p runs headless, so use the headless OpenCV build instead:

```bash
conda activate suite2p
pip uninstall opencv-python opencv-python-headless -y
pip install opencv-python-headless
```

This is a one-time fix — the change persists in the conda environment. Do not add it to the job script.

### sbatch error: Batch script contains DOS line breaks (\r\n)

If you see this error when submitting the job:
```
sbatch: error: Batch script contains DOS line breaks (\r\n)
sbatch: error: instead of expected UNIX line breaks (\n).
```

The job script was saved with Windows line endings. Fix it on the cluster with:
```bash
sed -i 's/\r$//' jobscript_s2p_pj.sh
```
Then resubmit with `sbatch jobscript_s2p_pj.sh`.
