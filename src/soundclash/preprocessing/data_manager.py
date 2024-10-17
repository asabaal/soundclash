import os
import requests
import zipfile
from typing import List

class DataManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.zip_filename = "all_data.zip"
        self.zip_link = "https://drive.google.com/file/d/1LFbqK8tgBaVfRZedJU7B6Z3n_PQyS2bd/view?usp=sharing"
        self.extracted_files: List[str] = []

    def download_and_extract_data(self) -> None:
        """
        Download the zip file from Google Drive and extract its contents if not already done.
        """
        zip_path = os.path.join(self.data_dir, self.zip_filename)

        if not os.path.exists(zip_path):
            os.makedirs(self.data_dir, exist_ok=True)
            
            print(f"Downloading {self.zip_filename}...")
            response = requests.get(self.zip_link)
            response.raise_for_status()  # Raises an HTTPError for bad responses

            with open(zip_path, 'wb') as file:
                file.write(response.content)
            
            print(f"Downloaded: {self.zip_filename}")

        if not self.extracted_files:
            print(f"Extracting {self.zip_filename}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.data_dir)
            self.extracted_files = zip_ref.namelist()
            print("Extraction complete.")

    def get_data_path(self, filename: str) -> str:
        """
        Get the path to a data file, ensuring the zip file is downloaded and extracted if necessary.
        
        :param filename: Name of the file to get
        :return: Path to the file
        """
        if not self.extracted_files:
            self.download_and_extract_data()

        if filename not in self.extracted_files:
            raise ValueError(f"File not found in the data package: {filename}")

        return os.path.join(self.data_dir, filename)

    def list_available_files(self) -> List[str]:
        """
        List all available files in the extracted data.
        
        :return: List of filenames
        """
        if not self.extracted_files:
            self.download_and_extract_data()
        
        return self.extracted_files