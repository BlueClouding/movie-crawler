# Feed Service Python化说明文档

## 概述

本项目将原Java版本的FeedService转换为Python版本，提供了完整的feed电影数据爬取和处理功能，并通过Flask API提供HTTP接口服务。

## 功能特性

### 核心功能
- ✅ **Feed页面爬取**: 自动获取123av.com的feed页面电影信息
- ✅ **分页处理**: 支持多页数据批量获取
- ✅ **Cookie管理**: 自动处理登录认证和Cookie缓存
- ✅ **数据解析**: 提取电影代码、标题、缩略图、时长等信息
- ✅ **错误处理**: 完善的异常处理和重试机制
- ✅ **RESTful API**: 提供HTTP接口供外部调用

### 技术特点
- 🔄 **自动重试**: 401错误时自动刷新Cookie重试
- 🎭 **Playwright集成**: 使用Playwright进行浏览器自动化登录
- 📊 **数据持久化**: 模拟数据库存储（可扩展为真实数据库）
- 🚀 **高性能**: 异步处理和连接池优化
- 📝 **完整日志**: 详细的操作日志记录

## 文件结构

```
├── feed_service.py          # 核心服务类
├── feed_api.py             # Flask API接口
├── requirements_feed.txt   # Python依赖包
└── feed_service_readme.md  # 说明文档
```

## 安装和配置

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements_feed.txt

# 安装Playwright浏览器
playwright install chromium
```

### 2. 配置参数

在`feed_service.py`中可以修改以下配置：

```python
# PlaywrightLoginService类中
self.login_username = "12345"      # 登录用户名
self.login_password = "kongqy"     # 登录密码

# FeedService类中
self.feed_base_url = "https://123av.com/ja/user/feed?sort=recent_update"  # Feed URL
```

## 使用方法

### 1. 直接使用服务类

```python
from feed_service import FeedService

# 创建服务实例
service = FeedService()

# 处理前5页的feed电影
result = service.process_feed_movies(5)
print(result)

# 获取所有电影
movies = service.get_all_movies()
print(f"总共找到 {len(movies)} 个电影")
```

### 2. 启动API服务

```bash
# 启动Flask API服务
python feed_api.py
```

服务启动后，访问 `http://localhost:5000` 查看API状态。

## API接口文档

### 基础信息
- **服务地址**: `http://localhost:5000`
- **数据格式**: JSON
- **字符编码**: UTF-8

### 接口列表

#### 1. 健康检查
```http
GET /
```

**响应示例**:
```json
{
  "status": "healthy",
  "service": "Feed API",
  "version": "1.0.0",
  "message": "Feed服务API正常运行"
}
```

#### 2. 处理Feed电影
```http
POST /api/feed/process
Content-Type: application/json

{
  "pages_to_fetch": 5
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "成功处理 25 个电影，保存了 20 个",
  "movies_found": 25,
  "movies_saved": 20,
  "errors": []
}
```

#### 3. 获取所有电影
```http
GET /api/feed/movies?limit=10&offset=0
```

**响应示例**:
```json
{
  "success": true,
  "total": 150,
  "count": 10,
  "limit": 10,
  "offset": 0,
  "movies": [
    {
      "code": "VERO-085",
      "title": "美女电影标题",
      "thumbnail": "https://example.com/thumb.jpg",
      "original_id": 12345,
      "likes": 100,
      "duration": "120分钟",
      "link": "/ja/movie/12345",
      "status": "NEW",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

#### 4. 获取单个电影
```http
GET /api/feed/movies/12345
```

#### 5. 获取统计信息
```http
GET /api/feed/stats
```

**响应示例**:
```json
{
  "success": true,
  "stats": {
    "total_movies": 150,
    "status_counts": {
      "NEW": 120,
      "PROCESSED": 30
    },
    "service_info": {
      "feed_base_url": "https://123av.com/ja/user/feed?sort=recent_update",
      "cache_enabled": true
    }
  }
}
```

#### 6. 获取总页数
```http
GET /api/feed/pages/total
```

#### 7. 清除缓存
```http
POST /api/feed/cache/invalidate
```

## 使用示例

### Python客户端示例

```python
import requests
import json

# API基础URL
base_url = "http://localhost:5000"

# 1. 检查服务状态
response = requests.get(f"{base_url}/")
print("服务状态:", response.json())

# 2. 处理feed电影
data = {"pages_to_fetch": 3}
response = requests.post(
    f"{base_url}/api/feed/process",
    json=data,
    headers={"Content-Type": "application/json"}
)
result = response.json()
print("处理结果:", json.dumps(result, indent=2, ensure_ascii=False))

