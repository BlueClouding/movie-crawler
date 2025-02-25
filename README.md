# 123AV Crawler

A multi-threaded web crawler for video information with resume capability and progress tracking.

## Prerequisites

- Python 3.8+
- PostgreSQL 15
- pip (Python package manager)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd 123av_crawler
```

2. 运行爬虫

```bash
python main.py
```

3. 查看结果
   爬取的数据将保存在 data/目录下，文件名为 categories\_时间戳.csv

## 注意事项

- 请遵守目标网站的 robots.txt 协议
- 适当调整请求频率，避免对服务器造成过大压力

### 修改后的项目结构

```
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
