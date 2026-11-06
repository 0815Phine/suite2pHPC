import os
import shutil
from os import listdir, rmdir
from os.path import join, isfile, isdir, dirname, abspath, splitext, exists
import subprocess
import yaml

# load parameters from the shared config file (same directory as this script)
config_path = join(dirname(abspath(__file__)), "parameters/config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# define paths
data_path = config["local_data_path"]        # folder with all raw .nd2 files
results_path = config["results_path"]         # folder for processed results
cluster_path = config["cluster_data_path"]    # per-recording folders on the cluster
analyzed_log_path = config["analyzed_log_path"]  # log of already-handled experiments
login_string = config["login_string"]
key_path = config["key_path"]
session_ids = config.get("session_ids", [])      # canonical session IDs (field 5)


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


def is_session_file(filename):
    """True if a raw file name follows the session convention
    animalID_date_time_sessionnum_sessionID, i.e. at least 5 fields
    with a known session ID in field 5. Test files / FOV images with
    other names are filtered out."""
    parts = splitext(filename)[0].split("_")
    return len(parts) >= 5 and parts[4] in session_ids


def processed_folder_name(stem):
    """Map a raw file stem (animalID_date_time_xxx) to its results folder
    name (animalID_xxx), i.e. drop the date and time fields."""
    parts = stem.split("_")
    return "_".join([parts[0]] + parts[4:])


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
        "\n 0: Only session files (animalID_date_time_sessionnum_sessionID) "
        "\n 1: Only session files that have not been analyzed before "
        "\n 2: All files in the raw data folder (including non-session files) "
        "\n 3: Specific files listed in a text file "
        "\n Select 0/1/2/3 >>> "
    ))

    if which == 0:
        selected_files = [f for f in raw_files if is_session_file(f)]
        skipped = [f for f in raw_files if not is_session_file(f)]
        if skipped:
            print("\n Skipping non-session files:")
            for f in skipped:
                print(f)

    elif which == 1:
        analyzed_stems = {splitext(x)[0] for x in read_name_list(analyzed_log_path)}
        selected_files = [f for f in raw_files
                          if is_session_file(f) and splitext(f)[0] not in analyzed_stems]
        skipped = [f for f in raw_files if not is_session_file(f)
                   and splitext(f)[0] not in analyzed_stems]
        if skipped:
            print("\n Skipping non-session files:")
            for f in skipped:
                print(f)

    elif which == 2:
        selected_files = raw_files

    elif which == 3:
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
        subprocess.run(["scp", "-i", key_path, join(data_path, f), f"{login_string}:{cluster_path}/{stem}"])
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
        dest = join(results_path, processed_folder_name(stem) + '_suite2p')
        # skip only folders that actually contain data (an empty dest is the
        # leftover of a previous failed attempt and will be retried); older
        # downloads with the nested suite2p/plane0 layout are left untouched
        if exists(dest) and listdir(dest):
            print(f"Suite2p data already exists for: {stem}")
            continue
        try:
            os.makedirs(dest, exist_ok=True)
            # download the suite2p output contents directly into dest (no extra
            # suite2p/ level), then flatten plane0/ up (single-plane runs), keeping
            # the plane's db.npy/settings.npy (the ones actually used by the run)
            subprocess.check_output(
                ["scp", "-i", key_path, "-r", f"{login_string}:{cluster_path}/{stem}/suite2p/*", dest]
            )
            plane0 = join(dest, "plane0")
            if isdir(plane0):
                for entry in listdir(plane0):
                    shutil.move(join(plane0, entry), join(dest, entry))
                rmdir(plane0)
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
