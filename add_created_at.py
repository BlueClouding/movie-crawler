import asyncio
import asyncpg

# 数据库连接参数
DATABASE_URL = "postgresql://dqy@localhost:5432/movie_crawler"

async def add_created_at_columns():
    # 直接使用asyncpg连接数据库
    conn = await asyncpg.connect(DATABASE_URL)
    
    # 需要添加created_at列的表
    tables = [
        'movie_titles',
        'actress_names',
        'genre_names',
        'movie_actresses',
        'movie_genres',
        'magnets',
        'watch_urls',
        'download_urls'
    ]
    
    try:
        for table in tables:
            # 检查表是否存在created_at列
            check_query = f"""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = '{table}' AND column_name = 'created_at'
            """
            exists = await conn.fetchval(check_query)
            
            if not exists:
                print(f"Adding created_at column to {table} table...")
                # 添加created_at列
                alter_query = f"""
                ALTER TABLE {table} 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                """
                await conn.execute(alter_query)
                print(f"Successfully added created_at column to {table} table.")
            else:
                print(f"created_at column already exists in {table} table.")
        
        print("All tables have been updated with created_at column if needed.")
    finally:
        # 确保关闭连接
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_created_at_columns())
