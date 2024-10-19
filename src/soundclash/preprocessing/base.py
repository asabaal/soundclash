import os
import subprocess
import pandas as pd
import json
from typing import List, Dict, Any, Tuple

def detect_silences(input_file: str, silence_thresh: float = -30, min_silence_len: float = 1) -> List[Tuple[float, float]]:
    """
    Detect silences in an audio file using ffmpeg.

    Parameters
    ----------
    input_file : str
        The path to the input audio file.
    silence_thresh : float, optional
        The threshold (in dB) below which the audio is considered silence.
        Default is -30 dB.
    min_silence_len : float, optional
        The minimum length of silence to detect, in seconds. Default is 1 second.

    Returns
    -------
    List[Tuple[float, float]]
        A list of tuples containing the start and end times of detected silences.

    Notes
    -----
    This function uses ffmpeg's silencedetect filter to identify silent periods in the audio.
    """
    # Declare variables with type hints
    command: List[str] = []
    result: subprocess.CompletedProcess
    silences: List[Tuple[float, float]] = []
    start: float
    end: float

    # Construct the ffmpeg command
    command = [
        'ffmpeg',
        '-i', input_file,
        '-af', f'silencedetect=noise={silence_thresh}dB:d={min_silence_len}',
        '-f', 'null',
        '-'
    ]
    
    # Run the ffmpeg command and capture the output
    result = subprocess.run(command, capture_output=True, text=True)
    
    # Parse the ffmpeg output to extract silence start and end times
    line: str
    for line in result.stderr.split('\n'):
        if 'silence_start' in line:
            start = float(line.split('silence_start: ')[1])
            silences.append((start, None))
        elif 'silence_end' in line:
            end = float(line.split('silence_end: ')[1].split(' ')[0])
            if silences and silences[-1][1] is None:
                silences[-1] = (silences[-1][0], end)
    
    return silences

def get_file_duration(input_file: str) -> float:
    """
    Get the duration of an audio file in milliseconds.

    Parameters
    ----------
    input_file : str
        The path to the input audio file.

    Returns
    -------
    float
        The duration of the audio file in milliseconds.
    """
    command: str = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{input_file}"'
    result: subprocess.CompletedProcess = subprocess.run(command, capture_output=True, text=True, shell=True)
    duration: float = float(result.stdout.strip()) * 1000  # Convert to milliseconds
    return duration

def generate_split_commands(input_file: str, silences: List[Tuple[float, float]], output_dir: str, min_duration: float = 60) -> List[str]:
    """
    Generate ffmpeg commands to split an audio file based on detected silences.

    Parameters
    ----------
    input_file : str
        The path to the input audio file.
    silences : List[Tuple[float, float]]
        A list of tuples containing the start and end times of detected silences.
    output_dir : str
        The directory where the split audio files will be saved.
    min_duration : float, optional
        The minimum duration (in seconds) for a split segment. Default is 60 seconds.

    Returns
    -------
    List[str]
        A list of ffmpeg commands to split the audio file.
    """
    commands: List[str] = []
    file_duration: float = get_file_duration(input_file)
    
    chunk_start: float = 0
    chunk_counter: int = 0

    silence_start: float
    silence_end: float

    for silence_start, silence_end in silences:
        if silence_start - chunk_start >= min_duration:
            output_file: str = os.path.join(output_dir, f"chunk_{chunk_counter:03d}.mp3")
            command: str = f'ffmpeg -i "{input_file}" -ss {chunk_start:.3f} -to {silence_start:.3f} -c copy "{output_file}"'
            commands.append(command)
            chunk_counter += 1
        
        chunk_start = silence_end

    # Handle the last segment if it's not silence and meets the minimum duration
    if file_duration - chunk_start >= min_duration:
        output_file: str = os.path.join(output_dir, f"chunk_{chunk_counter:03d}.mp3")
        command: str = f'ffmpeg -i "{input_file}" -ss {chunk_start:.3f} -to {file_duration:.3f} -c copy "{output_file}"'
        commands.append(command)

    return commands

