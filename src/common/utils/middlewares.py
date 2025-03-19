import logging
import time
import datetime
import traceback
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from common.utils.logging_config import setup_logging

# 使用集中式日志配置
logger = setup_logging(app_name="crawler", log_level=logging.DEBUG)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    中间件，用于记录所有请求的日志
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        request_id = id(request)
        
        # 记录请求开始
        logger.info(f"开始处理请求: {request.method} {request.url.path} [ID: {request_id}]")
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 记录请求完成
            process_time = time.time() - start_time
            logger.info(
                f"请求处理完成: {request.method} {request.url.path} "
                f"[ID: {request_id}] 状态码: {response.status_code} "
                f"处理时间: {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            logger.error(
                f"请求处理异常: {request.method} {request.url.path} "
                f"[ID: {request_id}] 处理时间: {process_time:.3f}s"
            )
            return await self.handle_exception(request, e)
    
    async def handle_exception(self, request: Request, exc: Exception) -> Response:
        """处理请求过程中的异常"""
        if isinstance(exc, Exception):
            error_msg = str(exc)
            error_traceback = traceback.format_exc()
            
            # 记录详细错误信息
            logger.error(f"处理请求时发生错误: {error_msg}")
            logger.error(error_traceback)
            
            # 提取错误位置
            tb = traceback.extract_tb(exc.__traceback__)
            if tb:
                last_frame = tb[-1]
                file_name = last_frame.filename
                line_number = last_frame.lineno
                function_name = last_frame.name
                line = last_frame.line
                error_location = f"{file_name}:{line_number} in {function_name}() - {line}"
            else:
                error_location = "未知位置"
            
            # 返回JSON格式的错误响应，只返回简洁的错误信息
            return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "msg": "服务器内部错误，请稍后重试",
                "timestamp": datetime.datetime.now().isoformat()
            }
        )
        
        # 如果不是我们处理的异常类型，继续抛出
        raise exc

def setup_middlewares(app: FastAPI):
    """
    设置应用的中间件
    
    Args:
        app: FastAPI 应用实例
    """
    # 添加日志中间件
    app.add_middleware(LoggingMiddleware)
