# 123AV Crawler

A multi-threaded web crawler for video information with resume capability and progress tracking, including specialized crawlers for various adult video websites.

## Features

- **MissAV Crawler**: Specialized crawler for extracting actress information from MissAV
- **Modular Architecture**: Clean separation of concerns with dedicated modules for different functionalities
- **Stealth Mode**: Uses Playwright with stealth plugins to avoid detection
- **Resume Support**: Can continue from where it left off
- **Progress Tracking**: Detailed logging and progress information

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Playwright browsers (installed automatically)

## Installation

1. Clone the repository:

    ```bash
    git clone <repository-url>
    cd 123av_crawler
    ```

2. Install dependencies:

    ```bash
    pip install -r requirements.txt

    # Install Playwright browsers
    playwright install
    ```

3. Run the MissAV crawler test:

    ```bash
    python -m src.test.test_missav_crawler
    ```

4. View results:
   - Logs: `missav_crawler_test.log`
   - Output: `output/` directory with JSON files containing actress data

## Project Structure

```text
123av_crawler/
├── README.md
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── __init__.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── crawlers/
│   │   │   ├── __init__.py
│   │   │   └── missav_crawler.py  # Main crawler implementation
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── stealth_utils.py   # Stealth browser utilities
│   │
│   └── test/
│       ├── __init__.py
│       └── test_missav_crawler.py  # Test script for the MissAV crawler
│
└── output/                       # Output directory for scraped data
    ├── missav_actresses_page1.json
    └── missav_actresses_all.json
```

## MissAV Crawler Usage

```python
from app.crawlers.missav_crawler import MissAVCrawler
import asyncio

async def main():
    async with MissAVCrawler(headless=False, max_pages=2) as crawler:
        # Get actresses from a specific page
        actresses = await crawler.get_actress_list(1)
        print(f"Found {len(actresses)} actresses on page 1")
        
        # Or scrape all pages
        async for page_num, page_actresses in crawler.scrape_all_pages():
            print(f"Page {page_num}: {len(page_actresses)} actresses")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

The MissAV crawler supports the following configuration options:

- `headless`: Run browser in headless mode (default: `True`)
- `max_pages`: Maximum number of pages to scrape (default: `10`)
- `timeout`: Page load timeout in milliseconds (default: `60000`)

## Notes

- Please respect the target website's `robots.txt` and terms of service
- Adjust request frequency to avoid overloading the server
- The crawler includes random delays to mimic human behavior
- For debugging, set `headless=False` to see the browser in action

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### 修改后的项目结构

```text
movie_database_project/
│
├── README.md
├── requirements.txt
├── .env
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── enums.py
│   │   ├── movie.py
│   │   ├── actress.py
│   │   ├── genre.py
│   │   ├── url.py
│   │   └── crawler.py
│   │
│   ├── repositories/           # 新增: Repository 层
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── movie_repository.py
│   │   ├── actress_repository.py
│   │   ├── genre_repository.py
│   │   ├── magnet_repository.py
│   │   ├── download_url_repository.py
│   │   ├── watch_url_repository.py
│   │   └── crawler_repository.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base_service.py
│   │   ├── movie_service.py
│   │   ├── actress_service.py
│   │   ├── genre_service.py
│   │   ├── magnet_service.py
│   │   ├── download_url_service.py
│   │   ├── watch_url_service.py
│   │   └── crawler_service.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── movies.py
│   │   │   ├── actresses.py
│   │   │   ├── genres.py
│   │   │   └── crawler.py
│   │   └── router.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── movie.py
│   │   ├── actress.py
│   │   ├── genre.py
│   │   └── crawler.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── crawler/
│   ├── __init__.py
│   ├── base_crawler.py
│   ├── movie_crawler.py
│   ├── genre_crawler.py
│   └── utils.py
│
├── scripts/
│   ├── create_tables.py
│   ├── import_data.py
│   └── example_usage.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_repositories.py  # 新增: Repository 测试
    ├── test_services.py
    └── test_api.py
```
