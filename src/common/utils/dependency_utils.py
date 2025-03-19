"""
依赖注入工具模块，用于在非HTTP上下文中使用FastAPI的依赖注入系统。
"""

import inspect
import logging
from typing import Any, Dict, Type, TypeVar, Callable, Optional
from contextvars import ContextVar
from fastapi import Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
# 导入服务类
from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
from crawler.service.crawler_progress_service import CrawlerProgressService


# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建上下文变量来存储当前会话
session_context: ContextVar[Optional[AsyncSession]] = ContextVar('session_context', default=None)

# 用于类型标注
T = TypeVar('T')

logger = logging.getLogger(__name__)

async def get_dependency(dependency: Callable) -> Any:
    """获取FastAPI依赖项，支持异步和同步依赖。
    
    Args:
        dependency: 依赖函数或类
        
    Returns:
        解析后的依赖项
    """
    # 处理Depends包装的依赖
    if hasattr(dependency, 'dependency'):
        dependency = dependency.dependency
    
    # 处理类依赖（如果依赖是一个类）
    if inspect.isclass(dependency):
        return await get_service_with_deps(dependency)
    
    # 处理函数依赖
    result = None
    if inspect.iscoroutinefunction(dependency):
        result = await dependency()
    else:
        result = await run_in_threadpool(dependency)
    
    # 处理异步生成器结果（如get_db_session）
    if inspect.isasyncgen(result):
        # 从异步生成器中获取第一个值
        async for item in result:
            return item
    
    return result

async def get_service_with_deps(service_class: Type[T]) -> T:
    """获取带有依赖项的服务实例。
    
    Args:
        service_class: 服务类
        
    Returns:
        服务实例
    """
    # 解析构造函数的依赖项
    init_params = {}
    for param_name, param in inspect.signature(service_class.__init__).parameters.items():
        if param_name == 'self':
            continue
            
        # 处理有默认值的参数
        if param.default != inspect.Parameter.empty:
            # 处理Depends标记的依赖 - 使用字符串表示检查，因为Depends是函数不是类型
            if str(type(param.default)).find('Depends') > 0:
                # 获取dependency属性
                dependency = getattr(param.default, 'dependency', None)
                if dependency:
                    init_params[param_name] = await get_dependency(dependency)
    
    # 创建服务实例
    return service_class(**init_params)

# 服务注册表，用于存储所有服务类
_service_registry = {}

def register_service(name: str = None):
    """服务注册装饰器，用于注册服务类。
    
    Args:
        name: 服务名称，默认为类名
        
    Returns:
        装饰器函数
    """
    def decorator(cls):
        service_name = name or cls.__name__
        _service_registry[service_name] = cls
        return cls
    return decorator


async def discover_services(package_names: list = None) -> None:
    """自动发现并注册服务类。
    
    Args:
        package_names: 包名列表，默认为 ['crawler.service', 'app.services']
    """
    if package_names is None:
        package_names = ['crawler.service', 'app.services']
    
    import importlib
    import pkgutil
    import inspect
    import sys
    
    for package_name in package_names:
        try:
            # 导入包
            package = importlib.import_module(package_name)
            
            # 遍历包中的所有模块
            for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
                try:
                    # 导入模块
                    module = importlib.import_module(module_name)
                    
                    # 遍历模块中的所有类
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # 检查类是否定义在当前模块中
                        if obj.__module__ == module_name and 'Service' in name:
                            # 注册服务类
                            _service_registry[name] = obj
                except Exception as e:
                    logger.warning(f"Error importing module {module_name}: {e}")
        except Exception as e:
            logger.warning(f"Error discovering services in package {package_name}: {e}")
    
    logger.info(f"Discovered {len(_service_registry)} services: {list(_service_registry.keys())}")


async def create_services_with_session(session: AsyncSession) -> Dict[str, Any]:
    """为给定的会话创建所有需要的服务实例。
    
    Args:
        session: 数据库会话
        
    Returns:
        服务实例字典
    """
    # 设置上下文变量
    token = session_context.set(session)
    
    try:
        # 如果注册表为空，自动发现服务
        if not _service_registry:
            await discover_services()
        
        # 创建所有注册的服务实例
        services = {}
        for name, service_class in _service_registry.items():
            try:
                services[name] = await get_service_with_deps(service_class)
            except Exception as e:
                logger.warning(f"Error creating service {name}: {e}")
        
        return services
    finally:
        # 恢复上下文变量
        session_context.reset(token)

# 修改后的数据库会话获取函数（需要在app/config/database.py中替换现有的get_db_session）
async def get_db_session_with_context() -> AsyncSession:
    """获取数据库会话，优先从上下文中获取。
    
    Returns:
        数据库会话
    """
    # 尝试从上下文中获取会话
    session = session_context.get()
    if session is not None:
        return session
    
    # 如果上下文中没有会话，则创建新会话
    from app.config.database import async_session
    return async_session()
