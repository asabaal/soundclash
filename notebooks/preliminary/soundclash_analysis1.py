# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: dl_env
#     language: python
#     name: python3
# ---

# %%
import glob
import importlib
import logging
import os
import subprocess
import types

import pandas as pd

from collections import OrderedDict
from typing import List, Tuple, Dict

from soundclash.preprocessing import detect_silences, generate_split_commands, analyze_audio_chunks, generate_split_commands_multi_file, convert_to_seconds

def find_package_location(package_name_or_module: str | types.ModuleType) -> str:
    """
    Find the location of a package, whether it's already imported or not.

    This function takes either a package name as a string or an already imported
    module object and returns the file path of the package.

    Parameters
    ----------
    package_name_or_module : Union[str, types.ModuleType]
        Either a string representing the package name or an imported module object.

    Returns
    -------
    str
        The file path of the package or an explanatory message if the package
        cannot be found or imported.

    Raises
    ------
    TypeError
        If the input is neither a string nor a module object.

    Examples
    --------
    >>> find_package_location('numpy')
    '/path/to/site-packages/numpy'
    >>> import pandas
    >>> find_package_location(pandas)
    '/path/to/site-packages/pandas'

    Notes
    -----
    The function assumes that the package is installed in a standard location
    within site-packages. It may not work correctly for packages installed in
    non-standard locations or for built-in modules.
    """

    package: types.ModuleType

    if isinstance(package_name_or_module, str):
        # If it's a string, treat it as a package name and try to import
        try:
            package = importlib.import_module(package_name_or_module)
        except ImportError:
            return f"Package '{package_name_or_module}' is not installed or cannot be imported."
    elif isinstance(package_name_or_module, types.ModuleType):
        # If it's already a module object, use it directly
        package = package_name_or_module
    else:
        raise TypeError("Argument must be a string (package name) or a module object.")
    
    # Get the file path of the package
    try:
        # Split the path and remove the last two components (usually 'site-packages' and the package name)
        package_path: str = "/".join(package.__file__.split("/")[:-3])
        return package_path
    except AttributeError:
        # Handle cases where __file__ is not available (e.g., for built-in modules)
        return f"Unable to determine the location of '{package.__name__}'. It might be a built-in module."
    
def run_command(command: str) -> None:
    """
    Execute an ffmpeg command and log the result.

    Parameters
    ----------
    command : str
        The ffmpeg command to execute.

    Returns
    -------
    None

    Notes
    -----
    This function logs the execution result or any errors that occur during execution.
    """
    try:
        process: subprocess.Popen = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout: str
        stderr: str
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            logging.error(f"Error executing command: {command}")
            logging.error(f"stderr: {stderr}")
        else:
            logging.info(f"Successfully executed: {command}")
    except Exception as e:
        logging.error(f"Exception occurred while executing command: {command}")
        logging.error(str(e))


# %%
host_dir: str = find_package_location("soundclash")
host_dir

# %%

# %%

# %%
#I'm going to see if I can find the silences in the audio files so I can get song lengths.
data_files: str = sorted(glob.glob(os.path.join(host_dir, "data", "*.mp3")))
data_files

# %%

# %%
silences: OrderedDict[Tuple[float, float]] = {}
for data_file in data_files:
    silences[data_file] = (detect_silences(data_file, silence_thresh = -40, min_silence_len=1.5))

# %%
output_dir = os.path.join(host_dir,"data/detected_audio_chunks")

# %%
output_dir

# %%
df = pd.read_csv(os.path.join(host_dir, "data", "SoundclashRemixContestWinners.csv"))
df["Track Length"] = df["Track Length"].apply(convert_to_seconds)

# %%
#split_commands = generate_split_commands(data_files[0], silences_1, output_dir)
split_commands = generate_split_commands_multi_file(silences, output_dir, df["Track Length"].values)

# %%
split_commands

# %%
# Remove files if already exist
import glob
for file in glob.glob(os.path.join(output_dir, "*")):
    os.remove(file)

# Execute commands
split_commands = [cmd for cmd in split_commands if "-to" in cmd]
for i, command in enumerate(split_commands):
    print(i, command)
    run_command(command)

# %%

# %%
chunks_df = analyze_audio_chunks(os.path.join(host_dir, "data/detected_audio_1"))

# %%
chunks_df

# %%
df = df.reset_index().rename(columns={"index":"track_number"})

# %%
df_1_comp = df.merge(chunks_df, left_on="track_number", right_on="chunk_number").iloc[0:44]

# %%
from datetime import timedelta
df_1_comp["duration"] = df_1_comp["duration"].apply(lambda x: timedelta(seconds=x))

# %%

# %%
df_1_comp

# %%
