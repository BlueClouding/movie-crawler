class VideoInfo:
    def __init__(self, id, url, title='', duration='00:00:00', release_date='1970-01-01', code='',
                 actresses=None, genres=None, maker='Das!', series='', likes=0,
                 magnets=None, description='', tags=None, director='', cover_image_url='',
                 preview_video_url='', thumbnail=''):
        self.id = id
        self.url = url
        self.title = title
        self.duration = duration
        self.release_date = release_date
        self.code = code
        self.actresses = actresses if actresses is not None else []
        self.genres = genres if genres is not None else []
        self.maker = maker
        self.series = series
        self.likes = likes
        self.magnets = magnets if magnets is not None else []
        self.description = description
        self.tags = tags if tags is not None else []
        self.director = director
        self.cover_image_url = cover_image_url
        self.preview_video_url = preview_video_url
        self.thumbnail = thumbnail

    def __repr__(self):
        return (f"VideoInfo(id='{self.id}', url='{self.url}', title='{self.title}', duration='{self.duration}', "
                f"release_date='{self.release_date}', code='{self.code}', "
                f"actresses={self.actresses}, genres={self.genres}, maker='{self.maker}', "
                f"series='{self.series}', likes={self.likes}, magnets={self.magnets}, "
                f"description='{self.description}', tags={self.tags}, director='{self.director}', "
                f"cover_image_url='{self.cover_image_url}', preview_video_url='{self.preview_video_url}', "
                f"thumbnail='{self.thumbnail}')")