import logging
import os
import time
from argparse import ArgumentParser
from pathlib import Path

import platformdirs
import win_roboco_py as robo
import yaml

logger = logging.getLogger(__name__)


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


def milli_time(_time):
    return round(_time * 1000)


def main():
    appname = "pickup"
    parser = ArgumentParser(prog=appname)
    parser.add_argument("config", help="Config file", type=str)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    assert os.path.exists(args.config), "Config file does not exist"

    with open(args.config, 'r') as file:
        config = yaml.safe_load(file)

    data_path = Path(platformdirs.user_data_dir(appname))
    if not data_path.exists():
        data_path.mkdir(parents=True)

    log_path = data_path.joinpath(".log")
    if args.verbose:
        logging.basicConfig(filename=log_path, level=logging.DEBUG)
    else:
        logging.basicConfig(filename=log_path)

    start_time = time.time()
    logger.info("Start time [ns]: %s" % start_time)

    timestamps = dict()

    timestamps_path = data_path.joinpath("timestamps.yml")
    chkp = {}
    if timestamps_path.exists():
        with open(timestamps_path, "r") as file:
            chkp = yaml.safe_load(file)

    for key, value in config.items():
        if not validate(value, ["inpath", "outpath", "filenames"]):
            logger.error(
                f"Skipping {key} because its structure is not valid. 'inpath', 'outpath' and 'filenames' fields are required!")
            continue

        inpath = value["inpath"]
        inpath_path = Path(inpath)

        outpath = value["outpath"]

        if not inpath_path.exists():
            logger.error(f"Skipping {key} because the inpath path ({inpath}) does not exist")
            continue

        key_path = Path(outpath, key)
        if not key_path.exists():
            os.makedirs(key_path)

        filenames_to_copy = value["filenames"]
        if type(filenames_to_copy) is not list:
            filenames_to_copy = [filenames_to_copy]

        timestamp = None
        if key in chkp and validate(chkp[key], ["name", "time"]):
            timestamp = chkp[key]

        directories = sorted_directory_listing(inpath)
        timestamps[key] = directories[-1]

        if timestamp is not None:
            index = find(directories, "name", timestamp["name"])
            if index == len(directories) - 1:
                continue
            if index is not None and index != -1:
                directories = directories[index::]

        for entry in directories:
            directory = entry["name"]
            source = inpath_path.joinpath(directory)
            destination = key_path.joinpath(directory)
            for to_copy in filenames_to_copy:
                try:
                    robo.copy_file(source.joinpath(to_copy), destination, verbose=args.verbose)
                except AssertionError:
                    logger.error(f"{source.joinpath(to_copy)} not found")

    with open(timestamps_path, "w") as file:
        yaml.dump(timestamps, file)

    end_time = time.time()
    logger.info("End time [ns]: %s" % end_time)
    logger.info("Duration [ms]: %s" % milli_time(end_time - start_time))


if __name__ == '__main__':
    main()
