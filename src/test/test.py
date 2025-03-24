import string
from bs4 import BeautifulSoup
import requests
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
import time

def extract_movie_info():
    url = 'https://missav.ai/dm5/en/shmo-162'

    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=header)
    html_content = response.text

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 提取DVD ID
    dvd_id = None
    meta_og_url = soup.find('meta', property='og:url')
    if meta_og_url and meta_og_url.get('content'):
        url = meta_og_url['content']
        dvd_id = url.split('/')[-1]  # 从URL中提取ID
    else:
        # 如果og:url不可用，尝试从<title>中提取
        title_tag = soup.find('title')
        if title_tag:
            dvd_id = title_tag.text.split()[0]  # 假设ID在标题开头
    
    # 提取m3u8链接
    encrypted_code, dictionary = extract_m3u8_info(soup)
    m3u8_info = deobfuscate_m3u8(encrypted_code, dictionary)
    
    # 提取封面URL
    cover_url = None
    meta_og_image = soup.find('meta', property='og:image')
    if meta_og_image and meta_og_image.get('content'):
        cover_url = meta_og_image['content']
    
    # 提取标题
    title = None
    meta_title = soup.find('meta', property='og:title')
    if meta_title and meta_title.get('content'):
        title = meta_title['content']
    
    # 提取介绍
    description = None
    meta_desc = soup.find('meta', property='og:description')
    if meta_desc and meta_desc.get('content'):
        description = meta_desc['content']
    
    # 提取发布日期
    release_date = None
    meta_date = soup.find('meta', property='og:video:release_date')
    if meta_date and meta_date.get('content'):
        release_date = meta_date['content']
    
    # 提取时长
    duration = None
    meta_duration = soup.find('meta', property='og:video:duration')
    if meta_duration and meta_duration.get('content'):
        duration = meta_duration['content']
    
    # 提取演员
    actor = None
    meta_actor = soup.find('meta', property='og:video:actor')
    if meta_actor and meta_actor.get('content'):
        actor = meta_actor['content']
    
    # 提取其他信息（系列、メーカー、レーベル、ジャンル）
    series, maker, label, genres = None, None, None, []
    info_div = soup.find('div', class_='space-y-2')  # 假设信息在某个div中
    if info_div:
        for div in info_div.find_all('div', class_='text-secondary'):
            text = div.text.strip()
            if 'シリーズ:' in text:
                series = text.split(':')[1].strip()
            elif 'メーカー:' in text:
                maker = text.split(':')[1].strip()
            elif 'レーベル:' in text:
                label = text.split(':')[1].strip()
            elif 'ジャンル:' in text:
                genres = [genre.strip() for genre in text.split(':')[1].split(',')]
    
    # 整合所有信息
    movie_info = {
        'dvd_id': dvd_id,
        'm3u8_info': m3u8_info,
        'cover_url': cover_url,
        'title': title,
        'description': description,
        'release_date': release_date,
        'duration': duration,
        'actor': actor,
        'series': series,
        'maker': maker,
        'label': label,
        'genres': genres
    }
    
    return movie_info

def extract_m3u8_info(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[List[str]]]:
    """从网页中提取加密代码和字典信息"""
    return extract_encrypted_code(soup)

def extract_encrypted_code(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[List[str]]]:
    scripts = soup.find_all('script')
    
    # 匹配特征代码结构
    pattern = re.compile(r"eval\(function\(p,a,c,k,e,d\)\{(.+?)\}\('(.+?)',([0-9]+),([0-9]+),'(.+?)'\.(split\('\|'\)|split\('\|'\),0,\{\})\)\)")
    
    for script in scripts:
        if script.string and 'eval(function(p,a,c,k,e,d)' in script.string:
            match = pattern.search(script.string)
            if match:
                # 提取字典部分
                dictionary_str = match.group(5)
                dictionary = dictionary_str.split('|')
                # 提取加密代码部分
                encrypted_code = match.group(2)
                return encrypted_code, dictionary
    return None, None


def deobfuscate_m3u8(encrypted_code, dictionary):
    # 分割加密字符串为独立语句
    parts = [p.split('=')[1].strip("';") for p in encrypted_code.split(';') if p]
    
    results = []
    for part in parts:
        # 去掉\\
        part = part.replace('\\', '')
        # 去掉'
        part = part.replace("'", '')
        # 去掉"
        part = part.replace('"', '')
        # 去掉空格
        part = part.replace(' ', '')
    
        # 遍历part的每个字符
        decoded : string = ''
        for char in part:
            if char not in ['.', '-', '/', ':']:
                # char为16进制
                number = int(char, 16)
                decoded += dictionary[number]
            else:
                decoded += char
        
        results.append(decoded)
            
    return results

# 使用示例
if __name__ == "__main__":
    #计算用时
    start_time = time.time()

    # 提取信息
    info = extract_movie_info()
    
    # 打印结果
    print("影片信息:")
    print(f"DVD ID: {info['dvd_id']}")
    print("M3U8 链接:" + str(info['m3u8_info']))
    print(f"封面 URL: {info['cover_url']}")
    print(f"标题: {info['title']}")
    print(f"介绍: {info['description']}")
    print(f"发布日期: {info['release_date']}")
    print(f"时长: {info['duration']} 秒")
    print(f"演员: {info['actor']}")
    print(f"系列: {info['series']}")
    print(f"メーカー: {info['maker']}")
    print(f"レーベル: {info['label']}")
    print(f"ジャンル: {', '.join(info['genres'])}")
    
    #计算用时
    end_time = time.time()
    print(f"用时: {end_time - start_time} 秒")