import logging
import os
import subprocess
import time
from argparse import ArgumentParser
from pathlib import Path

import platformdirs
import yaml


def validate(item, keys):
    return all(k in item for k in keys)


def sorted_directory_listing(directory):
    def get_creation_time(entry):
        return entry.stat().st_ctime

    with os.scandir(directory) as entries:
        sorted_entries = sorted(entries, key=get_creation_time)
        sorted_items = [{"name": entry.name, "time": entry.stat().st_ctime} for entry in sorted_entries]
    return sorted_items


def find(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1


def main():
    appname = "pickup"
    parser = ArgumentParser(prog=appname)
    parser.add_argument("config", help="Config file", type=str)
    args = parser.parse_args()

    assert os.path.exists(args.config), "Config file does not exist"

    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)

    logger = logging.getLogger(__name__)

    timestamps = dict()

    data_path = Path(platformdirs.user_data_dir(appname))
    if not data_path.exists():
        data_path.mkdir(parents=True)
    timestamps_path = data_path.joinpath("timestamps.yml")
    chkp = {}
    if timestamps_path.exists():
        with open(timestamps_path, "r") as file:
            chkp = yaml.safe_load(file)

    for key, value in config.items():
        if not validate(value, ["path", "size", "filenames"]):
            logger.warning(f"Skipping {key} because it's not valid")
            continue

        path = value["path"]

        if not os.path.exists(path):
            logger.warning(f"Skipping {key} because its path ({path}) field does not exist")

        size = value["size"]

        filenames_to_copy = value["filenames"]
        if type(filenames_to_copy) is not list:
            filenames_to_copy = [filenames_to_copy]

        timestamp = None
        if key in chkp and validate(chkp[key], ["name", "time"]):
            timestamp = chkp[key]

        if key.endswith(".zip"):
            zip_name = f"{key[0, len(key) - 3]}_{round(time.time() * 1000)}.zip"
        else:
            zip_name = f"{key}_{round(time.time() * 1000)}.zip"

        directories = sorted_directory_listing(path)
        timestamps[key] = directories[-1]

        if timestamp is not None:
            index = find(directories, "name", timestamp["name"])
            if index == len(directories) - 1:
                continue
            if index is not None and index != -1:
                directories = directories[index + 1::]

        key_path = data_path.joinpath(key)
        with open(key_path, "w") as file:
            for entry in directories:
                directory = entry["name"]
                for to_copy in filenames_to_copy:
                    name = os.path.join(path, directory, to_copy)
                    file.write(name)
                    file.write("\n")

        if size != 0:
            # subprocess.run(["7z", "a", "-spf", f"-v{size}m", zip_name, f"@{key}"])
            subprocess.run(["7z", "a", "-spf", f"-v{size}m", f"-ir@{key_path}", zip_name])
        else:
            subprocess.run(["7z", "a", "-spf", f"-ir@{key}", zip_name])

    with open(timestamps_path, "w") as file:
        yaml.dump(timestamps, file)


if __name__ == '__main__':
    main()
