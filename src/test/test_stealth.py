"""
Test script to verify the stealth browser functionality.
"""
import asyncio
import os
import sys
from pathlib import Path
from loguru import logger

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.stealth_utils import StealthBrowser, test_stealth


async def test_stealth_browser():
    """Test the StealthBrowser with bot detection test."""
    async with StealthBrowser(headless=False) as browser:
        page = browser.page
        
        # Navigate to bot detection test page
        logger.info("Navigating to bot detection test page...")
        await page.goto("https://bot.sannysoft.com/", timeout=60000)
        
        # Take a screenshot
        screenshots_dir = Path('screenshots')
        screenshots_dir.mkdir(exist_ok=True)
        screenshot_path = screenshots_dir / 'bot_test.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"Screenshot saved to {screenshot_path}")
        
        # Wait for manual verification
        logger.info("Please verify the screenshot to check if the browser is detected as a bot.")
        await asyncio.sleep(10)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        "logs/stealth_test.log",
        rotation="10 MB",
        retention="10 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
    )
    
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Run the test
    asyncio.run(test_stealth_browser())
