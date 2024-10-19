import pytest
import pandas as pd
import os
from typing import List, Tuple, Dict, Any
from unittest.mock import patch, MagicMock
from collections import OrderedDict

# Import the functions to be tested
from soundclash.preprocessing import (
    detect_silences,
    get_file_duration,
    generate_split_commands,
    analyze_audio_chunks,
    convert_to_seconds,
    generate_split_commands_multi_file
)

class TestDetectSilences:
    """
    A test class for the detect_silences function.

    This class contains test methods to verify the functionality of the
    detect_silences function, including tests with default and custom parameters.

    Methods
    -------
    test_detect_silences
        Test detect_silences function with default parameters.
    test_detect_silences_custom_params
        Test detect_silences function with custom silence threshold and minimum length.
    """

    @pytest.fixture
    def mock_subprocess_run(self: "TestDetectSilences") -> MagicMock:
        """
        Fixture to mock subprocess.run for testing.

        Returns
        -------
        MagicMock
            A mock object for subprocess.run.
        """
        with patch('subprocess.run') as mock_run:
            yield mock_run

    def test_detect_silences(self: "TestDetectSilences", mock_subprocess_run: MagicMock) -> None:
        """
        Test the detect_silences function with default parameters.

        Parameters
        ----------
        mock_subprocess_run : MagicMock
            Mocked subprocess.run function.

        Returns
        -------
        None
        """
        mock_result: MagicMock = MagicMock()
        mock_result.stderr = (
            "silence_start: 1.5\n"
            "silence_end: 3.0\n"
            "silence_start: 5.5\n"
            "silence_end: 7.0\n"
        )
        mock_subprocess_run.return_value = mock_result

        result: List[Tuple[float, float]] = detect_silences("test.mp3")
        expected: List[Tuple[float, float]] = [(1.5, 3.0), (5.5, 7.0)]
        assert result == expected

    def test_detect_silences_custom_params(self: "TestDetectSilences", mock_subprocess_run: MagicMock) -> None:
        """
        Test the detect_silences function with custom silence threshold and minimum length.

        Parameters
        ----------
        mock_subprocess_run : MagicMock
            Mocked subprocess.run function.

        Returns
        -------
        None
        """
        mock_result: MagicMock = MagicMock()
        mock_result.stderr = "silence_start: 2.0\nsilence_end: 4.0\n"
        mock_subprocess_run.return_value = mock_result

        result: List[Tuple[float, float]] = detect_silences("test.mp3", silence_thresh=-40, min_silence_len=2)
        expected: List[Tuple[float, float]] = [(2.0, 4.0)]
        assert result == expected

class TestGetFileDuration:
    """
    A test class for the get_file_duration function.

    This class contains a test method to verify the functionality of the
    get_file_duration function.

    Methods
    -------
    test_get_file_duration
        Test get_file_duration function with a mocked subprocess call.
    """

    @pytest.fixture
    def mock_subprocess_run(self: "TestGetFileDuration") -> MagicMock:
        """
        Fixture to mock subprocess.run for testing.

        Returns
        -------
        MagicMock
            A mock object for subprocess.run.
        """
        with patch('subprocess.run') as mock_run:
            yield mock_run

    def test_get_file_duration(self: "TestGetFileDuration", mock_subprocess_run: MagicMock) -> None:
        """
        Test the get_file_duration function.

        Parameters
        ----------
        mock_subprocess_run : MagicMock
            Mocked subprocess.run function.

        Returns
        -------
        None
        """
        mock_result: MagicMock = MagicMock()
        mock_result.stdout = "120.5\n"
        mock_subprocess_run.return_value = mock_result

        result: float = get_file_duration("test.mp3")
        assert result == 120500.0  # 120.5 seconds in milliseconds

class TestGenerateSplitCommands:
    """
    A test class for the generate_split_commands function.

    This class contains a test method to verify the functionality of the
    generate_split_commands function.

    Methods
    -------
    test_generate_split_commands
        Test generate_split_commands function with mocked file duration.
    """

    @pytest.fixture
    def mock_get_file_duration(self: "TestGenerateSplitCommands") -> MagicMock:
        """
        Fixture to mock get_file_duration for testing.

        Returns
        -------
        MagicMock
            A mock object for get_file_duration.
        """
        with patch('your_module.get_file_duration') as mock:
            mock.return_value = 180000  # 3 minutes in milliseconds
            yield mock

    def test_generate_split_commands(self: "TestGenerateSplitCommands") -> None:
        """
        Test the generate_split_commands function.

        Parameters
        ----------
        mock_get_file_duration : MagicMock
            Mocked get_file_duration function.

        Returns
        -------
        None
        """
        silences: List[Tuple[float, float]] = [(30.0, 35.0), (90.0, 95.0)]
        result: List[str] = generate_split_commands("input.mp3", silences, "/output/dir")
        expected: List[str] = [
            'ffmpeg -i "input.mp3" -ss 0.000 -to 30.000 -c copy "/output/dir/chunk_000.mp3"',
            'ffmpeg -i "input.mp3" -ss 35.000 -to 90.000 -c copy "/output/dir/chunk_001.mp3"',
            'ffmpeg -i "input.mp3" -ss 95.000 -to 180000.000 -c copy "/output/dir/chunk_002.mp3"'
        ]
        assert result == expected

