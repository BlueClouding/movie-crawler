"""
MissAV crawler for scraping actress data from missav.ai
"""
import asyncio
import datetime
import json
import logging
import os
import random
import sys
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

from lxml import etree
from playwright.async_api import Page, Playwright, async_playwright, TimeoutError as PlaywrightTimeoutError

from app.utils.stealth_utils import StealthBrowser

logger = logging.getLogger(__name__)

class MissAVCrawler:
    """Crawler for MissAV website."""
    
    BASE_URL = 'https://missav.ai'
    ACTRESS_LIST_URL = f"{BASE_URL}/ja/actresses"
    
    def __init__(self, headless: bool = False, max_pages: int = 1):
        """Initialize the crawler.
        
        Args:
            headless: Whether to run browser in headless mode
            max_pages: Maximum number of pages to scrape
        """
        self.headless = headless
        self.max_pages = max_pages
        self.browser = None
        self.page = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Start the browser and create a new page."""
        self.browser = StealthBrowser(headless=self.headless)
        await self.browser.start()
        self.page = self.browser.page
        logger.info("Browser started")
    
    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
    
    async def _random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Wait for a random amount of time to mimic human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def _scroll_page(self):
        """Scroll the page randomly to mimic human behavior."""
        viewport_height = await self.page.evaluate('window.innerHeight')
        scroll_amount = random.randint(
            int(viewport_height * 0.25),
            int(viewport_height * 0.75)
        )
        await self.page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await self._random_delay(0.5, 1.5)
    
    async def get_actress_list(self, page_num: int = 1) -> List[Dict]:
        """Get list of actresses from a specific page.
        
        Args:
            page_num: Page number to scrape (1-based)
            
        Returns:
            List of actress dictionaries with name, profile_url, etc.
        """
        actresses = []
        is_first_page = page_num == 1
        url = f"{self.ACTRESS_LIST_URL}?page={page_num}" if not is_first_page else self.ACTRESS_LIST_URL
        
        try:
            logger.info(f"Scraping page {page_num}: {url}")
            
            # Navigate to the page with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Clear cache and cookies for the first page to avoid any stale data
                    if is_first_page and attempt == 0:
                        await self.page.context.clear_cookies()
                    
                    # Navigate to the URL with a fresh state
                    await self.page.goto(
                        url, 
                        timeout=60000,
                        wait_until="domcontentloaded"
                    )
                    
                    # Wait for the content to load with multiple possible selectors
                    try:
                        await asyncio.wait_for(
                            self.page.wait_for_selector(
                                'div.grid.grid-cols-2.gap-4, div.grid.grid-cols-1.gap-4, div.actress-grid, div.actress-item',
                                timeout=15000,
                                state="attached"
                            ),
                            timeout=20
                        )
                    except (PlaywrightTimeoutError, asyncio.TimeoutError):
                        # If we can't find the grid, try to scroll down to trigger lazy loading
                        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(2)  # Wait for any lazy loading
                        
                        # Try to find the grid again
                        try:
                            await self.page.wait_for_selector(
                                'div.grid.grid-cols-2.gap-4, div.grid.grid-cols-1.gap-4, div.actress-grid, div.actress-item',
                                timeout=5000,
                                state="attached"
                            )
                        except (PlaywrightTimeoutError, asyncio.TimeoutError):
                            if is_first_page:
                                # If it's the first page and we still can't find the grid, try to reload
                                await self.page.reload(wait_until="domcontentloaded")
                                await asyncio.sleep(2)
                            else:
                                raise
                    
                    # Check if we're on a captcha page or error page
                    title = await self.page.title()
                    if any(term in title.lower() for term in ['captcha', 'error', 'not found', '404']):
                        raise Exception(f"Detected {title} page")
                    
                    break  # Successfully loaded the page
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to load page {page_num} after {max_retries} attempts")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying...")
                    await self._random_delay(2, 5)
            
            # Scroll randomly to mimic human behavior
            for _ in range(random.randint(2, 5)):
                await self._scroll_page()
                await self._random_delay(0.5, 1.5)
            
            # Get page content and parse with lxml
            content = await self.page.content()
            tree = etree.HTML(content)
            
            # Initialize cards variable
            cards = []
            
            # Try multiple possible selectors for actress cards using lxml
            card_selectors = [
                '//div[contains(@class, "grid") and contains(@class, "grid-cols-2")]//a',
                '//div[contains(@class, "grid")]//div[contains(@class, "group")]//a',
                '//div[contains(@class, "actress-item")]//a',
                '//div[contains(@class, "actress")]//a',
                '//a[contains(@class, "actress-link")]',
                '//div[contains(@class, "grid")]//a[.//img]',  # Links containing images
                '//div[contains(@class, "item")]//a[.//img]',  # Generic item with image
                '//div[contains(@class, "card")]//a[.//img]',  # Card with image
                '//a[.//img][.//div]'  # Link with image and div (common pattern)
            ]
            
            # Try lxml selectors first
            for selector in card_selectors:
                cards = tree.xpath(selector)
                if cards:
                    logger.debug(f"Found {len(cards)} cards with lxml selector: {selector}")
                    break
            
            # If lxml didn't find anything, try Playwright selectors
            if not cards:
                playwright_selectors = [
                    'div.grid a',
                    'div.actress-item a',
                    'a[href*="actress"]',
                    'div.grid > div > a',
                    'div.item a',
                    'div.card a'
                ]
                
                for selector in playwright_selectors:
                    try:
                        playwright_cards = await self.page.query_selector_all(selector)
                        if playwright_cards:
                            logger.debug(f"Found {len(playwright_cards)} cards with Playwright selector: {selector}")
                            # Convert Playwright elements to lxml elements
                            card_htmls = [await card.inner_html() for card in playwright_cards]
                            cards = [etree.HTML(f"<div>{html}</div>") for html in card_htmls]
                            break
                    except Exception as e:
                        logger.debug(f"Playwright selector '{selector}' failed: {e}")
                        continue
            
            if not cards:
                logger.warning(f"No actress cards found on page {page_num}")
                logger.debug(f"Page content: {content[:1000]}...")  # Log first 1000 chars for debugging
                return []
            
            logger.info(f"Found {len(cards)} actress cards on page {page_num}")
            
            for card in cards:
                try:
                    # Get the card HTML for debugging
                    card_html = etree.tostring(card, encoding='unicode', pretty_print=True)[:500] + "..."
                    
                    # Try multiple possible selectors for name
                    name = None
                    name_selectors = [
                        './/div[contains(@class, "text-sm")]',
                        './/h1',
                        './/h2',
                        './/h3',
                        './/h4',
                        './/div[contains(@class, "name")]',
                        './/div[contains(@class, "title")]',
                        './/span[contains(@class, "name")]',
                        './/span[contains(@class, "title")]',
                        './/*[contains(@class, "name")]',
                        './/*[contains(@class, "title")]',
                        './/*[contains(@class, "text-")]',  # Any text element
                        './/*[text()]'  # Any element with text
                    ]
                    
                    # First try to find name in text nodes
                    name_candidates = card.xpath('.//text()')
                    for candidate in name_candidates:
                        candidate = candidate.strip()
                        if (len(candidate) > 2 and 
                            len(candidate) < 50 and 
                            not any(c in candidate for c in ['<', '>', '{', '}', '[', ']', '|', '\\', '/', ':', ';'])):
                            name = candidate
                            break
                    
                    # If no name found, try selectors
                    if not name:
                        for selector in name_selectors:
                            try:
                                name_elems = card.xpath(selector)
                                if name_elems and name_elems[0].text and name_elems[0].text.strip():
                                    name = name_elems[0].text.strip()
                                    if 2 < len(name) < 50:  # Reasonable name length
                                        break
                                    name = None  # Reset if invalid length
                            except Exception as e:
                                logger.debug(f"Name selector '{selector}' failed: {e}")
                    
                    if not name:
                        logger.warning(f"Could not extract actress name from card: {card_html}")
                        continue
                    
                    # Clean up the name
                    name = ' '.join(name.split())  # Normalize whitespace
                    
                    # Get profile URL - try multiple locations
                    profile_url = ""
                    url_selectors = [
                        './/@href',  # Direct href
                        './/a[1]/@href',  # First link
                        './/a[contains(@href, "actress")]/@href',
                        './/a[contains(@href, "star")]/@href',
                        './/a[contains(@href, "id")]/@href'
                    ]
                    
                    for selector in url_selectors:
                        try:
                            urls = card.xpath(selector)
                            if urls and urls[0].strip():
                                profile_url = urljoin(self.BASE_URL, urls[0].strip())
                                if profile_url != self.BASE_URL:  # Make sure it's a valid URL
                                    break
                        except Exception as e:
                            logger.debug(f"URL selector '{selector}' failed: {e}")
                    
                    # Extract additional info if available
                    info = ""
                    info_selectors = [
                        './/div[contains(@class, "text-xs")]',
                        './/div[contains(@class, "info")]',
                        './/div[contains(@class, "description")]',
                        './/p',
                        './/span[contains(@class, "info")]',
                        './/*[contains(@class, "info")]',
                        './/*[contains(@class, "description")]',
                        './/*[contains(@class, "text-")]'  # Any text element
                    ]
                    
                    for selector in info_selectors:
                        try:
                            info_elems = card.xpath(f'{selector}/text()')
                            if info_elems:
                                info = ' '.join(e.strip() for e in info_elems if e.strip())
                                if info and len(info) < 500:  # Filter out too long text
                                    break
                        except Exception as e:
                            logger.debug(f"Info selector '{selector}' failed: {e}")
                    
                    # Clean up info
                    info = ' '.join(info.split()) if info else ""
                    
                    # Extract image URL if available
                    img_url = ""
                    img_selectors = [
                        './/img/@src',
                        './/img/@data-src',
                        './/img/@data-lazy-src',
                        './/img/@data-original',
                        './/div[contains(@class, "image")]//img/@src',
                        './/div[contains(@class, "thumb")]//img/@src',
                        './/img[1]/@src',  # First image in the card
                        './/*[contains(@class, "image")]//@src',
                        './/*[contains(@class, "thumb")]//@src'
                    ]
                    
                    for selector in img_selectors:
                        try:
                            img_elems = card.xpath(selector)
                            if img_elems and img_elems[0].strip():
                                img_url = urljoin(self.BASE_URL, img_elems[0].strip())
                                if img_url and img_url != self.BASE_URL:  # Make sure it's a valid URL
                                    # Check if it's a data URL or placeholder
                                    if not (img_url.startswith('data:') or 'placeholder' in img_url.lower()):
                                        break
                                    img_url = ""  # Reset if it's a data URL or placeholder
                        except Exception as e:
                            logger.debug(f"Image selector '{selector}' failed: {e}")
                    
                    # Skip if we don't have enough data
                    if not name and not img_url and not profile_url:
                        logger.warning(f"Skipping card with insufficient data: {card_html}")
                        continue
                    
                    actress_data = {
                        'name': name,
                        'profile_url': profile_url,
                        'info': info,
                        'image_url': img_url,
                        'source': 'missav',
                        'page_num': page_num,
                        'scraped_at': datetime.datetime.utcnow().isoformat(),
                        'card_html': card_html  # For debugging
                    }
                    
                    actresses.append(actress_data)
                    
                except Exception as e:
                    logger.error(f"Error parsing actress card: {e}", exc_info=True)
                    logger.debug(f"Card HTML: {card_html}" if 'card_html' in locals() else "No card HTML available")
                    continue
            
            logger.info(f"Successfully extracted {len(actresses)} actresses from page {page_num}")
            return actresses
            
        except (PlaywrightTimeoutError, asyncio.TimeoutError):
            logger.error(f"Timeout while loading page {page_num}")
            return []
        except Exception as e:
            logger.error(f"Error scraping page {page_num}: {str(e)}", exc_info=True)
            return []
    
    async def scrape_all_pages(self) -> AsyncGenerator[Tuple[int, List[Dict]], None]:
        """Scrape all pages of actresses.
        
        Yields:
            Tuple of (page_number, list_of_actresses) for each page
        """
        page_num = 1
        has_more_pages = True
        
        try:
            while has_more_pages and page_num <= self.max_pages:
                logger.info(f"Processing page {page_num}...")
                actresses = await self.get_actress_list(page_num)
                
                if not actresses:
                    logger.warning(f"No actresses found on page {page_num}, stopping pagination")
                    break
                    
                yield page_num, actresses
                
                # Check if there's a next page
                if page_num >= self.max_pages:
                    logger.info("Reached maximum number of pages to scrape")
                    break
                    
                # Add a random delay between pages
                delay = random.uniform(3, 8)
                logger.debug(f"Waiting {delay:.2f} seconds before next page...")
                await asyncio.sleep(delay)
                
                page_num += 1
                
        except Exception as e:
            logger.error(f"Error in scrape_all_pages: {str(e)}", exc_info=True)
            raise


async def main():
    """Main function to test the crawler."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('missav_crawler.log', encoding='utf-8')
        ]
    )
    
    # Create output directory if it doesn't exist
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize crawler with headless=False so we can see what's happening
        async with MissAVCrawler(headless=False, max_pages=2) as crawler:
            all_actresses = []
            start_time = datetime.datetime.now()
            
            logger.info("=" * 50)
            logger.info(f"Starting MissAV crawler at {start_time}")
            logger.info("=" * 50)
            
            try:
                async for page_num, actresses in enumerate(crawler.scrape_all_pages(), 1):
                    all_actresses.extend(actresses)
                    logger.info(f"Page {page_num}: Added {len(actresses)} actresses (Total: {len(all_actresses)})")
                    
                    # Save progress after each page
                    if actresses:  # Only save if we got data
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_file = os.path.join(output_dir, f'missav_actresses_page{page_num}_{timestamp}.json')
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(actresses, f, ensure_ascii=False, indent=2)
                        
                        logger.info(f"Saved {len(actresses)} actresses to {output_file}")
                
                # Save complete results
                if all_actresses:
                    end_time = datetime.datetime.now()
                    duration = (end_time - start_time).total_seconds() / 60  # in minutes
                    
                    # Create a summary
                    summary = {
                        'metadata': {
                            'source': 'missav.ai',
                            'start_time': start_time.isoformat(),
                            'end_time': end_time.isoformat(),
                            'duration_minutes': round(duration, 2),
                            'total_actresses': len(all_actresses),
                            'pages_scraped': page_num
                        },
                        'actresses': all_actresses
                    }
                    
                    # Save complete results
                    final_output = os.path.join(output_dir, f'missav_actresses_complete_{timestamp}.json')
                    with open(final_output, 'w', encoding='utf-8') as f:
                        json.dump(summary, f, ensure_ascii=False, indent=2)
                    
                    logger.info("=" * 50)
                    logger.info(f"Crawling completed in {duration:.2f} minutes")
                    logger.info(f"Total actresses collected: {len(all_actresses)}")
                    logger.info(f"Results saved to: {final_output}")
                    logger.info("=" * 50)
                else:
                    logger.warning("No actresses were scraped. Check the logs for errors.")
                    
            except Exception as e:
                logger.error(f"An error occurred during crawling: {str(e)}", exc_info=True)
                raise
                
    except Exception as e:
        logger.critical(f"Fatal error in crawler: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
