"""Image downloader module for downloading movie images."""

import logging
import os
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
import time
import random

class ImageDownloader:
    """Downloader for movie images."""
    
    def __init__(self, output_dir: str, max_retries: int = 3, delay: int = 1):
        """Initialize ImageDownloader.
        
        Args:
            output_dir: Directory to save images
            max_retries: Maximum number of retries for failed downloads
            delay: Delay between downloads in seconds
        """
        self._output_dir = output_dir
        self._max_retries = max_retries
        self._delay = delay
        self._logger = logging.getLogger(__name__)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    async def download_image(self, url: str, filename: str, session: Optional[aiohttp.ClientSession] = None) -> bool:
        """Download an image.
        
        Args:
            url: URL of the image
            filename: Filename to save the image as
            session: Optional aiohttp session
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not url:
            self._logger.error("Empty URL provided")
            return False
            
        filepath = os.path.join(self._output_dir, filename)
        
        # Skip if file already exists
        if os.path.exists(filepath):
            self._logger.debug(f"Image already exists: {filepath}")
            return True
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True
            
        try:
            for attempt in range(self._max_retries):
                try:
                    async with session.get(url, timeout=30) as response:
                        if response.status == 200:
                            with open(filepath, 'wb') as f:
                                f.write(await response.read())
                            self._logger.debug(f"Downloaded image: {url} -> {filepath}")
                            return True
                        else:
                            self._logger.warning(f"Failed to download image: {url}, HTTP {response.status}")
                except Exception as e:
                    self._logger.warning(f"Error downloading image (attempt {attempt+1}/{self._max_retries}): {url}, {str(e)}")
                    
                # Add delay before retry
                await asyncio.sleep(self._delay * (attempt + 1))
                
            self._logger.error(f"Failed to download image after {self._max_retries} attempts: {url}")
            return False
            
        finally:
            if close_session:
                await session.close()
    
    async def download_movie_images(self, movie_data: Dict[str, Any]) -> Dict[str, bool]:
        """Download all images for a movie.
        
        Args:
            movie_data: Movie data dictionary
            
        Returns:
            dict: Dictionary of image types and download status
        """
        if not movie_data.get('code'):
            self._logger.error("No movie code provided")
            return {'cover': False, 'thumbnails': False}
            
        movie_code = movie_data['code']
        movie_dir = os.path.join(self._output_dir, movie_code)
        os.makedirs(movie_dir, exist_ok=True)
        
        results = {}
        
        # Create a single session for all downloads
        async with aiohttp.ClientSession() as session:
            # Download cover image
            if movie_data.get('cover_image'):
                cover_filename = f"{movie_code}/cover.jpg"
                results['cover'] = await self.download_image(
                    movie_data['cover_image'], 
                    cover_filename,
                    session
                )
                # Add small delay
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
            # Download thumbnails
            if movie_data.get('thumbnails'):
                thumbnail_tasks = []
                for i, thumb_url in enumerate(movie_data['thumbnails']):
                    thumb_filename = f"{movie_code}/thumb_{i+1}.jpg"
                    # Add small random delay between thumbnail downloads
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    thumbnail_tasks.append(self.download_image(thumb_url, thumb_filename, session))
                
                if thumbnail_tasks:
                    thumbnail_results = await asyncio.gather(*thumbnail_tasks)
                    results['thumbnails'] = all(thumbnail_results)
                else:
                    results['thumbnails'] = False
        
        return results