class TestAnalyzeAudioChunks:
    """
    A test class for the analyze_audio_chunks function.

    This class contains a test method to verify the functionality of the
    analyze_audio_chunks function.

    Methods
    -------
    test_analyze_audio_chunks
        Test analyze_audio_chunks function with mocked os and subprocess calls.
    """

    @pytest.fixture
    def mock_os_listdir(self: "TestAnalyzeAudioChunks") -> MagicMock:
        """
        Fixture to mock os.listdir for testing.

        Returns
        -------
        MagicMock
            A mock object for os.listdir.
        """
        with patch('os.listdir') as mock:
            mock.return_value = ["chunk_000.mp3", "chunk_001.mp3"]
            yield mock

    @pytest.fixture
    def mock_subprocess_run(self: "TestAnalyzeAudioChunks") -> MagicMock:
        """
        Fixture to mock subprocess.run for testing.

        Returns
        -------
        MagicMock
            A mock object for subprocess.run.
        """
        with patch('subprocess.run') as mock_run:
            mock_result: MagicMock = MagicMock()
            mock_result.stdout = '{"streams": [{"codec_type": "audio", "sample_rate": "44100", "channels": "2"}], "format": {"duration": "60.5", "bit_rate": "128000"}}'
            mock_run.return_value = mock_result
            yield mock_run

    def test_analyze_audio_chunks(self: "TestAnalyzeAudioChunks") -> None:
        """
        Test the analyze_audio_chunks function.

        Parameters
        ----------
        mock_os_listdir : MagicMock
            Mocked os.listdir function.
        mock_subprocess_run : MagicMock
            Mocked subprocess.run function.

        Returns
        -------
        None
        """
        result: pd.DataFrame = analyze_audio_chunks("/test/dir")
        expected_df: pd.DataFrame = pd.DataFrame([
            {"chunk_number": 0, "duration": 60.5, "bit_rate": 128000, "sample_rate": 44100, "channels": 2},
            {"chunk_number": 1, "duration": 60.5, "bit_rate": 128000, "sample_rate": 44100, "channels": 2}
        ])
        pd.testing.assert_frame_equal(result, expected_df)

class TestConvertToSeconds:
    """
    A test class for the convert_to_seconds function.

    This class contains a parameterized test method to verify the functionality
    of the convert_to_seconds function with various inputs.

    Methods
    -------
    test_convert_to_seconds
        Test convert_to_seconds function with different time string inputs.
    """

    @pytest.mark.parametrize("time_str,expected", [
        ("1:30", 90),
        ("0:45", 45),
        ("2:00", 120),
    ])
    def test_convert_to_seconds(self: "TestConvertToSeconds", time_str: str, expected: int) -> None:
        """
        Test the convert_to_seconds function with various inputs.

        Parameters
        ----------
        time_str : str
            Input time string in the format "minutes:seconds".
        expected : int
            Expected output in seconds.

        Returns
        -------
        None
        """
        assert convert_to_seconds(time_str) == expected

class TestGenerateSplitCommandsMultiFile:
    """
    A test class for the generate_split_commands_multi_file function.

    This class contains a test method to verify the functionality of the
    generate_split_commands_multi_file function.

    Methods
    -------
    test_generate_split_commands_multi_file
        Test generate_split_commands_multi_file function with mocked file durations.
    """

    @pytest.fixture
    def mock_get_file_duration(self: "TestGenerateSplitCommandsMultiFile") -> MagicMock:
        """
        Fixture to mock get_file_duration for testing.

        Returns
        -------
        MagicMock
            A mock object for get_file_duration.
        """
        with patch('your_module.get_file_duration') as mock:
            mock.side_effect = [180000, 120000]  # 3 minutes, 2 minutes
            yield mock

    def test_generate_split_commands_multi_file(self: "TestGenerateSplitCommandsMultiFile") -> None:
        """
        Test the generate_split_commands_multi_file function.

        Parameters
        ----------
        mock_get_file_duration : MagicMock
            Mocked get_file_duration function.

        Returns
        -------
        None
        """
        silences: OrderedDict[str, List[Tuple[float, float]]] = OrderedDict([
            ("file1.mp3", [(30.0, 35.0), (90.0, 95.0)]),
            ("file2.mp3", [(50.0, 55.0)])
        ])
        known_durations: List[float] = [60, 150, 70]
        result: List[str] = generate_split_commands_multi_file(silences, "/output/dir", known_durations)
        expected: List[str] = [
            'ffmpeg -i "file1.mp3" -ss 0.000 -to 30.000 -c copy "/output/dir/chunk_000.mp3"',
            'ffmpeg -i "file1.mp3" -ss 35.000 -to 65.000 -c copy "/output/dir/chunk_000.mp3"',
            'ffmpeg -i "file1.mp3" -ss 65.000 -to 90.000 -c copy "/output/dir/chunk_001.mp3"',
            'ffmpeg -i "file1.mp3" -ss 95.000 -to 180.000 -c copy "/output/dir/chunk_001.mp3"',
            'ffmpeg -i "file2.mp3" -ss 0.000 -to 50.000 -c copy "/output/dir/chunk_001.mp3"',
            'ffmpeg -i "file2.mp3" -ss 55.000 -to 75.000 -c copy "/output/dir/chunk_002.mp3"'
        ]
        assert result == expected