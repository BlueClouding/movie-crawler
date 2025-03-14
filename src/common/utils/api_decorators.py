import functools
import logging
import traceback
from fastapi import HTTPException, status
from typing import Callable, Any

logger = logging.getLogger(__name__)

def handle_exceptions(func: Callable) -> Callable:
    """
    装饰器，用于处理API端点中的异常并提供统一的错误响应格式
    
    用法:
    @router.post("/endpoint")
    @handle_exceptions
    async def my_endpoint():
        # 您的代码
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 直接传递HTTP异常
            return await func(*args, **kwargs)
        except HTTPException:
            # 如果是HTTP异常，直接重新抛出
            raise
        except Exception as e:
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            
            # 记录错误信息
            logger.error(f"API调用时发生错误: {error_msg}")
            logger.error(error_traceback)
            
            # 提取错误发生的文件和行号
            tb = traceback.extract_tb(e.__traceback__)
            if tb:
                last_frame = tb[-1]
                file_name = last_frame.filename
                line_number = last_frame.lineno
                function_name = last_frame.name
                line = last_frame.line
                error_location = f"{file_name}:{line_number} in {function_name}() - {line}"
            else:
                error_location = "未知位置"
            
            # 抛出格式化的HTTP异常
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": error_msg,
                    "location": error_location,
                    "traceback": error_traceback.split("\n")
                }
            )
    
    return wrapper

def log_api_call(func: Callable) -> Callable:
    """
    装饰器，用于记录API调用的开始和结束
    
    用法:
    @router.post("/endpoint")
    @log_api_call
    async def my_endpoint():
        # 您的代码
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        endpoint_name = func.__name__
        logger.info(f"开始处理API请求: {endpoint_name}")
        
        result = await func(*args, **kwargs)
        
        logger.info(f"API请求处理完成: {endpoint_name}")
        return result
    
    return wrapper
