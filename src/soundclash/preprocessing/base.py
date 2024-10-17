import os
import re
import logging
import glob
import subprocess
import json
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_silence
from datetime import timedelta
from typing import List, Tuple

#TODO document this code in github

#TODO convert this to a function
#ffmpeg to split the audio file into chunks
# ffmpeg -i SoundclashRecordings7.mp3 -f segment -segment_time 10 -c copy chunks_7/chunk_t%03d.mp3
# and same for the others

def count_chunks(raw_audio: str, chunks_dir: str = "chunks") -> int:
    # count the number of chunks in the directory
    return len(os.listdir(os.path.join(path_of(raw_audio), chunks_dir)))

def path_of(file: str) -> str:
    return os.path.join(os.getcwd(), file)

def process_audio_file_in_chunks(directory):
    # Get a list of all files in the directory
    chunk_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.mp3')]

    # Extract numeric values from file names
    numeric_values = [int(f.split("_")[-1].split(".")[0][1:]) for f in chunk_files]

    # Get the sorted indices based on numeric values
    sorted_indices = np.argsort(numeric_values)

    # Sort the chunk files based on the sorted indices
    sorted_chunk_files = [chunk_files[i] for i in sorted_indices]

    return sorted_chunk_files

def find_silences_in_audio(sorted_chunk_files, silence_thresh=-40, min_silence_len=1000):
    silences = []
    previous_chunk_end = 0
    previous_chunk_silence_end = None

    # Process each chunk in sorted order
    for i, chunk_file in enumerate(sorted_chunk_files):
        audio_chunk = AudioSegment.from_mp3(chunk_file)
        chunk_silences = detect_silence(audio_chunk, min_silence_len=min_silence_len, silence_thresh=silence_thresh)

        # Adjust silence positions relative to the original audio
        adjusted_silences = [(start + previous_chunk_end, end + previous_chunk_end) for start, end in chunk_silences]

        # Check for silence at the start of the chunk
        if previous_chunk_silence_end is not None and adjusted_silences and adjusted_silences[0][0] == previous_chunk_end:
            # Merge with the previous chunk's ending silence
            adjusted_silences[0] = (previous_chunk_silence_end[0], adjusted_silences[0][1])
            previous_chunk_silence_end = None

        # Check for silence at the end of the chunk
        if adjusted_silences and adjusted_silences[-1][1] == previous_chunk_end + len(audio_chunk):
            previous_chunk_silence_end = adjusted_silences.pop()

        silences.extend(adjusted_silences)
        previous_chunk_end += len(audio_chunk)

    # Add the last chunk's ending silence if it exists
    if previous_chunk_silence_end is not None:
        silences.append(previous_chunk_silence_end)

    return silences


def generate_ffmpeg_silence_detect_command(input_file):
    return [
        "ffmpeg",
        "-i", input_file,
        "-af", "silencedetect=noise=-30dB:d=0.5",
        "-f", "null",
        "-"
    ]

def parse_silence_output(output):
    silences = []
    for line in output.split('\n'):
        if "silence_end" in line:
            parts = line.split()
            end = float(parts[4])
            duration = float(parts[8])
            start = end - duration
            silences.append((start, end))
    return silences


def get_file_duration(input_file: str) -> float:
    command = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{input_file}"'
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return float(result.stdout.strip()) * 1000  # Convert to milliseconds

def generate_split_commands(input_file: str, silences: List[Tuple[int, int]], chunk_dir: str, output_dir: str, min_duration: int = 60000) -> List[str]:
    commands = []
    file_duration = get_file_duration(input_file)
    
    # Handle the first non-silent segment
    chunk_counter = 0
    start = 0
    for silence_start, silence_end in silences:
        if silence_start - start >= min_duration:
            output_file = os.path.join(output_dir, f"chunk_{chunk_counter:03d}.mp3")
            command = f'ffmpeg -i "{input_file}" -ss {start/1000:.3f} -to {silence_start/1000:.3f} -c copy "{output_file}"'
            commands.append(command)
            chunk_counter += 1
        start = silence_end
    
    # Handle the last segment (which might be silence)
    if file_duration - start >= min_duration:
        output_file = os.path.join(output_dir, f"chunk_{chunk_counter:03d}.mp3")
        command = f'ffmpeg -i "{input_file}" -ss {start/1000:.3f} -c copy "{output_file}"'
        commands.append(command)
    
    return commands

def run_ffmpeg_command(command: str):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            logging.error(f"Error executing command: {command}")
            logging.error(f"stderr: {stderr}")
        else:
            logging.info(f"Successfully executed: {command}")
    except Exception as e:
        logging.error(f"Exception occurred while executing command: {command}")
        logging.error(str(e))
