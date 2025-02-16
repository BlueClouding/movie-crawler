"""Database utilities for the crawler."""

import logging
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta

class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, dbname='movie_crawler', user=None, password=None, host='localhost', port=5432):
        """Initialize database connection.
        
        Args:
            dbname (str): Database name
            user (str): Database user
            password (str): Database password
            host (str): Database host
            port (int): Database port
        """
        self._logger = logging.getLogger(__name__)
        self._conn_params = {
            'dbname': dbname,
            'host': host,
            'port': port
        }
        if user:
            self._conn_params['user'] = user
        if password:
            self._conn_params['password'] = password
            
        self._conn = None
        self._connect()
        
    def _connect(self):
        """Establish database connection."""
        try:
            if self._conn is None or self._conn.closed:
                self._conn = psycopg2.connect(**self._conn_params)
                self._logger.info("Database connection established")
        except Exception as e:
            self._logger.error(f"Error connecting to database: {str(e)}")
            raise
            
    def _ensure_connection(self):
        """Ensure database connection is active."""
        try:
            cur = self._conn.cursor()
            cur.execute('SELECT 1')
            cur.close()
        except (psycopg2.Error, Exception):
            self._connect()
            
    def save_movie(self, movie_data):
        """Save movie data to database.
        
        Args:
            movie_data (dict): Movie information
            
        Returns:
            int: ID of the inserted movie
        """
        self._ensure_connection()
        try:
            with self._conn.cursor() as cur:
                # 1. Insert movie basic info
                cur.execute("""
                    INSERT INTO movies (code, duration, release_date, cover_image_url, 
                                      preview_video_url, likes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    movie_data['code'],
                    self._parse_duration(movie_data['duration']),
                    movie_data['release_date'],
                    movie_data.get('cover_image'),
                    movie_data.get('preview_video'),
                    movie_data.get('likes', 0)
                ))
                movie_id = cur.fetchone()[0]
                
                # 2. Insert movie title
                cur.execute("""
                    INSERT INTO movie_titles (movie_id, language, title)
                    VALUES (%s, %s, %s)
                """, (movie_id, 'en', movie_data['title']))
                
                # 3. Insert actresses
                for actress_name in movie_data.get('actresses', []):
                    # Check if actress exists
                    cur.execute("""
                        WITH actress_check AS (
                            SELECT a.id 
                            FROM actresses a
                            JOIN actress_names an ON a.id = an.actress_id
                            WHERE an.name = %s AND an.language = 'en'
                        ), new_actress AS (
                            INSERT INTO actresses DEFAULT VALUES
                            RETURNING id
                        )
                        SELECT COALESCE(
                            (SELECT id FROM actress_check),
                            (SELECT id FROM new_actress)
                        ) as actress_id
                    """, (actress_name,))
                    actress_id = cur.fetchone()[0]
                    
                    # Insert actress name if new
                    cur.execute("""
                        INSERT INTO actress_names (actress_id, language, name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (actress_id, language) DO NOTHING
                    """, (actress_id, 'en', actress_name))
                    
                    # Link actress to movie
                    cur.execute("""
                        INSERT INTO movie_actresses (movie_id, actress_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (movie_id, actress_id))
                
                # 4. Insert genres
                for genre_name in movie_data.get('genres', []):
                    # Check if genre exists
                    cur.execute("""
                        WITH genre_check AS (
                            SELECT g.id 
                            FROM genres g
                            JOIN genre_names gn ON g.id = gn.genre_id
                            WHERE gn.name = %s AND gn.language = 'en'
                        ), new_genre AS (
                            INSERT INTO genres DEFAULT VALUES
                            RETURNING id
                        )
                        SELECT COALESCE(
                            (SELECT id FROM genre_check),
                            (SELECT id FROM new_genre)
                        ) as genre_id
                    """, (genre_name,))
                    genre_id = cur.fetchone()[0]
                    
                    # Insert genre name if new
                    cur.execute("""
                        INSERT INTO genre_names (genre_id, language, name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (genre_id, language) DO NOTHING
                    """, (genre_id, 'en', genre_name))
                    
                    # Link genre to movie
                    cur.execute("""
                        INSERT INTO movie_genres (movie_id, genre_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (movie_id, genre_id))
                
                # 5. Insert magnets
                if movie_data.get('magnets'):
                    magnet_data = [(
                        movie_id,
                        magnet['url'],
                        magnet.get('name'),
                        magnet.get('size'),
                        magnet.get('date')
                    ) for magnet in movie_data['magnets']]
                    execute_values(cur, """
                        INSERT INTO magnets (movie_id, url, name, size, created_date)
                        VALUES %s
                        ON CONFLICT (movie_id, url) DO NOTHING
                    """, magnet_data)
                
                # 6. Insert watch URLs
                if movie_data.get('watch_urls_info'):
                    watch_data = [(
                        movie_id,
                        url_info['url'],
                        url_info.get('name'),
                        url_info['index']
                    ) for url_info in movie_data['watch_urls_info']]
                    execute_values(cur, """
                        INSERT INTO watch_urls (movie_id, url, name, index)
                        VALUES %s
                        ON CONFLICT (movie_id, url) DO NOTHING
                    """, watch_data)
                
                # 7. Insert download URLs
                if movie_data.get('download_urls_info'):
                    download_data = [(
                        movie_id,
                        url_info['url'],
                        url_info.get('name'),
                        url_info.get('host'),
                        url_info['index']
                    ) for url_info in movie_data['download_urls_info']]
                    execute_values(cur, """
                        INSERT INTO download_urls (movie_id, url, name, host, index)
                        VALUES %s
                        ON CONFLICT (movie_id, url) DO NOTHING
                    """, download_data)
                
                self._conn.commit()
                return movie_id
                
        except Exception as e:
            self._conn.rollback()
            self._logger.error(f"Error saving movie data: {str(e)}")
            raise
            
    def _parse_duration(self, duration_str):
        """Parse duration string to interval.
        
        Args:
            duration_str (str): Duration string in format "HH:MM:SS"
            
        Returns:
            timedelta: Duration as interval
        """
        try:
            hours, minutes, seconds = map(int, duration_str.split(':'))
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except (ValueError, AttributeError):
            return timedelta(0)
            
    def close(self):
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._logger.info("Database connection closed") 