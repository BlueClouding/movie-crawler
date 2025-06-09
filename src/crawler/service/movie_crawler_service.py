"""
Movie crawler service module.

This module provides a wrapper around the MovieDetailCrawlerService
to maintain backward compatibility with code that imports MovieCrawlerService.
"""

from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService

# For backward compatibility, create an alias
MovieCrawlerService = MovieDetailCrawlerService
