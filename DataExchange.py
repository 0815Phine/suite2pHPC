import os
from os import listdir
from os.path import join, isfile, dirname, abspath, splitext, exists
import subprocess
import yaml

# load parameters from the shared config file (same directory as this script)
config_path = join(dirname(abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# define paths
data_path = config["local_data_path"]        # folder with all raw .nd2 files
results_path = config["results_path"]         # folder for processed results
cluster_path = config["cluster_data_path"]    # per-recording folders on the cluster
analyzed_log_path = config["analyzed_log_path"]  # log of already-handled experiments
login_string = config["login_string"]


# --- helpers ------------------------------------------------

def read_name_list(path):
    """Return the non-empty, stripped lines of a plain-text file (or [])."""
    if not exists(path):
        return []
    with open(path, "r") as fh:
        return [line.strip() for line in fh if line.strip()]


def append_names(path, names):
    """Append names to a plain-text file, one per line."""
    with open(path, "a") as fh:
        for name in names:
            fh.write(name + "\n")


def processed_folder_name(stem):
    """Map a raw file stem (animalID_date_time_xxx) to its results folder
    name (animalID_xxx), i.e. drop the date and time fields."""
    parts = stem.split("_")
    return "_".join([parts[0]] + parts[3:])


# --- gather local + cluster state ---------------------------

# all raw .nd2 files in the raw data folder
raw_files = sorted(
    f for f in listdir(data_path)
    if isfile(join(data_path, f)) and f.lower().endswith(".nd2")
)

# folders currently on the cluster (each named after a raw file stem)
print("\n Retrieving information from the cluster...")
result = subprocess.run(["ssh", "marvin", "'ls'", f"'{cluster_path}'"], capture_output=True)
cluster_folders = [e.strip() for e in result.stdout.decode("UTF-8").split("\n") if e.strip()]
print(f"{len(cluster_folders)} recording folder(s) currently on the cluster.")

todo = int(input(
    "\n What do you want to do? "
    "\n 0: Upload data to cluster "
    "\n 1: Download results from cluster "
    "\n 2: Delete data/results from cluster "
    "\n Select 0/1/2 >>> "
))


### Upload Functionality
if todo == 0:
    which = int(input(
        "\n Which files do you want to upload? "
        "\n 0: All files in the raw data folder "
        "\n 1: Only files that have not been analyzed before "
        "\n 2: Specific files listed in a text file "
        "\n Select 0/1/2 >>> "
    ))

    if which == 0:
        selected_files = raw_files

    elif which == 1:
        analyzed_stems = {splitext(x)[0] for x in read_name_list(analyzed_log_path)}
        selected_files = [f for f in raw_files if splitext(f)[0] not in analyzed_stems]

    elif which == 2:
        list_path = input("\n Path to the text file listing the file names >>> ").strip().strip('"')
        wanted_stems = {splitext(x)[0] for x in read_name_list(list_path)}
        selected_files = [f for f in raw_files if splitext(f)[0] in wanted_stems]

    else:
        selected_files = []

    print("\n The following files will be uploaded:")
    for f in selected_files:
        print(f)

    # make directories and copy
    print("\n Uploading now...")
    uploaded = []
    for f in selected_files:
        stem = splitext(f)[0]
        if stem in cluster_folders:
            print(f"Already on cluster, skipping: {stem}")
            continue
        subprocess.run(["ssh", "marvin", "'mkdir'", f"'{cluster_path}/{stem}'"])
        print(f"Created directory for: {stem}")
        subprocess.run(["scp", join(data_path, f), f"{login_string}:{cluster_path}/{stem}"])
        print(f"Copied nd2 file into {stem}")
        uploaded.append(f)

    # keep the analyzed-experiments log up to date
    if uploaded:
        already_logged = set(read_name_list(analyzed_log_path))
        new_entries = [f for f in uploaded if f not in already_logged]
        if new_entries:
            append_names(analyzed_log_path, new_entries)
            print(f"\n Added {len(new_entries)} entry/entries to {analyzed_log_path}")


### Download Functionality
elif todo == 1:
    print("\n Downloading now...")
    for stem in cluster_folders:
        dest = join(results_path, processed_folder_name(stem))
        if exists(join(dest, "suite2p")):
            print(f"Suite2p data already exists for: {stem}")
            continue
        try:
            os.makedirs(dest, exist_ok=True)
            subprocess.check_output(
                ["scp", "-r", f"{login_string}:{cluster_path}/{stem}/suite2p", dest]
            )
            print(f"Copied suite2p data into {dest}")
        except subprocess.CalledProcessError:
            print(f"No suite2p results for: {stem}")


### Delete Functionality
elif todo == 2:
    sure = input(
        f"\n Are you sure you want to delete ALL {len(cluster_folders)} "
        f"recording folder(s) on the cluster :( ? (yes/no) >>>"
    )
    if sure.lower() == "yes":
        for stem in cluster_folders:
            subprocess.run(["ssh", "marvin", "'rm'", "'-r'", f"'{cluster_path}/{stem}'"])
            print(f"Deleted folder for: {stem}")
    else:
        print("Phew!")

else:
    pass
