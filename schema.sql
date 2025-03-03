-- 创建语言枚举类型
CREATE TYPE supported_language AS ENUM ('en', 'ja', 'zh');

-- 创建电影基本信息表
CREATE TABLE movies (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    duration INTERVAL NOT NULL,
    release_date DATE NOT NULL,
    cover_image_url TEXT,
    preview_video_url TEXT,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建电影标题多语言表
CREATE TABLE movie_titles (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL,
    language supported_language NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (movie_id, language)
);

-- 创建演员表
CREATE TABLE actresses (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建演员名称多语言表
CREATE TABLE actress_names (
    id SERIAL PRIMARY KEY,
    actress_id INTEGER NOT NULL,
    language supported_language NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (actress_id, language)
);

-- 创建电影-演员关联表
CREATE TABLE movie_actresses (
    movie_id INTEGER NOT NULL,
    actress_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (movie_id, actress_id)
);

-- 创建类型表
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    urls TEXT[] NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建类型名称多语言表
CREATE TABLE genre_names (
    id SERIAL PRIMARY KEY,
    genre_id INTEGER NOT NULL,
    language supported_language NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (genre_id, language)
);

-- 创建电影-类型关联表
CREATE TABLE movie_genres (
    movie_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (movie_id, genre_id)
);

-- 创建磁力链接表
CREATE TABLE magnets (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    name TEXT,
    size TEXT,
    created_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (movie_id, url)
);

-- 创建观看链接表
CREATE TABLE watch_urls (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    name TEXT,
    index INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (movie_id, url)
);

-- 创建下载链接表
CREATE TABLE download_urls (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    name TEXT,
    host TEXT,
    index INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (movie_id, url)
);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为 movies 表添加更新时间触发器
CREATE TRIGGER update_movies_updated_at
    BEFORE UPDATE ON movies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 创建爬虫进度主表
CREATE TABLE IF NOT EXISTS crawler_progress (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建页面进度表
CREATE TABLE IF NOT EXISTS pages_progress (
    id SERIAL PRIMARY KEY,
    crawler_progress_id INTEGER NOT NULL,
    relation_id INTEGER NOT NULL,
    page_type VARCHAR(50) NOT NULL,
    page_number INTEGER NOT NULL,
    total_pages INTEGER NOT NULL,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(relation_id, page_number)
);

-- 创建视频处理进度表
CREATE TABLE IF NOT EXISTS video_progress (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    url TEXT NOT NULL,
    genre_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    title TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    detail_fetched BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, genre_id)
);

-- 注意：video_resources 表不存在，因此移除相关触发器
-- CREATE TRIGGER update_video_resources_timestamp
--     BEFORE UPDATE ON video_resources
--     FOR EACH ROW
--     EXECUTE FUNCTION update_updated_at_column();

-- 为视频进度表添加更新时间触发器
CREATE TRIGGER update_video_progress_timestamp
    BEFORE UPDATE ON video_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 创建爬虫相关索引
-- 注意：video_resources 和 genre_pages 表不存在，因此移除相关索引
-- CREATE INDEX idx_video_resources_code ON video_resources(code);
-- CREATE INDEX idx_video_resources_genre_page ON video_resources(genre_id, page_number);
-- CREATE INDEX idx_video_resources_status ON video_resources(status);
-- CREATE INDEX idx_genre_pages_status ON genre_pages(status);
CREATE INDEX idx_video_progress_status ON video_progress(status);

-- 创建索引
CREATE INDEX idx_movies_code ON movies(code);
CREATE INDEX idx_movies_release_date ON movies(release_date);
CREATE INDEX idx_movie_titles_language ON movie_titles(language);
CREATE INDEX idx_movie_titles_movie_id ON movie_titles(movie_id);
CREATE INDEX idx_actress_names_language ON actress_names(language);
CREATE INDEX idx_actress_names_actress_id ON actress_names(actress_id);
CREATE INDEX idx_genre_names_language ON genre_names(language);
CREATE INDEX idx_genre_names_genre_id ON genre_names(genre_id);
CREATE INDEX idx_movie_actresses_movie_id ON movie_actresses(movie_id);
CREATE INDEX idx_movie_actresses_actress_id ON movie_actresses(actress_id);
CREATE INDEX idx_movie_genres_movie_id ON movie_genres(movie_id);
CREATE INDEX idx_movie_genres_genre_id ON movie_genres(genre_id);
CREATE INDEX idx_magnets_movie_id ON magnets(movie_id);
CREATE INDEX idx_watch_urls_movie_id ON watch_urls(movie_id);
CREATE INDEX idx_download_urls_movie_id ON download_urls(movie_id);
CREATE INDEX idx_pages_progress_crawler_progress_id ON pages_progress(crawler_progress_id);

-- 添加 created_at 列到已有表（如果表已存在且列不存在）
DO $$
BEGIN
    -- 为 movie_titles 表添加 created_at 列
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'movie_titles') AND 
       NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'movie_titles' AND column_name = 'created_at') THEN
        ALTER TABLE movie_titles ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- 为 actress_names 表添加 created_at 列
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'actress_names') AND 
       NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'actress_names' AND column_name = 'created_at') THEN
        ALTER TABLE actress_names ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- 为 movie_actresses 表添加 created_at 列
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'movie_actresses') AND 
       NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'movie_actresses' AND column_name = 'created_at') THEN
        ALTER TABLE movie_actresses ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- 为 genre_names 表添加 created_at 列
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'genre_names') AND 
       NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'genre_names' AND column_name = 'created_at') THEN
        ALTER TABLE genre_names ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- 为 movie_genres 表添加 created_at 列
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'movie_genres') AND 
       NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'movie_genres' AND column_name = 'created_at') THEN
        ALTER TABLE movie_genres ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- 为 magnets 表添加 created_at 列
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'magnets') AND 
       NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'magnets' AND column_name = 'created_at') THEN
        ALTER TABLE magnets ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- 为 watch_urls 表添加 created_at 列
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'watch_urls') AND 
       NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'watch_urls' AND column_name = 'created_at') THEN
        ALTER TABLE watch_urls ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- 为 download_urls 表添加 created_at 列
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'download_urls') AND 
       NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'download_urls' AND column_name = 'created_at') THEN
        ALTER TABLE download_urls ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
END
$$;