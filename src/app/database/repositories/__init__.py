from database.repositories.movie_repository import MovieRepository
from database.repositories.actress_repository import ActressRepository
from database.repositories.genre_repository import GenreRepository

# 创建仓储实例
movie_repository = MovieRepository()
actress_repository = ActressRepository()
genre_repository = GenreRepository()