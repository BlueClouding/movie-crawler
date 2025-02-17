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
爬取的数据将保存在data/目录下，文件名为categories_时间戳.csv

## 注意事项
- 请遵守目标网站的robots.txt协议
- 适当调整请求频率，避免对服务器造成过大压力
