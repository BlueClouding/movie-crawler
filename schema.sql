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
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    language supported_language NOT NULL,
    title TEXT NOT NULL,
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
    actress_id INTEGER NOT NULL REFERENCES actresses(id) ON DELETE CASCADE,
    language supported_language NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (actress_id, language)
);

-- 创建电影-演员关联表
CREATE TABLE movie_actresses (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    actress_id INTEGER NOT NULL REFERENCES actresses(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, actress_id)
);

-- 创建类型表
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建类型名称多语言表
CREATE TABLE genre_names (
    id SERIAL PRIMARY KEY,
    genre_id INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    language supported_language NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (genre_id, language)
);

-- 创建电影-类型关联表
CREATE TABLE movie_genres (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- 创建磁力链接表
CREATE TABLE magnets (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    name TEXT,
    size TEXT,
    created_date DATE,
    UNIQUE (movie_id, url)
);

-- 创建观看链接表
CREATE TABLE watch_urls (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    name TEXT,
    index INTEGER NOT NULL,
    UNIQUE (movie_id, url)
);

-- 创建下载链接表
CREATE TABLE download_urls (
    id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    name TEXT,
    host TEXT,
    index INTEGER NOT NULL,
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

-- 创建索引
CREATE INDEX idx_movies_code ON movies(code);
CREATE INDEX idx_movies_release_date ON movies(release_date);
CREATE INDEX idx_movie_titles_language ON movie_titles(language);
CREATE INDEX idx_actress_names_language ON actress_names(language);
CREATE INDEX idx_genre_names_language ON genre_names(language); 