import os
import subprocess
import logging
from urllib.parse import urlparse
import json
import shutil
import re  
from ..config.settings import DOWNLOAD_FOLDER, SUPPORTED_SITES_FILE, YT_DLP_FOLDER, GALLERY_DL_CONFIG, TEXT_CONFIG
from .base_service import BaseService

logger = logging.getLogger(__name__)

class DownloaderService(BaseService):
    def __init__(self):
        super().__init__()
        self.supported_sites = self.get_supported_sites()
        self.DOWNLOAD_FOLDER = DOWNLOAD_FOLDER
        self.YT_DLP_FOLDER = YT_DLP_FOLDER

    def get_supported_sites(self):
        logger.info("Loading supported sites from file.")
        supported_sites = []
        try:
            with open(SUPPORTED_SITES_FILE, 'r', encoding='utf-8') as file:
                for line in file:
                    match = re.search(r'https?://\S+', line)
                    if match:
                        domain = urlparse(match.group(0)).netloc
                        supported_sites.append(domain)
            logger.info("Supported sites loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading supported sites: {e}")
        return supported_sites

    def is_supported(self, url):
        domain = urlparse(url).netloc
        is_supported = domain in self.supported_sites
        logger.info(f"URL {url} is {'supported' if is_supported else 'not supported'}.")
        return is_supported

    def sanitize_description(self, text):
        """Remove hashtags and clean up description text"""
        if not text:
            return ""
        # Remove hashtags and the words they're attached to
        text = re.sub(r'#\w+\b', '', text)
        # Remove multiple spaces and trim
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def is_youtube_url(self, url):
        """Check if the URL is from YouTube"""
        domain = urlparse(url).netloc.lower()
        return any(yt_domain in domain for yt_domain in ['youtube.com', 'youtu.be'])

    def get_video_description(self, info_file_path):
        """Extract and sanitize video description from info.json"""
        try:
            with open(info_file_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
                title = info.get('title', '').strip()
                description = info.get('description', '').strip()
                uploader = info.get('uploader', '').strip()
                
                # Check if description is same as title or contains title
                if description == title or title in description:
                    full_description = description
                else:
                    full_description = f"{title}\n\n{description}"

                # Add uploader if available and not already in description
                if uploader and uploader not in full_description:
                    full_description = f"By: {uploader}\n\n{full_description}"

                return self.sanitize_description(full_description)
        except Exception as e:
            logger.error(f"Error reading video description: {e}")
            return ""

    def download_video(self, url):
        # Block YouTube URLs completely
        if self.is_youtube_url(url):
            logger.debug(f"[DOWNLOAD] Blocking YouTube URL: {url}")
            return None, None  # Changed to return None, None instead of error message

        logger.debug(f"[DOWNLOAD] Starting video download process for URL: {url}")
        os.makedirs(self.YT_DLP_FOLDER, exist_ok=True)

        try:
            # Check if the video is live
            check_result = subprocess.run(
                [
                    "yt-dlp",
                    "--print", "is_live",
                    url
                ],
                capture_output=True,
                text=True
            )
            
            if "True" in check_result.stdout:
                logger.debug(f"[DOWNLOAD] Skipping live video: {url}")
                return None, "This is a live video stream which cannot be downloaded."

            # Download using best format
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-o", f"{self.YT_DLP_FOLDER}/%(title)s.%(ext)s",
                    "--write-info-json",
                    "--merge-output-format", "mp4",
                    "--no-playlist",
                    "-f", "best",
                    url
                ],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                video_files = [os.path.join(self.YT_DLP_FOLDER, f) for f in os.listdir(self.YT_DLP_FOLDER) 
                             if f.endswith(('.mp4', '.mkv', '.webm'))]
                
                if video_files:
                    video_path = video_files[0]
                    # Look for corresponding .info.json file
                    info_file = os.path.splitext(video_path)[0] + '.info.json'
                    description = self.get_video_description(info_file) if os.path.exists(info_file) else ""
                    return video_path, description
                    
                return None, None
            else:
                logger.debug(f"[DOWNLOAD] Download failed: {result.stderr}")
                return self._fallback_download(url)

        except Exception as e:
            logger.debug(f"[DOWNLOAD] Critical error in video download: {e}")
            return None, None

    def _fallback_download(self, url):
        """Fallback method when primary download fails"""
        logger.debug(f"[FALLBACK] Attempting fallback download for URL: {url}")
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-o", f"{self.YT_DLP_FOLDER}/%(title)s.%(ext)s",
                    "--write-info-json",
                    "--merge-output-format", "mp4",
                    "--no-playlist",
                    "-f", "best",
                    url
                ],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                video_files = [f for f in os.listdir(self.YT_DLP_FOLDER) 
                             if f.endswith(('.mp4', '.mkv', '.webm'))]
                if video_files:
                    video_path = os.path.join(self.YT_DLP_FOLDER, video_files[0])
                    info_file = os.path.splitext(video_path)[0] + '.info.json'
                    description = self.get_video_description(info_file) if os.path.exists(info_file) else ""
                    return video_path, description
            
            return None, "Could not download video."
            
        except Exception as e:
            logger.debug(f"[FALLBACK] Error in fallback download: {e}")
            return None, None

    def download_images(self, url):
        logger.info(f"Starting image download for URL: {url}")
        os.makedirs(self.DOWNLOAD_FOLDER, exist_ok=True)
        result = subprocess.run(
            [
                "gallery-dl",
                "--write-metadata",
                "--write-info-json",
                "--cookies", "cookies.txt",  # Add cookies if needed for better access
                "--config", GALLERY_DL_CONFIG,
                url
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            metadata_files = [os.path.join(self.DOWNLOAD_FOLDER, f) for f in os.listdir(self.DOWNLOAD_FOLDER) 
                            if f.endswith('.json')]
            
            description = ""
            original_order = []
            
            if metadata_files:
                try:
                    with open(metadata_files[0], 'r', encoding='utf-8') as metadata_file:
                        metadata = json.load(metadata_file)
                        author = metadata.get('author', {})
                        author_nick = author.get('nick', '') or author.get('name', '')
                        content = metadata.get('content', '')
                        content = self.sanitize_description(content)
                        description = f"{author_nick}:\n\n{content}" if author_nick else content
                        
                        # Try to get original order from metadata
                        if isinstance(metadata, dict) and 'posts' in metadata:
                            for post in metadata['posts']:
                                if 'files' in post:
                                    original_order.extend([f['filename'] for f in post['files']])
                        logger.debug(f"Extracted original order from metadata: {original_order}")
                except Exception as e:
                    logger.error(f"Error parsing metadata: {e}")
            
            # Get all downloaded image files
            downloaded_files = [
                os.path.join(self.DOWNLOAD_FOLDER, f) for f in os.listdir(self.DOWNLOAD_FOLDER)
                if os.path.isfile(os.path.join(self.DOWNLOAD_FOLDER, f)) and 
                f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))
            ]
            
            if original_order:
                # Sort based on the original order from metadata
                sorted_files = []
                for original_name in original_order:
                    for file in downloaded_files:
                        if os.path.basename(file) == original_name or original_name in file:
                            sorted_files.append(file)
                            break
                
                # Add any remaining files that weren't in the original order
                remaining_files = [f for f in downloaded_files if f not in sorted_files]
                if remaining_files:
                    sorted_files.extend(sorted(remaining_files))
                    
                downloaded_files = sorted_files
            else:
                # Fallback to sorting by creation time if no metadata order is available
                downloaded_files.sort(key=lambda x: os.path.getctime(x))
            
            logger.debug(f"Final file order: {[os.path.basename(f) for f in downloaded_files]}")
            return downloaded_files, description
        else:
            logger.error(f"gallery-dl error: {result.stderr}")
        return [], ''

    def download_tweet_text(self, url):
        logger.info(f"Starting text download for URL: {url}")
        os.makedirs(self.DOWNLOAD_FOLDER, exist_ok=True)
        result = subprocess.run(
            ["gallery-dl", "--config", TEXT_CONFIG, url],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            text_files = [os.path.join(self.DOWNLOAD_FOLDER, f) for f in os.listdir(self.DOWNLOAD_FOLDER) 
                         if f.endswith('.txt')]
            
            content = ""
            if text_files:
                with open(text_files[0], 'r', encoding='utf-8') as text_file:
                    content = text_file.read()
                    content = self.sanitize_description(content)
            
            return content
        return ""

    def purge_folder(self, folder_path):
        logger.info(f"Purging folder: {folder_path}")
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            os.makedirs(folder_path, exist_ok=True)