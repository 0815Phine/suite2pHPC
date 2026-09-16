# Suite2P on HPC

This repository contains information on how to set up an analysis pipeline with Suize2P on Marvin.

# Setup Instructions

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
The next step is to copy the files config.yaml, jobscript_s2p_pj.sh and suite2p_pipeline.py to the Marvin home directory
1) Dowload the files from this repository.
2) Open a new terminal and copy the files from your computer to your Marvin home directory via:

```scp /path/to/file [USERNAME]@marvin.hpc.uni-bonn.de:/home/[USERNAME]```

Now, ssh back into Marvin, check if the files are in your home directory (```ls -all```).

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

### STEP 7: Copy the results to your local device.
For this you can use the dataexchange.py