def analyze_audio_chunks(chunk_dir: str) -> pd.DataFrame:
    """
    Analyze audio chunks in a given directory using ffmpeg.

    This function goes through each MP3 file in the specified directory,
    extracts information using ffmpeg, and creates a pandas DataFrame
    with the results.

    Parameters
    ----------
    chunk_dir : str
        The directory containing the audio chunk files (format: chunk_xxx.mp3).

    Returns
    -------
    pd.DataFrame
        A DataFrame containing information about each audio chunk, including:
        - chunk_number: The number extracted from the filename
        - duration: The length of the audio file in seconds
        - bit_rate: The bit rate of the audio file
        - sample_rate: The sample rate of the audio file
        - channels: The number of audio channels

    Raises
    ------
    FileNotFoundError
        If the specified directory does not exist.
    subprocess.CalledProcessError
        If there's an error running the ffmpeg command.

    Notes
    -----
    This function requires ffmpeg to be installed and accessible in the system PATH.
    """
    if not os.path.isdir(chunk_dir):
        raise FileNotFoundError(f"The directory {chunk_dir} does not exist.")

    chunk_files: List[str] = [f for f in os.listdir(chunk_dir) if f.startswith("chunk_") and f.endswith(".mp3")]
    chunk_files.sort()  # Ensure files are processed in order

    data: List[Dict[str, Any]] = []

    for chunk_file in chunk_files:
        chunk_number: int = int(chunk_file.split("_")[1].split(".")[0])
        file_path: str = os.path.join(chunk_dir, chunk_file)

        # Run ffprobe command to get file information
        cmd: List[str] = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        try:
            result: subprocess.CompletedProcess = subprocess.run(cmd, capture_output=True, text=True, check=True)
            file_info: Dict[str, Any] = json.loads(result.stdout)

            # Extract relevant information
            audio_stream: Dict[str, Any] = next(s for s in file_info["streams"] if s["codec_type"] == "audio")
            format_info: Dict[str, Any] = file_info["format"]

            data.append({
                "chunk_number": chunk_number,
                "duration": float(format_info["duration"]),
                "bit_rate": int(format_info["bit_rate"]),
                "sample_rate": int(audio_stream["sample_rate"]),
                "channels": int(audio_stream["channels"])
            })
        except subprocess.CalledProcessError as e:
            print(f"Error processing file {chunk_file}: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error parsing ffprobe output for file {chunk_file}: {e}")

    # Create DataFrame from the collected data
    df: pd.DataFrame = pd.DataFrame(data)
    return df

# Convert "Track Length" to seconds
def convert_to_seconds(time_str: str) -> float:
    minutes, seconds = map(int, time_str.split(':'))
    return minutes * 60 + seconds


def generate_split_commands_multi_file(input_files: List[str], silences: List[List[Tuple[float, float]]], output_dir: str, known_durations: List[float]) -> List[str]:
    """
    Generate ffmpeg commands to split multiple audio files based on known song durations and detected silences.

    Parameters
    ----------
    input_files : List[str]
        A list of paths to the input audio files, in the correct order.
    silences : List[List[Tuple[float, float]]]
        A list of silence lists, each corresponding to an input file.
        Each silence is represented as a tuple of (start_time, end_time).
    output_dir : str
        The directory where the split audio files will be saved.
    known_durations : List[float]
        A list of known song durations in seconds.

    Returns
    -------
    List[str]
        A list of ffmpeg commands to split the audio files.
    """
    commands: List[str] = []
    chunk_counter: int = 0
    current_file_index: int = 0
    current_file_position: float = 0
    remaining_duration: float = 0

    for i, duration in enumerate(known_durations):
        print(i)
        remaining_duration = duration

        while remaining_duration > 0 and current_file_index < len(input_files):
            current_file = input_files[current_file_index]
            file_duration = get_file_duration(current_file)
            file_silences = silences[current_file_index]

            chunk_start = current_file_position
            chunk_end = min(file_duration, chunk_start + remaining_duration)

            # Adjust chunk_end if it crosses a silence
            for silence_start, silence_end in file_silences:
                if silence_start <= chunk_end < silence_end:
                    chunk_end = silence_start
                    break

            output_file = os.path.join(output_dir, f"chunk_{chunk_counter:03d}.mp3")
            command = f'ffmpeg -i "{current_file}" -ss {chunk_start:.3f} -to {chunk_end:.3f} -c copy "{output_file}"'
            commands.append(command)

            chunk_duration = chunk_end - chunk_start
            remaining_duration -= chunk_duration
            current_file_position += chunk_duration

            # Move to next file if we've reached the end of the current file
            if current_file_position >= file_duration:
                current_file_index += 1
                current_file_position = 0

        chunk_counter += 1

    return commands