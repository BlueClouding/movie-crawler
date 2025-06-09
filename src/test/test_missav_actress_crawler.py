import sys
import time
import json
import random
import logging
import warnings
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from loguru import logger

# Suppress urllib3 OpenSSL warning
warnings.filterwarnings('ignore', message='.*urllib3 v2 only supports OpenSSL 1.1.1+.*')

# Configure logging
logger.remove()
logger.add(
    "logs/crawler.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}"
)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

class ActressCrawler:
    def __init__(self, max_pages: int = 5):
        """Initialize the crawler.
        
        Args:
            max_pages: Maximum number of pages to crawl
        """
        self.max_pages = max_pages
        self.session = self._create_session()
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for the request with a random user agent and browser-like headers.
        
        Returns:
            Dictionary of headers that mimic a real browser
        """
        # Common accept headers for modern browsers
        accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
        
        # Common languages for Japanese sites
        accept_language = 'ja,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6'
        
        # Get a random user agent
        user_agent = self._get_random_user_agent()
        
        # Common headers for Chrome/Firefox on Windows/macOS
        headers = {
            'User-Agent': user_agent,
            'Accept': accept,
            'Accept-Language': accept_language,
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://123av.com/ja/actresses',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Sec-GPC': '1',
        }
        
        return headers
        
    def _get_random_user_agent(self) -> str:
        """Return a random user agent to avoid detection."""
        user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            # Chrome on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/136.0',
            # Firefox on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/136.0',
            # Safari on macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0'
        ]
        return random.choice(user_agents)
    
    def _create_session(self):
        """Create and configure a requests session with retry strategy."""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        # Configure retry strategy with more aggressive settings
        retry_strategy = Retry(
            total=5,  # Increased from 3 to 5
            backoff_factor=1.5,  # Slightly increased backoff
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 527, 530],
            allowed_methods=["GET", "POST", "HEAD", "OPTIONS"],
            respect_retry_after_header=True
        )
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Increased from default of 10
            pool_maxsize=20,      # Increased from default of 10
            pool_block=False
        )
        
        # Mount the retry strategy to both http and https
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers using our _get_headers method
        session.headers.update(self._get_headers())
        
        # Configure session settings
        session.trust_env = False  # Don't read proxy settings from environment
        session.max_redirects = 5  # Limit redirects
        
        # Set cookies if available
        cookies = {
            'locale': 'ja',
            'DNT': '1',
            'Sec-GPC': '1',
            'over18': '1',  # Some adult sites require this
            'age_verified': '1'  # Another common adult site cookie
        }
        
        # Set cookies with proper domain handling
        for name, value in cookies.items():
            try:
                # Try with and without leading dot for domain
                for domain in ['123av.com', '.123av.com']:
                    try:
                        session.cookies.set(name, value, domain=domain, secure=True, httponly=True, samesite='Lax')
                    except Exception as e:
                        logger.debug(f"Couldn't set cookie {name} for domain {domain}: {e}")
            except Exception as e:
                logger.warning(f"Failed to set cookie {name}: {e}")
        
        # Add some common headers that might help with anti-bot detection
        session.headers.update({
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers',
        })
        
        # Set a default referer
        session.headers['Referer'] = 'https://123av.com/ja/genres'
        
        # Verify SSL but don't warn about it
        session.verify = True
        
        # Configure keep-alive
        session.keep_alive = True
        
        return session
    
    def _random_delay(self, min_seconds: float = 2.0, max_seconds: float = 5.0):
        """Random delay between requests to avoid being blocked.
        
        Args:
            min_seconds: Minimum delay in seconds
            max_seconds: Maximum delay in seconds
        """
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)
        
        # Occasionally wait longer to simulate human behavior
        if random.random() < 0.2:  # 20% chance
            extra_delay = random.uniform(3, 8)
            logger.debug(f"Additional wait time: {extra_delay:.2f} seconds")
            time.sleep(extra_delay)
    
    def fetch_page(self, url: str, max_retries: int = 5) -> Optional[str]:
        """Fetch a single page with advanced retry logic and request management.
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
            
        Returns:
            HTML content as string if successful, None otherwise
        """
        last_exception = None
        
        # Update headers with fresh values
        self.session.headers.update(self._get_headers())
        
        # Add cache-busting parameter to URL if it's a GET request and doesn't already have query params
        parsed_url = requests.utils.urlparse(url)
        if not parsed_url.query and parsed_url.scheme in ('http', 'https'):
            cache_buster = int(time.time())
            url = f"{url}?_={cache_buster}"
        
        for attempt in range(max_retries):
            try:
                # Add progressive delay between retries
                if attempt > 0:
                    delay = min((2 ** attempt) + random.uniform(0, 1), 300)  # Cap at 5 minutes
                    logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s delay...")
                    time.sleep(delay)
                
                # Update referer to the previous URL if available
                if hasattr(self, 'last_url') and self.last_url:
                    self.session.headers['Referer'] = self.last_url
                
                logger.debug(f"Fetching {url} (attempt {attempt + 1}/{max_retries})")
                
                # Make the request with timeout and streaming
                response = self.session.get(
                    url,
                    timeout=(10, 30),  # Connect timeout, read timeout
                    allow_redirects=True,
                    verify=True,  # Now we verify SSL certificates
                    stream=True,  # Stream response to handle large files
                    headers={
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                    }
                )
                
                # Store the current URL as last_url for the next request
                self.last_url = response.url
                
                # Check if request was successful
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    logger.warning(f"Unexpected content type: {content_type}")
                    continue
                
                # Read response with size limit (10MB)
                content = b''
                max_size = 10 * 1024 * 1024  # 10MB
                for chunk in response.iter_content(chunk_size=8192):
                    content += chunk
                    if len(content) > max_size:
                        raise ValueError(f"Response too large (> {max_size} bytes)")
                
                # Decode with proper handling
                try:
                    # Try UTF-8 first
                    html = content.decode('utf-8')
                except UnicodeDecodeError:
                    # Fall back to other common encodings
                    for encoding in ['shift_jis', 'euc-jp', 'iso-2022-jp', 'cp932']:
                        try:
                            html = content.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        raise ValueError("Could not decode response with any standard encoding")
                
                # Check for error pages or CAPTCHAs
                if any(marker in html.lower() for marker in ['captcha', 'cloudflare', 'access denied', '403 forbidden']):
                    raise requests.exceptions.RequestException("CAPTCHA or blocking detected")
                
                # Check for reasonable content length
                if len(html) < 1000:  # Arbitrary threshold
                    logger.warning(f"Suspiciously small response ({len(html)} bytes)")
                
                return html
                
            except requests.exceptions.SSLError as e:
                last_exception = e
                logger.warning(f"SSL Error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error("SSL verification failed after all retries")
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Timeout (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error("Request timed out after all retries")
                
            except requests.exceptions.TooManyRedirects as e:
                last_exception = e
                logger.error(f"Too many redirects: {e}")
                break  # Don't retry on redirect loops
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Handle rate limiting and server errors
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                    logger.warning(f"HTTP {status_code} error")
                    
                    # Special handling for common status codes
                    if status_code == 429:  # Too Many Requests
                        retry_after = int(e.response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                        time.sleep(retry_after)
                        continue
                    elif status_code in [500, 502, 503, 504]:  # Server errors
                        wait_time = min(60 * (attempt + 1), 300)  # Cap at 5 minutes
                        logger.warning(f"Server error. Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    elif status_code == 403:  # Forbidden
                        logger.error("Access forbidden. The IP might be blocked.")
                        # Consider rotating proxy here if available
                        break
                    elif status_code == 404:  # Not Found
                        logger.error("Page not found (404)")
                        break  # No point in retrying
                
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error (attempt {attempt + 1}/{max_retries}): {e}", exc_info=True)
                
                # For certain errors, we might want to give up immediately
                if isinstance(e, (KeyboardInterrupt, SystemExit, MemoryError)):
                    raise
                
                # For other unexpected errors, use exponential backoff
                time.sleep(min(2 ** attempt, 60))
        
        # If we've exhausted all retries, log the final error
        if last_exception:
            logger.error(f"Failed to fetch {url} after {max_retries} attempts. Last error: {last_exception}")
        
        return None
    
    def parse_actress_page(self, html: str) -> List[Dict]:
        """Parse the HTML content and extract actress information with improved error handling.
        
        Args:
            html: HTML content of the page
            
        Returns:
            List of dictionaries containing actress information
        """
        if not html or not html.strip():
            logger.warning("Empty or invalid HTML content")
            return []
        
        try:
            # Try different parsers if lxml fails
            try:
                soup = BeautifulSoup(html, 'lxml')
            except Exception as e:
                logger.warning(f"lxml parser failed, falling back to html.parser: {e}")
                soup = BeautifulSoup(html, 'html.parser')
            
            actresses = []
            
            # Try different selectors to find actress items
            selectors = [
                'div.actress-item',                # Direct item class
                'div.grid > div',                  # Grid layout
                'div.space-y-4 > div',             # Common grid layout
                'div.relative',                    # Common container
                'div[class*="actress"]',          # Class contains 'actress'
                'div[class*="item"]',             # Generic item class
                'div.card',                        # Card layout
                'div[data-testid*="actress"]',    # Test ID based
                'div[class*="grid"] > div',        # Generic grid
                'div[class*="list"] > div'         # Generic list
            ]
            
            items = []
            for selector in selectors:
                found_items = soup.select(selector)
                if found_items:
                    logger.debug(f"Found {len(found_items)} items with selector: {selector}")
                    items = found_items
                    # Don't break, try to find more specific selectors
            
            if not items:
                # Fallback: Find all divs with links that might contain actress info
                potential_items = []
                for div in soup.find_all('div', recursive=True):
                    if div.find('a') and (div.find('img') or any('actress' in str(c).lower() for c in div.get('class', []))):
                        potential_items.append(div)
                
                if potential_items:
                    logger.debug(f"Found {len(potential_items)} potential items using fallback method")
                    items = potential_items
                else:
                    logger.warning("No actress items found on the page")
                    return []
            
            for item in items:
                try:
                    # Extract name - try multiple strategies
                    name = None
                    name_selectors = [
                        'h4', 'h3', 'h2', 'h1',  # Common header tags
                        '.name', '.title', '.actress-name',  # Common class names
                        '[class*="name"]', '[class*="title"]',  # Partial class matches
                        'a[href*="actress"]',  # Links that might contain actress names
                        'strong', 'b', 'span'  # Common text containers
                    ]
                    
                    for selector in name_selectors:
                        name_elem = item.select_one(selector)
                        if name_elem and name_elem.get_text(strip=True):
                            name = name_elem.get_text(strip=True)
                            break
                    
                    # If still no name, try to find any text that looks like a name
                    if not name:
                        text = item.get_text(' ', strip=True)
                        if len(text) < 100:  # Arbitrary length limit to avoid large blocks
                            name = ' '.join(text.split()[:3])  # First few words as name
                    
                    name = name or "Unknown Actress"
                    
                    # Extract works count - look for numbers that might represent work counts
                    works = "0"
                    works_text = item.get_text()
                    import re
                    works_match = re.search(r'(\d+)\s*(?:部|作品|movies|works|videos)', works_text, re.IGNORECASE)
                    if works_match:
                        works = works_match.group(1)
                    
                    # Extract avatar URL
                    avatar_url = ""
                    img = item.find('img')
                    if img:
                        for attr in ['src', 'data-src', 'data-lazy-src', 'data-original']:
                            if img.has_attr(attr):
                                avatar_url = img[attr]
                                if avatar_url and not (avatar_url.startswith(('http:', 'https:')) or avatar_url.startswith('//')):
                                    avatar_url = f"https:{avatar_url}" if avatar_url.startswith('//') else f"https://123av.com{avatar_url}"
                                break
                    
                    # Extract profile URL
                    profile_url = ""
                    link = item.find('a', href=True)
                    if link:
                        profile_url = link['href']
                        if profile_url and not (profile_url.startswith(('http:', 'https:')) or profile_url.startswith('//')):
                            profile_url = f"https:{profile_url}" if profile_url.startswith('//') else f"https://123av.com{profile_url}"
                    
                    # Only add if we have at least a name or profile URL
                    if name != "Unknown Actress" or profile_url:
                        actress_data = {
                            "name": name,
                            "works_count": works,
                            "avatar_url": avatar_url,
                            "profile_url": profile_url,
                            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        actresses.append(actress_data)
                        
                except Exception as e:
                    logger.warning(f"Error parsing actress item: {e}", exc_info=True)
                    continue
            
            logger.info(f"Successfully parsed {len(actresses)} actresses from the page")
            return actresses
            
        except Exception as e:
            logger.error(f"Failed to parse page: {e}", exc_info=True)
            return []
    
    def crawl(self, base_url: str = "https://123av.com/ja/actresses") -> List[Dict]:
        """Crawl multiple pages and collect actress data with improved error handling.
        
        Args:
            base_url: Base URL to start crawling from
            
        Returns:
            List of all actresses found, with duplicates removed
        """
        from collections import defaultdict
        import time
        
        all_actresses = []
        seen_actresses = set()  # To track duplicates
        consecutive_errors = 0
        max_consecutive_errors = 3
        start_time = time.time()
        
        try:
            # First, visit the homepage to set initial cookies
            logger.info("Visiting homepage to set initial cookies...")
            self.fetch_page("https://123av.com/")
            self._random_delay(min_seconds=2.0, max_seconds=5.0)
            
            # Create output directories if they don't exist
            Path("output").mkdir(exist_ok=True)
            Path("logs").mkdir(exist_ok=True)
            
            logger.info(f"Starting crawl of up to {self.max_pages} pages from {base_url}")
            
            for page in range(1, self.max_pages + 1):
                page_start_time = time.time()
                page_retry_count = 0
                max_page_retries = 2
                page_success = False
                
                while page_retry_count <= max_page_retries and not page_success:
                    try:
                        # Add random delay between page requests, longer for subsequent pages
                        if page > 1:
                            delay = random.uniform(3.0, 8.0) * (1 + (page_retry_count * 0.5))  # Increase delay with retries
                            logger.debug(f"Waiting {delay:.1f}s before next page...")
                            time.sleep(delay)
                        
                        # Build URL with cache-busting parameter
                        cache_buster = int(time.time())
                        url = f"{base_url}?page={page}&_={cache_buster}" if page > 1 else f"{base_url}?_={cache_buster}"
                        
                        logger.info(f"Crawling page {page}/{self.max_pages} (attempt {page_retry_count + 1}/{max_page_retries + 1}): {url}")
                        
                        # Fetch and parse the page
                        html = self.fetch_page(url)
                        if not html:
                            raise ValueError("Empty response received")
                        
                        # Check for captcha or blocking
                        if any(marker in html.lower() for marker in ["captcha", "cloudflare", "access denied", "403 forbidden"]):
                            raise Exception("CAPTCHA or blocking detected")
                        
                        # Parse the page
                        actresses = self.parse_actress_page(html)
                        
                        if not actresses:
                            if page_retry_count < max_page_retries:
                                logger.warning(f"No actresses found on page {page}. Retrying...")
                                page_retry_count += 1
                                continue
                            else:
                                logger.warning(f"No actresses found on page {page} after {max_page_retries} attempts. This might be the last page.")
                                page_success = True  # Consider this a success to continue to next page
                                break
                        
                        # Filter out duplicates and add new actresses
                        new_actresses = []
                        for actress in actresses:
                            # Create a unique key based on name and profile URL
                            profile_url = actress.get('profile_url', '')
                            name = actress.get('name', '').strip()
                            
                            if not name and not profile_url:
                                continue  # Skip invalid entries
                                
                            key = f"{name.lower()}:{profile_url}"
                            if key not in seen_actresses:
                                seen_actresses.add(key)
                                new_actresses.append(actress)
                        
                        if new_actresses:
                            all_actresses.extend(new_actresses)
                            logger.success(f"Page {page}: Found {len(new_actresses)} new actresses (total: {len(all_actresses)})")
                            
                            # Save results after each successful page
                            self.save_results(all_actresses, f"page_{page}")
                        else:
                            logger.info(f"Page {page}: No new actresses found")
                        
                        page_success = True
                        consecutive_errors = 0  # Reset error counter on success
                        
                    except requests.exceptions.RequestException as e:
                        page_retry_count += 1
                        status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                        
                        if status_code == 404 and page > 1:  # Likely reached the last page
                            logger.info(f"Received 404 on page {page}, assuming this is the last page")
                            page_success = True  # Consider this a normal termination
                            break
                            
                        if page_retry_count > max_page_retries:
                            logger.error(f"Failed to fetch page {page} after {max_page_retries} attempts: {e}")
                            consecutive_errors += 1
                            if consecutive_errors >= max_consecutive_errors:
                                logger.error(f"Too many consecutive errors ({consecutive_errors}). Stopping...")
                                raise
                        else:
                            retry_delay = min(30 * (2 ** page_retry_count), 300)  # Exponential backoff, max 5 minutes
                            logger.warning(f"Request failed (attempt {page_retry_count}/{max_page_retries}). Retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                    
                    except Exception as e:
                        page_retry_count += 1
                        logger.error(f"Error processing page {page} (attempt {page_retry_count}/{max_page_retries + 1}): {e}", 
                                   exc_info=page_retry_count > max_page_retries)  # Full traceback only on final attempt
                        
                        if page_retry_count > max_page_retries:
                            consecutive_errors += 1
                            if consecutive_errors >= max_consecutive_errors:
                                logger.error(f"Too many consecutive errors ({consecutive_errors}). Stopping...")
                                raise
                        
                        # Add delay before retry
                        time.sleep(5 * page_retry_count)
                
                # Add page processing time to log
                page_time = time.time() - page_start_time
                logger.debug(f"Page {page} processed in {page_time:.1f} seconds")
                
                # If we had too many consecutive errors, stop the crawl
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Stopping due to {consecutive_errors} consecutive errors")
                    break
            
            logger.success(f"Crawling completed. Found {len(all_actresses)} unique actresses in {time.time() - start_time:.1f} seconds")
            return all_actresses
            
        except KeyboardInterrupt:
            logger.warning("Crawling interrupted by user")
            return all_actresses
            
        except Exception as e:
            logger.error(f"Fatal error during crawling: {e}", exc_info=True)
            return all_actresses
            
        finally:
            # Always save the final results
            if all_actresses:
                try:
                    self.save_results(all_actresses, "final")
                    logger.info(f"Saved final results with {len(all_actresses)} actresses")
                except Exception as e:
                    logger.error(f"Error saving final results: {e}", exc_info=True)
                
        return all_actresses
    
    def save_results(self, data: List[Dict], page_num: int | str):
        """Save the scraped data to a JSON file with error handling and backup.
        
        Args:
            data: List of actress dictionaries
            page_num: Current page number or identifier (can be string or int)
        """
        if not data:
            logger.warning("No data to save")
            return
            
        output_dir = Path("output")
        
        try:
            # Create output directory if it doesn't exist
            output_dir.mkdir(exist_ok=True, parents=True)
            
            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"actresses_{timestamp}_page{page_num}.json"
            output_file = output_dir / filename
            
            # Create a temporary file first
            temp_file = output_file.with_suffix('.tmp')
            
            # Write to temporary file
            with temp_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            
            # Rename temp file to final filename (atomic operation)
            temp_file.replace(output_file)
            
            logger.success(f"Successfully saved {len(data)} actresses to {output_file}")
            
            # Create a symlink to the latest file for easier access
            latest_link = output_dir / "latest.json"
            try:
                if latest_link.is_symlink() or latest_link.exists():
                    latest_link.unlink()
                latest_link.symlink_to(output_file.name)
            except OSError as e:
                logger.warning(f"Could not create latest.json symlink: {e}")
                
        except Exception as e:
            logger.error(f"Error saving results to {output_file}: {e}")
            
            # Try to save to a backup location if the primary save fails
            try:
                backup_dir = Path("backup_output")
                backup_dir.mkdir(exist_ok=True, parents=True)
                
                backup_file = backup_dir / f"backup_actresses_{int(time.time())}.json"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"Saved backup to {backup_file}")
                
            except Exception as backup_error:
                logger.critical(f"Failed to save backup: {backup_error}")
                
                # As a last resort, print a portion of the data
                try:
                    sample = data[:min(3, len(data))]
                    logger.debug(f"Sample data (first {len(sample)} items): {json.dumps(sample, ensure_ascii=False, indent=2)}")
                except:
                    logger.critical("Could not log sample data")

def main():
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    
    try:
        # Initialize and run the crawler
        crawler = ActressCrawler(max_pages=5)
        results = crawler.crawl()
        
        if results:
            logger.success(f"Scraping completed! Found {len(results)} actresses in total.")
        else:
            logger.warning("No data was scraped.")
            
    except KeyboardInterrupt:
        logger.info("Crawling interrupted by user")
    except Exception as e:
        logger.exception("An error occurred during crawling")
    finally:
        logger.info("Crawling session ended")

if __name__ == "__main__":
    main()