# 3. 获取电影列表
response = requests.get(f"{base_url}/api/feed/movies?limit=5")
movies = response.json()
print(f"找到 {movies['total']} 个电影，显示前 {movies['count']} 个:")
for movie in movies['movies']:
    print(f"- {movie['code']}: {movie['title']}")

# 4. 获取统计信息
response = requests.get(f"{base_url}/api/feed/stats")
stats = response.json()
print("统计信息:", json.dumps(stats, indent=2, ensure_ascii=False))
```

### curl命令示例

```bash
# 处理feed电影
curl -X POST http://localhost:5000/api/feed/process \
  -H "Content-Type: application/json" \
  -d '{"pages_to_fetch": 2}'

# 获取电影列表
curl "http://localhost:5000/api/feed/movies?limit=5&offset=0"

# 获取统计信息
curl http://localhost:5000/api/feed/stats

# 清除缓存
curl -X POST http://localhost:5000/api/feed/cache/invalidate
```

## 数据模型

### Movie对象结构

```python
@dataclass
class Movie:
    code: Optional[str] = None          # 电影代码，如"VERO-085"
    title: Optional[str] = None         # 电影标题
    thumbnail: Optional[str] = None     # 缩略图URL
    original_id: Optional[int] = None   # 原始ID
    likes: Optional[int] = None         # 点赞数
    duration: Optional[str] = None      # 时长
    link: Optional[str] = None          # 详情页链接
    status: str = "NEW"                 # 状态
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
```

## 错误处理

### 常见错误码

- **400**: 请求参数错误
- **401**: 认证失败（会自动重试）
- **404**: 资源不存在
- **500**: 服务器内部错误

### 错误响应格式

```json
{
  "success": false,
  "message": "错误描述",
  "error_type": "异常类型",
  "errors": ["详细错误信息"]
}
```

## 扩展和定制

### 1. 数据库集成

可以将模拟的内存存储替换为真实数据库：

```python
# 在FeedService类中添加数据库连接
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class FeedService:
    def __init__(self):
        # 数据库配置
        self.engine = create_engine('sqlite:///movies.db')
        self.Session = sessionmaker(bind=self.engine)
    
    def save_single_movie(self, movie: Movie) -> bool:
        session = self.Session()
        try:
            # 检查是否存在
            existing = session.query(MovieModel).filter_by(
                original_id=movie.original_id
            ).first()
            
            if existing:
                return False
            
            # 保存新电影
            movie_model = MovieModel(**movie.to_dict())
            session.add(movie_model)
            session.commit()
            return True
        finally:
            session.close()
```

### 2. 异步处理

可以使用异步框架提高性能：

```python
import asyncio
import aiohttp
from fastapi import FastAPI

class AsyncFeedService:
    async def get_movies_from_feed_page_async(self, page_number: int):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                html = await response.text()
                return self.extract_movie_from_element(html)
```

### 3. 缓存优化

添加Redis缓存：

```python
import redis
import json

class CachedFeedService(FeedService):
    def __init__(self):
        super().__init__()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    def get_movies_from_feed_page(self, page_number: int):
        cache_key = f"feed_page_{page_number}"
        cached = self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        movies = super().get_movies_from_feed_page(page_number)
        self.redis_client.setex(
            cache_key, 
            3600,  # 1小时过期
            json.dumps([m.to_dict() for m in movies])
        )
        return movies
```

## 性能优化建议

1. **并发处理**: 使用线程池或异步处理多页面爬取
2. **连接复用**: 使用Session对象复用HTTP连接
3. **缓存策略**: 合理设置Cookie和页面数据缓存时间
4. **限流控制**: 添加请求间隔避免被反爬
5. **监控告警**: 添加性能监控和异常告警

## 部署建议

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements_feed.txt .
RUN pip install -r requirements_feed.txt
RUN playwright install chromium

COPY feed_service.py feed_api.py ./

EXPOSE 5000

CMD ["python", "feed_api.py"]
```

### 生产环境配置

```bash
# 使用Gunicorn部署
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 feed_api:app

# 使用Nginx反向代理
# /etc/nginx/sites-available/feed-api
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 总结

本Python版本的FeedService完全复现了原Java版本的功能，并提供了更加灵活的API接口。主要优势：

- ✅ **功能完整**: 100%复现原Java功能
- ✅ **易于使用**: 提供RESTful API接口
- ✅ **扩展性强**: 支持数据库、缓存等扩展
- ✅ **维护简单**: Python代码更加简洁易懂
- ✅ **部署灵活**: 支持多种部署方式

如有任何问题或需要进一步定制，请参考代码注释或联系开发团队。