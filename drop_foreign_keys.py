import asyncio
import asyncpg

# 数据库连接参数
DATABASE_URL = "postgresql://dqy@localhost:5432/movie_crawler"

async def drop_all_foreign_keys():
    print("开始删除所有外键约束...")
    
    # 连接到数据库
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # 查询所有外键约束
        constraints = await conn.fetch("""
            SELECT
                tc.constraint_name,
                tc.table_name,
                tc.constraint_schema
            FROM
                information_schema.table_constraints AS tc
            WHERE
                tc.constraint_type = 'FOREIGN KEY'
                AND tc.constraint_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY
                tc.constraint_schema,
                tc.table_name
        """)
        
        if not constraints:
            print("没有找到外键约束")
            return
        
        print(f"找到 {len(constraints)} 个外键约束")
        
        # 开始事务
        async with conn.transaction():
            for constraint in constraints:
                constraint_name = constraint['constraint_name']
                table_name = constraint['table_name']
                schema = constraint['constraint_schema']
                
                # 构建删除约束的SQL
                drop_sql = f'ALTER TABLE "{schema}"."{table_name}" DROP CONSTRAINT "{constraint_name}"'
                
                print(f"执行: {drop_sql}")
                await conn.execute(drop_sql)
                print(f"已删除外键约束: {constraint_name} 从表 {table_name}")
        
        print("所有外键约束已成功删除")
    
    except Exception as e:
        print(f"发生错误: {e}")
    
    finally:
        # 关闭连接
        await conn.close()
        print("数据库连接已关闭")

if __name__ == "__main__":
    asyncio.run(drop_all_foreign_keys())
