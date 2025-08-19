#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feed API服务
提供HTTP接口访问FeedService功能
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from feed_service import FeedService
from loguru import logger
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

# 创建FastAPI应用
app = FastAPI(
    title="Feed API服务",
    description="提供123av.com feed电影数据爬取和处理功能的HTTP API接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 启用跨域支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建FeedService实例
feed_service = FeedService()

# Pydantic模型定义
class ProcessFeedRequest(BaseModel):
    pages_to_fetch: int = 1
    
class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    
class MovieResponse(BaseModel):
    code: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    original_id: Optional[int] = None
    likes: Optional[int] = None
    duration: Optional[str] = None
    link: Optional[str] = None
    status: str = "NEW"
    created_at: datetime
    
class MoviesListResponse(BaseModel):
    success: bool
    total: int
    count: int
    limit: int
    offset: int
    movies: List[MovieResponse]

@app.get("/", summary="健康检查", description="检查API服务状态")
async def health_check():
    """健康检查接口"""
    return {
        'status': 'healthy',
        'service': 'Feed API',
        'version': '1.0.0',
        'message': 'Feed服务API正常运行'
    }

@app.post("/api/feed/process", summary="处理Feed电影", description="从feed页面爬取并处理电影数据")
async def process_feed_movies(request: ProcessFeedRequest):
    """处理feed电影数据"""
    try:
        pages_to_fetch = request.pages_to_fetch
        
        if pages_to_fetch < 1:
            raise HTTPException(status_code=400, detail="参数错误: pages_to_fetch必须是大于0的整数")
        
        if pages_to_fetch > 50:  # 限制最大页数
            raise HTTPException(status_code=400, detail="参数错误: pages_to_fetch不能超过50页")
        
        logger.info(f"开始处理feed电影，页数: {pages_to_fetch}")
        
        # 调用服务处理
        result = feed_service.process_feed_movies(pages_to_fetch)
        
        logger.info(f"处理完成: {result}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理feed电影时出错: {e}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@app.get("/api/feed/movies", response_model=MoviesListResponse, summary="获取电影列表", description="分页获取所有电影数据")
async def get_movies(
    limit: int = Query(50, ge=1, le=1000, description="每页数量，1-1000之间"),
    offset: int = Query(0, ge=0, description="偏移量，从0开始")
):
    """获取所有电影"""
    try:
        # 获取所有电影
        all_movies = feed_service.get_all_movies()
        total = len(all_movies)
        
        # 分页处理
        movies_slice = all_movies[offset:offset + limit]
        
        # 转换为响应格式
        movies_data = []
        for movie in movies_slice:
            movie_data = MovieResponse(
                code=movie.code if hasattr(movie, 'code') else movie.get('code'),
                title=movie.title if hasattr(movie, 'title') else movie.get('title'),
                thumbnail=movie.thumbnail if hasattr(movie, 'thumbnail') else movie.get('thumbnail'),
                original_id=movie.original_id if hasattr(movie, 'original_id') else movie.get('original_id'),
                likes=movie.likes if hasattr(movie, 'likes') else movie.get('likes'),
                duration=movie.duration if hasattr(movie, 'duration') else movie.get('duration'),
                link=movie.link if hasattr(movie, 'link') else movie.get('link'),
                status=movie.status if hasattr(movie, 'status') else movie.get('status'),
                created_at=movie.created_at if hasattr(movie, 'created_at') else movie.get('created_at')
            )
            movies_data.append(movie_data)
        
        return MoviesListResponse(
            success=True,
            total=total,
            count=len(movies_data),
            limit=limit,
            offset=offset,
            movies=movies_data
        )
        
    except Exception as e:
        logger.error(f"获取电影列表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@app.get("/api/feed/movies/{movie_id}", summary="获取单个电影", description="根据电影ID获取详细信息")
async def get_movie(movie_id: int):
    """获取单个电影详情"""
    try:
        all_movies = feed_service.get_all_movies()
        
        # 查找指定ID的电影
        target_movie = None
        for movie in all_movies:
            movie_id_value = movie.original_id if hasattr(movie, 'original_id') else movie.get('original_id')
            if movie_id_value == movie_id:
                target_movie = movie
                break
        
        if not target_movie:
            raise HTTPException(status_code=404, detail=f"未找到ID为{movie_id}的电影")
        
        movie_data = MovieResponse(
            code=target_movie.code if hasattr(target_movie, 'code') else target_movie.get('code'),
            title=target_movie.title if hasattr(target_movie, 'title') else target_movie.get('title'),
            thumbnail=target_movie.thumbnail if hasattr(target_movie, 'thumbnail') else target_movie.get('thumbnail'),
            original_id=target_movie.original_id if hasattr(target_movie, 'original_id') else target_movie.get('original_id'),
            likes=target_movie.likes if hasattr(target_movie, 'likes') else target_movie.get('likes'),
            duration=target_movie.duration if hasattr(target_movie, 'duration') else target_movie.get('duration'),
            link=target_movie.link if hasattr(target_movie, 'link') else target_movie.get('link'),
            status=target_movie.status if hasattr(target_movie, 'status') else target_movie.get('status'),
            created_at=target_movie.created_at if hasattr(target_movie, 'created_at') else target_movie.get('created_at')
        )
        
        return {
            'success': True,
            'movie': movie_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取电影详情时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@app.get("/api/feed/stats", summary="获取统计信息", description="获取电影数据统计信息")
async def get_stats():
    """获取统计信息"""
    try:
        all_movies = feed_service.get_all_movies()
        
        # 统计不同状态的电影数量
        status_counts = {}
        for movie in all_movies:
            status = movie.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'success': True,
            'stats': {
                'total_movies': len(all_movies),
                'status_counts': status_counts,
                'service_info': {
                    'feed_base_url': feed_service.feed_base_url,
                    'cache_enabled': True
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取统计信息时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@app.get("/api/feed/pages/total", summary="获取总页数", description="获取feed页面总数")
async def get_total_pages():
    """获取feed总页数"""
    try:
        total_pages = feed_service.get_total_feed_pages()
        
        return {
            'success': True,
            'total_pages': total_pages
        }
        
    except Exception as e:
        logger.error(f"获取总页数时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取总页数失败: {str(e)}")

@app.post("/api/feed/cache/invalidate", summary="清除缓存", description="清除Cookie缓存")
async def invalidate_cache():
    """清除缓存"""
    try:
        # 清除登录服务的cookie缓存
        if hasattr(feed_service, 'playwright_login_service'):
            feed_service.playwright_login_service.cached_cookies = None
            feed_service.playwright_login_service.cookie_cache_time = None
        
        return {
            'success': True,
            'message': 'Cookie缓存已清除'
        }
        
    except Exception as e:
        logger.error(f"清除缓存时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")

# 全局异常处理

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局异常: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"服务器内部错误: {str(exc)}",
            "error_type": type(exc).__name__
        }
    )

if __name__ == '__main__':
    import uvicorn
    import sys
    
    # 获取端口参数
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
            if port < 1 or port > 65535:
                print("错误: 端口号必须在1-65535之间")
                sys.exit(1)
        except ValueError:
            print("错误: 端口号必须是数字")
            sys.exit(1)
    
    # 显示API接口列表
    print("\n=== Feed FastAPI 服务 ===")
    print(f"服务地址: http://localhost:{port}")
    print(f"Swagger文档: http://localhost:{port}/docs")
    print(f"ReDoc文档: http://localhost:{port}/redoc")
    print("\n可用接口:")
    print(f"  GET  http://localhost:{port}/                        - 健康检查")
    print(f"  POST http://localhost:{port}/api/feed/process         - 处理feed电影")
    print(f"  GET  http://localhost:{port}/api/feed/movies          - 获取电影列表")
    print(f"  GET  http://localhost:{port}/api/feed/movies/{{id}}     - 获取单个电影")
    print(f"  GET  http://localhost:{port}/api/feed/stats           - 获取统计信息")
    print(f"  GET  http://localhost:{port}/api/feed/pages/total     - 获取总页数")
    print(f"  POST http://localhost:{port}/api/feed/cache/invalidate - 清除缓存")
    print("\n启动服务...\n")
    
    try:
        uvicorn.run(
            "feed_api:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"\n启动服务时出错: {e}")
        sys.exit(1)