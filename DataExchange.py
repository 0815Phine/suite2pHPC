import os
from os import listdir
from os.path import join, isfile, isdir
import subprocess
import re

# define paths
data_path = "R:/JosephineTimm"
results_path = "//ieekf-fs1/home/timmjo/Animals/"
cluster_path = "/lustre/scratch/data/jtim_hpc-2PAnalysis"
login_string = "jtim_hpc@marvin.hpc.uni-bonn.de"

# get cohorts
print("The following cohorts are available:")
cohorts = [f for f in listdir(data_path) if isdir(join(data_path, f))]

# print cohorts
for item in range(len(cohorts)):
    print(f"{item}: {cohorts[item]}")

# pick cohort
command = int(input("Which cohort? >>>"))

# get animals
cohort_path = join(data_path,cohorts[command])
animals = [f for f in listdir(cohort_path) if isdir(join(cohort_path, f)) and f[0].isdigit()]
print(f"\n The followong animals are inside {cohorts[command]}:")
for item in animals:
    print(item)

# get folders on MARVIN
print("\n Retrieving information from the cluster...")
result = subprocess.run(["ssh", "marvin", "'ls'", f"'{cluster_path}'"],  capture_output = True)
entries = result.stdout.decode("UTF-8").split("\n")
cohort_entries = []
print("The following data folders can be found on the cluster:")
for entry in entries:
    if len(entry) >= 1:
        for animal in animals:
            if entry.split("_")[1] == animal.split("_")[1]:
                print(entry)
                cohort_entries.append(entry)

todo = int(input("\n What do you want to do? \n 0: Upload data to cluster \n 1: Download results from cluster \n 2: Delete data/results from cluster \n Select 0/1/2 >>> "))

### Upload Functionality
if todo == 0:
    imaging_data = {}
    for animal in animals:
        animal_path = cohort_path + "/" + animal
        folders = [f for f in listdir(animal_path) if isdir(join(animal_path, f))]
        for item in folders:
            if re.match(r"^S\d+_", item):
                session_path = animal_path + '/' + item + "/Imaging_Data/"
                files = [f for f in listdir(session_path) if isfile(join(session_path, f))]
                for file in files:
                    if file[-3:] == "nd2":
                        imaging_data[f"{animal}_{item}"] = join(session_path, file)
            else: pass
                
    print("\n The following imaging data exists:")
    for item in imaging_data:
        print(f"{item} : {imaging_data[item]}")
    
    # Make directories and copy    
    print("\n Uploading now...")
    for item in imaging_data:
        if item not in cohort_entries:
            subprocess.run(["ssh", "marvin", "'mkdir'", f"'{cluster_path}/{item}'"])
            print(f"Created directory for: {item}")
            subprocess.run(["scp", f"{imaging_data[item]}", f"{login_string}:{cluster_path}/{item}"])
            print(f"Copied nd2 file into {item}")

### Download Functionality
elif todo == 1:
    print("\n Downloading now...")
    for entry in cohort_entries:
        parts = entry.split("_")
        try:
            entry_folder = join(results_path,cohorts[command]) + "/" + f"{parts[0]}_{parts[1]}/{parts[2]}_{parts[3]}/Imaging_Data"
            entry_folder_contents = [f for f in listdir(entry_folder) if isdir(join(entry_folder, f))]
            if not "suite2p" in entry_folder_contents:
                subprocess.check_output(["scp", "-r", f"{login_string}:{cluster_path}/{entry}/suite2p", f"{entry_folder}"])
                print(f"Copied suite2p data into {entry_folder}")
            else:
                print(f"Suite2p data already exists for: {entry}")
        except subprocess.CalledProcessError:
            print(f"No suite2p results for: {entry}")
        except:
            print(f"No entry folder for: {entry}")

### Delete Functionality
elif todo == 2:
    sure = input(f"\n Are you sure you want to delete all data and results for {cohorts[command]} on MARVIN :( ? (yes/no) >>>")
    if sure.lower() == "yes":
        print(f"Deleting cohort data/results for: {cohorts[command]}")
        for entry in cohort_entries:
            subprocess.run(["ssh", "marvin", "'rm'", "'-r'", f"'{cluster_path}/{entry}'" ])
            print(f"Deleted folder for: {entry}")
    else: 
        print("Phew!")
else: pass
    