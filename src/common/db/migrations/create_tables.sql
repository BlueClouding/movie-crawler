-- Create crawler progress table
CREATE TABLE IF NOT EXISTS crawler_progress (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create pages progress table
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create video progress table
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
