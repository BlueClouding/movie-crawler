#!/usr/bin/env python3
"""
重建数据库脚本
此脚本会删除所有现有表，然后从schema.sql重新导入表结构
"""

import asyncio
import logging
import os
import subprocess
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 要删除的表列表（按依赖关系排序，先删除依赖表）
TABLES_TO_DROP = [
    "magnets",
    "watch_urls",
    "download_urls",
    "movie_actresses",
    "movie_genres",
    "movie_titles",
    "video_progress",
    "pages_progress",
    "crawler_progress",
    "movies",
    "actresses",
    "actress_names",
    "genres",
    "genre_names",
]

async def drop_all_tables():
    """删除所有表"""
    engine = create_async_engine(settings.DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            # 先检查并删除外键约束
            logger.info("正在检查并删除外键约束...")
            try:
                # 获取所有外键约束
                result = await conn.execute(text("""
                    SELECT
                        tc.table_name, 
                        kcu.column_name, 
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name,
                        tc.constraint_name
                    FROM 
                        information_schema.table_constraints AS tc 
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                          AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                          AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY';
                """))
                
                constraints = result.fetchall()
                
                # 删除所有外键约束
                for constraint in constraints:
                    table_name = constraint[0]
                    constraint_name = constraint[4]
                    
                    await conn.execute(text(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"))
                    logger.info(f"已删除外键约束: {constraint_name} 从表 {table_name}")
            except Exception as e:
                logger.error(f"删除外键约束时出错: {str(e)}")
            
            # 删除表
            for table in TABLES_TO_DROP:
                try:
                    await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    logger.info(f"已删除表: {table}")
                except Exception as e:
                    logger.error(f"删除表 {table} 时出错: {str(e)}")
            
            # 删除枚举类型
            try:
                await conn.execute(text("DROP TYPE IF EXISTS supported_language CASCADE"))
                logger.info("已删除枚举类型: supported_language")
            except Exception as e:
                logger.error(f"删除枚举类型时出错: {str(e)}")
                
            # 删除函数和触发器
            try:
                await conn.execute(text("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE"))
                logger.info("已删除函数: update_updated_at_column")
            except Exception as e:
                logger.error(f"删除函数时出错: {str(e)}")
                
            logger.info("所有表和相关对象已删除")
    except Exception as e:
        logger.error(f"删除表时发生错误: {str(e)}")
    finally:
        await engine.dispose()

def import_schema():
    """从schema.sql导入数据库结构"""
    try:
        # 获取数据库连接信息
        db_user = settings.DB_USER
        db_password = settings.DB_PASSWORD
        db_host = settings.DB_HOST
        db_port = settings.DB_PORT
        db_name = settings.DB_NAME
        
        # 构建psql命令
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
        
        # 设置环境变量以传递密码
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        # 执行psql命令导入schema
        command = [
            "psql",
            "-h", db_host,
            "-p", str(db_port),
            "-U", db_user,
            "-d", db_name,
            "-f", schema_path
        ]
        
        logger.info(f"正在从 {schema_path} 导入数据库结构...")
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("数据库结构导入成功")
        else:
            logger.error(f"导入数据库结构时出错: {result.stderr}")
            
    except Exception as e:
        logger.error(f"导入数据库结构时发生错误: {str(e)}")

async def rebuild_database():
    """重建数据库：删除所有表并从schema.sql重新导入"""
    # 1. 删除所有表
    await drop_all_tables()
    
    # 2. 导入schema.sql
    import_schema()
    
    logger.info("数据库重建完成")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="重建数据库结构")
    parser.add_argument("--drop-only", action="store_true", help="只删除表，不重新导入")
    parser.add_argument("--import-only", action="store_true", help="只导入schema.sql，不删除表")
    
    args = parser.parse_args()
    
    if args.drop_only:
        asyncio.run(drop_all_tables())
    elif args.import_only:
        import_schema()
    else:
        # 默认行为：重建数据库
        asyncio.run(rebuild_database())
