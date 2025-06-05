"""
Test script to verify the stealth browser functionality using Playwright.
"""
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from loguru import logger
from lxml import html
from playwright.async_api import Page

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.stealth_utils import StealthBrowser

BASE_URL = 'https://123av.com/ja/actresses'
MAX_PAGES = 5  # Limit for testing


@dataclass
class ActressInfo:
    """Data class to store actress information."""
    name: str
    works_count: str
    debut_year: str
    avatar_url: str
    profile_url: str = ""


def parse_html(content: str) -> List[ActressInfo]:
    """
    Parse HTML content and extract actress information.
    
    Args:
        content: HTML content to parse
        
    Returns:
        List of ActressInfo objects
    """
    actresses = []
    tree = html.fromstring(content)
    
    # Try multiple possible selectors for actress items
    items = tree.xpath('//div[contains(@class, "space-y-4")]')
    if not items:
        items = tree.xpath('//div[contains(@class, "actress-item")]')
    if not items:
        items = tree.xpath('//div[contains(@class, "grid")]//div[contains(@class, "group")]')
    
    for item in items:
        try:
            # Extract actress name
            name_elem = item.xpath('.//h4[contains(@class, "text-nord13")] | .//h3')
            name = name_elem[0].text_content().strip() if name_elem else 'Unknown'
            
            # Extract number of works
            works_elem = item.xpath('.//p[contains(@class, "text-nord10") and contains(text(), "条影片")] | .//p[contains(text(), "movies")]')
            works = works_elem[0].text_content().strip('\n ') if works_elem else '0'
            works = ''.join(filter(str.isdigit, works)) or '0'  # Extract only digits, default to '0'
            
            # Extract debut year
            debut_elem = item.xpath('.//p[contains(@class, "text-nord10") and contains(text(), "出道")] | .//p[contains(text(), "debut")]')
            debut = debut_elem[0].text_content().strip('\n ') if debut_elem else ''
            debut = ''.join(filter(str.isdigit, debut))  # Extract only digits
            
            # Extract avatar URL
            avatar_elem = item.xpath('.//img')
            avatar = avatar_elem[0].get('src', '') if avatar_elem else ''
            if avatar and not (avatar.startswith('http') or avatar.startswith('//')):
                avatar = f"https:{avatar}" if avatar.startswith('//') else f"{BASE_URL.rstrip('/')}/{avatar.lstrip('/')}"
            
            # Extract profile URL if available
            link_elem = item.xpath('.//a[@href]')
            profile_url = link_elem[0].get('href', '') if link_elem else ''
            if profile_url and not (profile_url.startswith('http') or profile_url.startswith('//')):
                profile_url = f"https:{profile_url}" if profile_url.startswith('//') else f"{BASE_URL.rstrip('/')}/{profile_url.lstrip('/')}"
            
            actresses.append(ActressInfo(
                name=name,
                works_count=works,
                debut_year=debut,
                avatar_url=avatar,
                profile_url=profile_url
            ))
            
        except Exception as e:
            logger.error(f"Error parsing actress item: {e}")
            continue
    
    return actresses


async def scrape_page(page: Page, page_num: int) -> List[ActressInfo]:
    """
    Scrape a single page of actresses.
    
    Args:
        page: Playwright page object
        page_num: Page number to scrape
        
    Returns:
        List of ActressInfo objects
    """
    try:
        # Navigate to the page
        url = BASE_URL if page_num == 1 else f"{BASE_URL}?page={page_num}"
        logger.info(f"Navigating to page {page_num}: {url}")
        
        response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        if not response or not response.ok:
            logger.warning(f"Failed to load page {page_num}: {response.status if response else 'No response'}")
            return []
        
        # Wait for content to load
        try:
            await asyncio.wait_for(
                page.wait_for_selector(
                    'div.grid.grid-cols-2.gap-4, div.grid.grid-cols-1.gap-4, div.actress-grid, div.actress-item, div.space-y-4',
                    timeout=15000,
                    state="attached"
                ),
                timeout=20
            )
        except (Exception, asyncio.TimeoutError):
            # Try scrolling to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            try:
                await page.wait_for_selector(
                    'div.grid.grid-cols-2.gap-4, div.grid.grid-cols-1.gap-4, div.actress-grid, div.actress-item, div.space-y-4',
                    timeout=15000,
                    state="attached"
                )
            except (Exception, asyncio.TimeoutError):
                logger.warning(f"Failed to find grid on page {page_num}")
                return []
        
        # Get page content and parse it
        html_content = await page.content()
        actresses = parse_html(html_content)
        
        # Log results
        for actress in actresses:
            logger.info(f"Found: {actress.name} - {actress.works_count} works, debut: {actress.debut_year}")
        
        return actresses
        
    except Exception as e:
        logger.error(f"Error scraping page {page_num}: {e}")
        return []


async def test_stealth_browser():
    """Test the StealthBrowser with the target website."""
    async with StealthBrowser(headless=False) as browser:
        page = browser.page
        
        # Enable request/response logging
        async def log_response(response):
            logger.debug(f"Response: {response.status} {response.url}")
        
        page.on("response", log_response)
        
        # Scrape multiple pages
        all_actresses = []
        for page_num in range(1, MAX_PAGES + 1):
            actresses = await scrape_page(page, page_num)
            if not actresses:
                logger.warning(f"No actresses found on page {page_num}, stopping")
                break
                
            all_actresses.extend(actresses)
            logger.info(f"Page {page_num} complete. Total actresses: {len(all_actresses)}")
            
            # Add a small delay between pages
            await asyncio.sleep(1)
        
        # Print summary
        logger.info(f"Scraping complete. Found {len(all_actresses)} actresses in total.")
        return all_actresses


if __name__ == "__main__":
    # Configure logging
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    logger.remove()
    logger.add(
        logs_dir / "stealth_test.log",
        rotation="10 MB",
        retention="10 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
    )
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Run the scraper
    try:
        asyncio.run(test_stealth_browser())
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.exception("An error occurred during scraping")

