from bs4 import BeautifulSoup
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
import psycopg2
from urllib.parse import urljoin

@dataclass
class Actress:
    name: str
    avatar_url: str
    detail_url: str
    video_count: int

class ActressProcessor:
    def __init__(self, db_connection):
        self.db_conn = db_connection
        self.base_url = "https://123av.com"
        
    def parse_actress_list(self, html: str) -> List[Actress]:
        """解析演员列表页面"""
        soup = BeautifulSoup(html, 'html.parser')
        actresses = []
        
        for item in soup.select('.bl-item'):
            try:
                name = item.select_one('.name').text.strip()
                avatar = item.select_one('.avatar img')['src']
                detail_url = item.select_one('a')['href']
                video_count = int(item.select_one('.text-muted').text.split()[0])
                
                actresses.append(Actress(
                    name=name,
                    avatar_url=avatar,
                    detail_url=detail_url,
                    video_count=video_count
                ))
            except Exception as e:
                print(f"解析演员信息失败: {e}")
                continue
                
        return actresses
    
    def save_actress(self, actress: Actress) -> Optional[int]:
        """保存演员信息到数据库"""
        try:
            with self.db_conn.cursor() as cur:
                # 插入演员基本信息
                cur.execute("""
                    INSERT INTO actresses DEFAULT VALUES
                    RETURNING id
                """)
                actress_id = cur.fetchone()[0]
                
                # 插入演员名称（日语）
                cur.execute("""
                    INSERT INTO actress_names (actress_id, language, name)
                    VALUES (%s, 'ja', %s)
                """, (actress_id, actress.name))
                
                self.db_conn.commit()
                return actress_id
        except Exception as e:
            print(f"保存演员信息失败: {e}")
            self.db_conn.rollback()
            return None
    
    def process_page(self, page: int) -> bool:
        """处理单个页面"""
        url = f"{self.base_url}/ja/actresses?page={page}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            actresses = self.parse_actress_list(response.text)
            for actress in actresses:
                self.save_actress(actress)
            
            return True
        except Exception as e:
            print(f"处理页面 {page} 失败: {e}")
            return False
    
    def process_all(self, start_page: int = 1, end_page: int = 982):
        """处理所有页面"""
        for page in range(start_page, end_page + 1):
            print(f"正在处理第 {page} 页...")
            if not self.process_page(page):
                print(f"处理第 {page} 页失败，跳过继续处理")
                continue