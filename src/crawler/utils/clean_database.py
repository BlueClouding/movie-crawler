
import asyncio
import logging
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 直接从环境变量或配置文件获取数据库连接信息
try:
    from app.config.settings import settings
    DATABASE_URL = settings.DATABASE_URL
except ImportError:
        # 如果无法导入settings，使用默认值
        DATABASE_URL = os.environ.get(
            "DATABASE_URL", 
            "postgresql+asyncpg://dqy@localhost:5432/movie_crawler"
        )
        

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 要清空的表列表（按依赖关系排序，先清空依赖表）
TABLES_TO_CLEAN = [
    "magnets",
    "watch_urls",
    "download_urls",
    "movie_actresses",
    "movie_genres",
    "movie_titles",
    "video_progress",
    "pages_progress",
    "crawler_progress",
    # 以下表格包含基础数据，谨慎清空
    "movies",
    "actresses",
    "actress_names",
    "genres",
    "genre_names",
]

# 要重置序列的表列表，所有表
# 注意：只有使用SERIAL或BIGSERIAL的表才有序列
SEQUENCES_TO_RESET = [
    "video_progress_id_seq",
    "pages_progress_id_seq",
    "crawler_progress_id_seq",
    "movies_id_seq",
    "actresses_id_seq",
    "actress_names_id_seq",
    "genres_id_seq",
    "genre_names_id_seq",
    "magnets_id_seq",
    "watch_urls_id_seq",
    "download_urls_id_seq",
    "movie_titles_id_seq",
    # 以下表使用复合主键，没有序列
    # "movie_actresses_id_seq", 
    # "movie_genres_id_seq",
]

async def clean_database():
    """清空数据库中的所有表并重置序列"""
    engine = create_async_engine(DATABASE_URL)
    
    try:
        # 1. 清空表
        for table in TABLES_TO_CLEAN:
            try:
                # 为每个操作使用单独的事务
                async with engine.begin() as conn:
                    # 尝试使用更高权限的方式清空表
                    try:
                        # 先尝试直接清空
                        await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                        logger.info(f"已清空表: {table}")
                    except Exception as inner_e:
                        # 如果直接清空失败，尝试使用DELETE FROM
                        try:
                            await conn.execute(text(f"DELETE FROM {table}"))
                            logger.info(f"已使用DELETE FROM清空表: {table}")
                        except Exception as delete_e:
                            # 两种方式都失败，记录错误
                            raise Exception(f"无法清空表 {table}: {str(inner_e)} 和 {str(delete_e)}")
            except Exception as e:
                logger.error(f"清空表 {table} 时出错: {str(e)}")
        
        # 2. 重置序列
        for sequence in SEQUENCES_TO_RESET:
            try:
                # 为每个操作使用单独的事务
                async with engine.begin() as conn:
                    try:
                        # 尝试直接重置序列
                        await conn.execute(text(f"ALTER SEQUENCE {sequence} RESTART WITH 1"))
                        logger.info(f"已重置序列: {sequence}")
                    except Exception as inner_e:
                        # 如果直接重置失败，尝试使用SELECT setval
                        try:
                            await conn.execute(text(f"SELECT setval('{sequence}', 1, false)"))
                            logger.info(f"已使用setval重置序列: {sequence}")
                        except Exception as setval_e:
                            # 两种方式都失败，记录错误
                            raise Exception(f"无法重置序列 {sequence}: {str(inner_e)} 和 {str(setval_e)}")
            except Exception as e:
                logger.error(f"重置序列 {sequence} 时出错: {str(e)}")
                
        logger.info("数据库清理完成")
    except Exception as e:
        logger.error(f"清理数据库时发生错误: {str(e)}")
    finally:
        await engine.dispose()

async def clean_specific_tables(tables=None, reset_sequences=True):
    """清空指定的表并可选择性地重置序列"""
    if tables is None:
        tables = TABLES_TO_CLEAN
        
    engine = create_async_engine(DATABASE_URL)
    
    try:
        # 1. 清空指定表
        for table in tables:
            try:
                # 为每个操作使用单独的事务
                async with engine.begin() as conn:
                    # 尝试使用更高权限的方式清空表
                    try:
                        # 先尝试直接清空
                        await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                        logger.info(f"已清空表: {table}")
                    except Exception as inner_e:
                        # 如果直接清空失败，尝试使用DELETE FROM
                        try:
                            await conn.execute(text(f"DELETE FROM {table}"))
                            logger.info(f"已使用DELETE FROM清空表: {table}")
                        except Exception as delete_e:
                            # 两种方式都失败，记录错误
                            raise Exception(f"无法清空表 {table}: {str(inner_e)} 和 {str(delete_e)}")
            except Exception as e:
                logger.error(f"清空表 {table} 时出错: {str(e)}")
        
        # 2. 如果需要，重置序列
        if reset_sequences:
            for sequence in SEQUENCES_TO_RESET:
                try:
                    # 为每个操作使用单独的事务
                    async with engine.begin() as conn:
                        # 检查序列是否存在
                        check_result = await conn.execute(
                            text("SELECT EXISTS(SELECT 1 FROM pg_sequences WHERE sequencename = :seq_name)")
                            .bindparams(seq_name=sequence)
                        )
                        exists = check_result.scalar()
                        
                        if exists:
                            await conn.execute(text(f"ALTER SEQUENCE {sequence} RESTART WITH 1"))
                            logger.info(f"已重置序列: {sequence}")
                        else:
                            logger.warning(f"序列不存在，跳过: {sequence}")
                except Exception as e:
                    logger.error(f"重置序列 {sequence} 时出错: {str(e)}")
                
        logger.info("指定表清理完成")
    except Exception as e:
        logger.error(f"清理指定表时发生错误: {str(e)}")
    finally:
        await engine.dispose()

async def clean_crawler_data():
    """只清空爬虫进度相关的表，保留电影和演员数据"""
    crawler_tables = [
        "video_progress",
        "pages_progress",
        "crawler_progress",
    ]
    await clean_specific_tables(tables=crawler_tables)

async def clean_all_data():
    """清空所有表"""
    all_tables = TABLES_TO_CLEAN + [
        "movies",
        "actresses",
        "actress_names",
        "genres",
        "genre_names",
        "magnets",
        "watch_urls",
        "download_urls",
        "movie_actresses",
        "movie_genres",
        "movie_titles",
    ]
    await clean_specific_tables(tables=all_tables)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="清理数据库中的数据")
    parser.add_argument("--all", action="store_true", help="清空所有表，包括电影和演员数据")
    parser.add_argument("--crawler", action="store_true", help="只清空爬虫进度相关的表")
    parser.add_argument("--table", nargs="+", help="指定要清空的表名")
    
    args = parser.parse_args()
    
    if args.all:
        asyncio.run(clean_all_data())
    elif args.crawler:
        asyncio.run(clean_crawler_data())
    elif args.table:
        asyncio.run(clean_specific_tables(tables=args.table))
    else:
        # 默认清空TABLES_TO_CLEAN中的表
        asyncio.run(clean_database())
