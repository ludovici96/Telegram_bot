
import os
import shutil
from pydub import AudioSegment
from typing import List

def convert_ogg_to_wav(ogg_path: str, wav_path: str) -> None:
    """
    Convert OGG audio file to WAV format.
    
    Args:
        ogg_path (str): Path to the OGG file
        wav_path (str): Path where the WAV file should be saved
    """
    try:
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")
    except Exception as e:
        print(f"Error converting OGG to WAV: {e}")
        raise

def clear_directory(directory: str) -> None:
    """
    Clear all contents of a directory.
    
    Args:
        directory (str): Path to the directory to clear
    """
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

def cleanup_files(file_paths: List[str]) -> None:
    """
    Remove multiple files from the filesystem.
    
    Args:
        file_paths (List[str]): List of file paths to remove
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error removing file {file_path}: {e}")