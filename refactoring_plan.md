# 123_crawler 代码重构计划

## 问题分析

1. **重复文件**:
   - `src/crawler/utils/progress_manager.py`
   - `src/crawler/core/progress_manager.py`
   这两个文件有重叠功能，需要合并。

2. **过长文件**:
   - `src/crawler/core/detail_crawler.py` (767行)
   - `src/crawler/core/genre_processor.py` (337行)
   - `src/crawler/utils/db.py` (227行)
   这些文件需要拆分成更小的模块。

## 重构计划

### 1. 合并进度管理器

将 `utils/progress_manager.py` 和 `core/progress_manager.py` 合并，保留在 `utils` 目录下，
因为它是一个通用工具类。

### 2. 拆分 detail_crawler.py

将 `detail_crawler.py` 拆分为以下几个模块:
- `detail_crawler.py` - 主类和核心逻辑
- `parsers/movie_parser.py` - 电影详情页面解析逻辑
- `parsers/actress_parser.py` - 演员信息解析逻辑
- `downloaders/image_downloader.py` - 图片下载功能

### 3. 拆分 genre_processor.py

将 `genre_processor.py` 拆分为:
- `genre_processor.py` - 主类和核心逻辑
- `parsers/genre_parser.py` - 类别页面解析逻辑

### 4. 重构 db.py

将 `db.py` 拆分为:
- `db/connection.py` - 数据库连接管理
- `db/operations.py` - 数据库操作

### 5. 清理废弃代码

- 移除未使用的函数和类
- 移除冗余的日志语句
- 统一错误处理方式
