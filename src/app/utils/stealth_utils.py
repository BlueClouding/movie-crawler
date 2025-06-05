"""
Utilities for setting up Playwright with stealth and anti-detection measures.
"""
import asyncio
import random
import time
from typing import Optional, Dict, Any
from pathlib import Path

from playwright.async_api import Page, BrowserContext, async_playwright
from playwright_stealth import stealth_async
from loguru import logger


class StealthBrowser:
    """
    A class to handle browser automation with stealth techniques to avoid detection.
    """
    
    def __init__(self, headless: bool = True, proxy: Optional[Dict] = None):
        """
        Initialize the StealthBrowser.
        
        Args:
            headless: Whether to run the browser in headless mode
            proxy: Optional proxy configuration
        """
        self.headless = headless
        self.proxy = proxy
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Start the browser with stealth configuration."""
        try:
            self.playwright = await async_playwright().start()
            
            # Launch browser with options
            launch_options = {
                'headless': self.headless,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                ],
            }
            
            if self.proxy:
                launch_options['proxy'] = self.proxy
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            
            # Create a new context with viewport settings
            self.context = await self.browser.new_context(
                viewport={
                    'width': random.randint(1366, 1920),
                    'height': random.randint(768, 1080),
                    'device_scale_factor': 1,
                },
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                color_scheme='light',
            )
            
            # Create a new page
            self.page = await self.context.new_page()
            
            # Apply stealth settings
            await stealth_async(self.page)
            
            # Set a random user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            ]
            await self.page.set_extra_http_headers({
                'User-Agent': random.choice(user_agents)
            })
            
            # Set random viewport size
            await self.page.set_viewport_size({
                'width': random.randint(1366, 1920),
                'height': random.randint(768, 1080)
            })
            
            # Set random geolocation
            await self.context.grant_permissions(['geolocation'])
            await self.context.set_geolocation({
                'latitude': random.uniform(-90, 90),
                'longitude': random.uniform(-180, 180),
                'accuracy': random.uniform(0, 1)
            })
            
            # Set timezone via CDP session (if needed)
            # Note: Timezone emulation is not directly supported in Playwright
            # Consider using a proxy service if timezone emulation is critical
            
            logger.info("Browser started with stealth configuration")
            return self.page
            
        except Exception as e:
            logger.error(f"Failed to start browser: {str(e)}")
            await self.close()
            raise
    
    async def close(self):
        """Close the browser and release resources."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error while closing browser: {str(e)}")
    
    async def human_like_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Simulate human-like delay between actions."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def human_like_scroll(self, page: Page, scroll_pause_time: float = 1.0):
        """Simulate human-like scrolling behavior."""
        viewport_height = await page.evaluate('window.innerHeight')
        total_height = await page.evaluate('document.body.scrollHeight')
        current_position = 0
        
        while current_position < total_height:
            # Random scroll distance (between 100 and 300 pixels)
            scroll_distance = random.randint(100, 300)
            current_position += scroll_distance
            
            # Scroll
            await page.evaluate(f'window.scrollBy(0, {scroll_distance})')
            
            # Random pause
            await self.human_like_delay(scroll_pause_time * 0.5, scroll_pause_time * 1.5)
            
            # Update total height in case of dynamic content loading
            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height > total_height:
                total_height = new_height
            
            # Random chance to scroll back up a bit
            if random.random() < 0.2 and current_position > viewport_height * 2:
                back_distance = random.randint(100, 300)
                current_position = max(0, current_position - back_distance)
                await page.evaluate(f'window.scrollBy(0, -{back_distance})')
                await self.human_like_delay(scroll_pause_time * 0.5, scroll_pause_time * 1.5)


async def test_stealth():
    """Test function to verify stealth configuration."""
    async with StealthBrowser(headless=False) as browser:
        page = browser.page
        
        # Navigate to bot detection test page
        await page.goto('https://bot.sannysoft.com/', timeout=60000)
        
        # Take a screenshot
        screenshot_path = 'bot_test.png'
        await page.screenshot(path=screenshot_path, full_page=True)
        logger.info(f"Screenshot saved to {screenshot_path}")
        
        # Wait for a while to check manually
        await asyncio.sleep(30)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_stealth())
