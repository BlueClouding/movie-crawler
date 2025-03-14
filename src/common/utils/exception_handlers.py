import traceback
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from fastapi import FastAPI

# 获取日志记录器
logger = logging.getLogger(__name__)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理请求验证异常
    """
    error_detail = []
    for error in exc.errors():
        error_detail.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        })
    
    logger.error(f"请求验证错误: {error_detail}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {
                "message": "请求数据验证失败",
                "errors": error_detail,
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY
            }
        }
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    处理SQLAlchemy异常
    """
    error_msg = str(exc)
    logger.error(f"数据库错误: {error_msg}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {
                "message": "数据库操作错误",
                "error": error_msg,
                "error_type": "SQLAlchemyError",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                # 不返回完整的堆栈跟踪信息
            }
        }
    )

async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """
    处理Pydantic验证异常
    """
    error_detail = []
    for error in exc.errors():
        error_detail.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        })
    
    logger.error(f"数据验证错误: {error_detail}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {
                "message": "数据验证失败",
                "errors": error_detail,
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY
            }
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器，捕获所有未处理的异常
    """
    error_msg = str(exc)
    error_traceback = traceback.format_exc()
    
    # 记录详细的错误信息
    logger.error(f"未处理的异常: {error_msg}")
    logger.error(error_traceback)
    
    # 提取错误发生的文件和行号
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
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {
                "message": error_msg,
                "error_type": exc.__class__.__name__,
                "location": error_location,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                # 不返回完整的堆栈跟踪信息
            }
        }
    )

def register_exception_handlers(app : FastAPI):
    """
    注册所有异常处理器到FastAPI应用
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
