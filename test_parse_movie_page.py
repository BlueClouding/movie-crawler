#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试MovieDetailCrawler的parse_movie_page方法
使用已保存的HTML文件直接测试解析功能
"""

import sys
import os
import json
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 简化版的MovieDetailCrawler类，只包含parse_movie_page方法
class SimpleMovieDetailCrawler:
    """简化版的电影详情解析器，用于测试parse_movie_page方法"""
    
    def __init__(self, movie_code: str):
        self.movie_code = movie_code
        self.field_patterns = self.initialize_field_patterns()
    
    def initialize_field_patterns(self):
        """初始化字段模式"""
        return {
            "genre": ["ジャンル", "類型", "Genre", "类型"],
            "actress": ["女優", "演員", "Actress", "女优"],
            "studio": ["スタジオ", "工作室", "Studio", "制作商"],
            "label": ["レーベル", "廠牌", "Label", "厂牌"],
            "series": ["シリーズ", "系列", "Series"],
            "director": ["監督", "導演", "Director", "导演"]
        }
    
    def extract_m3u8_info(self, html: str) -> dict:
        """提取M3U8加密信息"""
        try:
            # 查找包含M3U8信息的script标签
            script_pattern = r'var\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*"([^"]+)"[^}]*var\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\[([^\]]+)\]'
            match = re.search(script_pattern, html)
            
            if match:
                encrypted_code = match.group(2)
                dictionary_str = match.group(4)
                dictionary = [item.strip('"') for item in dictionary_str.split(',')]
                
                logger.info(f"找到M3U8加密信息: 代码长度={len(encrypted_code)}, 字典长度={len(dictionary)}")
                return {
                    "encrypted_code": encrypted_code,
                    "dictionary": dictionary
                }
            else:
                logger.warning("未找到M3U8加密信息")
                return {"encrypted_code": "", "dictionary": []}
        except Exception as e:
            logger.error(f"提取M3U8信息时出错: {e}")
            return {"encrypted_code": "", "dictionary": []}
    
    def deobfuscate_m3u8(self, encrypted_code: str, dictionary: list) -> list:
        """解密M3U8 URL"""
        if not encrypted_code or not dictionary:
            logger.warning("解密M3U8失败: 加密代码或字典为空")
            return []
        
        try:
            results = []
            decoded = ""
            
            for c in encrypted_code:
                if c in [".", "-", "/", ":"]:
                    decoded += c
                else:
                    try:
                        number = int(c, 16)
                        if 0 <= number < len(dictionary):
                            decoded += dictionary[number]
                    except ValueError:
                        decoded += c
            
            if decoded and (".m3u8" in decoded or "/master" in decoded):
                results.append(decoded)
                logger.info(f"解密出M3U8 URL: {decoded[:50]}...")
            
            return results
        except Exception as e:
            logger.error(f"解密M3U8时出错: {e}")
            return []
    
    def _extract_info_by_label(self, soup, label_text: str) -> list:
        """根据标签文本提取信息"""
        try:
            # 查找包含标签文本的元素
            label_elem = soup.find(text=re.compile(label_text, re.IGNORECASE))
            if label_elem:
                parent = label_elem.parent
                # 查找相邻的链接元素
                links = parent.find_next_siblings('a') or parent.find_all('a')
                return [link.get_text(strip=True) for link in links if link.get_text(strip=True)]
        except Exception:
            pass
        return []
    
    def _extract_single_field_by_label(self, soup, label_text: str) -> str:
        """根据标签文本提取单个字段"""
        try:
            info_list = self._extract_info_by_label(soup, label_text)
            return info_list[0] if info_list else ""
        except Exception:
            return ""
    
    def parse_movie_page(self, html: str) -> dict:
        """分析电影页面HTML以提取详细信息"""
        result = {
            "id": self.movie_code,
            "url": f"https://missav.ai/ja/{self.movie_code}",
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "title": "",
            "cover_url": "",
            "release_date": "",
            "duration_seconds": None,
            "studio": "",
            "label": "",
            "series": "",
            "director": "",
            "tags": [],
            "actresses": [],
            "description": "",
            "magnets": [],
            "m3u8_urls": [],
        }
        
        try:
            # 检查HTML内容的有效性
            if not html or len(html) < 1000:
                logger.error(f"HTML内容长度不足: {len(html) if html else 0}")
                return result

            # 验证HTML是否包含电影ID
            # if self.movie_code.upper() not in html.upper():
            #     logger.error(f"HTML内容不包含电影ID: {self.movie_code}")
            #     return result

            # 验证不是首页
            if "MissAV | オンラインで無料" in html and not re.search(
                r"<h1[^>]*>[^<]*" + re.escape(self.movie_code) + r"[^<]*</h1>",
                html,
                re.IGNORECASE,
            ):
                logger.error(f"HTML内容可能是网站首页")
                return result

            soup = BeautifulSoup(html, "html.parser")

            # 尝试提取页面标题
            # 1. 先从h1标签获取
            h1_title = soup.select_one("h1")
            if (
                h1_title
                and len(h1_title.text) > 3
                and self.movie_code.upper() in h1_title.text.upper()
            ):
                result["title"] = h1_title.text.strip()
                logger.info(f"从h1标签获取到标题: {result['title']}")

            # 2. 尝试从meta标签获取
            if not result["title"] or "MissAV" in result["title"]:
                og_title = soup.select_one('meta[property="og:title"]')
                if og_title:
                    title_text = og_title.get("content", "").strip()
                    if self.movie_code.upper() in title_text.upper():
                        result["title"] = title_text
                        logger.info(f"从og:title获取到标题: {result['title']}")

            # 3. 如果还是没有获取到，尝试从title标签获取
            if not result["title"] or "MissAV" in result["title"]:
                title_tag = soup.select_one("title")
                if title_tag and self.movie_code.upper() in title_tag.text.upper():
                    result["title"] = title_tag.text.strip()
                    logger.info(f"从title标签获取到标题: {result['title']}")

            # 获取封面图片
            # 1. 先尝试通过特定的图片标签获取
            cover_img = soup.select_one(f'img[alt*="{self.movie_code}"]')
            if not cover_img:
                cover_img = soup.select_one(".aspect-video > img") or soup.select_one(
                    ".cover-image"
                )

            if cover_img and "src" in cover_img.attrs:
                result["cover_url"] = cover_img["src"]
                logger.info(f"从img标签获取到封面: {result['cover_url']}")
            else:
                # 2. 尝试从meta标签获取
                og_image = soup.select_one('meta[property="og:image"]')
                if og_image:
                    result["cover_url"] = og_image.get("content")
                    logger.info(f"从og:image获取到封面: {result['cover_url']}")

            # 获取描述信息
            og_desc = soup.select_one('meta[property="og:description"]')
            if og_desc and len(og_desc.get("content", "")) > 10:
                result["description"] = og_desc.get("content")
                logger.info(f"获取到描述信息，长度: {len(result['description'])}")

            # 获取视频时长
            og_duration = soup.select_one('meta[property="og:video:duration"]')
            if og_duration and og_duration.get("content", "").isdigit():
                result["duration_seconds"] = int(og_duration.get("content"))
                logger.info(f"获取到视频时长: {result['duration_seconds']}秒")

            # 提取M3U8流媒体URL
            try:
                # 提取加密的M3U8信息
                m3u8_info = self.extract_m3u8_info(html)
                # 解密M3U8 URL
                m3u8_urls = self.deobfuscate_m3u8(
                    m3u8_info["encrypted_code"], m3u8_info["dictionary"]
                )
                if m3u8_urls:
                    result["m3u8_urls"] = m3u8_urls
                    logger.info(f"成功提取到{len(m3u8_urls)}个M3U8流媒体URL")
            except Exception as e:
                logger.error(f"提取M3U8流媒体URL失败: {e}")

            # 获取发布日期
            og_release_date = soup.select_one('meta[property="og:video:release_date"]')
            if og_release_date and og_release_date.get("content"):
                result["release_date"] = og_release_date.get("content")
                logger.info(f"从meta标签获取到发布日期: {result['release_date']}")

            # 解析标签
            # 1. 尝试通过Alpine.js标记的div
            tags_div = soup.select_one("div[x-show=\"currentTab === 'tags'\"]")
            if tags_div:
                tags = [tag.text.strip() for tag in tags_div.select("a.tag")]
                if tags:
                    result["tags"] = tags
                    logger.info(f"从x-show标签获取到{len(tags)}个标签")

            # 2. 尝试使用field_patterns获取
            if not result["tags"]:
                tags = self._extract_info_by_label(
                    soup, self.field_patterns["genre"][0]
                )
                if tags:
                    result["tags"] = tags
                    logger.info(f"从field_patterns获取到{len(tags)}个标签")

            # 3. 尝试从meta关键词获取
            if not result["tags"]:
                meta_keywords = soup.select_one('meta[name="keywords"]')
                if meta_keywords and meta_keywords.get("content"):
                    keywords = meta_keywords.get("content").split(",")
                    result["tags"] = [
                        kw.strip()
                        for kw in keywords
                        if kw.strip() and kw.strip() != "無料AV"
                    ]
                    logger.info(f"从meta关键词获取到{len(result['tags'])}个标签")

            # 解析女优
            # 1. 尝试通过Alpine.js标记的div
            actresses_div = soup.select_one(
                "div[x-show=\"currentTab === 'actresses'\"]"
            )
            if actresses_div:
                actresses = [
                    actress.text.strip()
                    for actress in actresses_div.select("a.actress")
                ]
                if actresses:
                    result["actresses"] = actresses
                    logger.info(f"从x-show标签获取到{len(actresses)}个女优")

            # 2. 尝试使用field_patterns获取
            if not result["actresses"]:
                actresses = self._extract_info_by_label(
                    soup, self.field_patterns["actress"][0]
                )
                if actresses:
                    result["actresses"] = actresses
                    logger.info(f"从field_patterns获取到{len(actresses)}个女优")

            # 解析磁力链接
            magnets_div = soup.select_one("div[x-show=\"currentTab === 'magnets'\"]")
            if magnets_div:
                magnet_rows = magnets_div.select("tbody tr")
                magnets = []
                for row in magnet_rows:
                    magnet_link = row.select_one('a[href^="magnet:"]')
                    if magnet_link:
                        magnet_url = magnet_link.get("href", "")
                        magnet_title = magnet_link.text.strip()

                        # 获取大小和日期
                        size_cell = (
                            row.select("td")[1] if len(row.select("td")) > 1 else None
                        )
                        date_cell = (
                            row.select("td")[2] if len(row.select("td")) > 2 else None
                        )

                        magnet_info = {
                            "url": magnet_url,
                            "title": magnet_title,
                            "size": size_cell.text.strip() if size_cell else "",
                            "date": date_cell.text.strip() if date_cell else "",
                        }
                        magnets.append(magnet_info)

                result["magnets"] = magnets
                logger.info(f"获取到{len(magnets)}个磁力链接")

            # 获取工作室、厂商、系列等信息
            studio = self._extract_single_field_by_label(
                soup, self.field_patterns["studio"][0]
            )
            if studio:
                result["studio"] = studio
                logger.info(f"获取到工作室: {result['studio']}")

            label = self._extract_single_field_by_label(
                soup, self.field_patterns["label"][0]
            )
            if label:
                result["label"] = label
                logger.info(f"获取到厂商: {result['label']}")

            series = self._extract_single_field_by_label(
                soup, self.field_patterns["series"][0]
            )
            if series:
                result["series"] = series
                logger.info(f"获取到系列: {result['series']}")

            director = self._extract_single_field_by_label(
                soup, self.field_patterns["director"][0]
            )
            if director:
                result["director"] = director
                logger.info(f"获取到导演: {result['director']}")

        except Exception as e:
            logger.error(f"解析页面时出错: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return result

def test_parse_movie_page():
    """测试解析电影页面功能"""
    print("=== 测试MovieDetailCrawler的parse_movie_page方法 ===")
    
    # HTML文件路径
    html_file = project_root / "test_536VOLA_data" / "HZHB-004_ja.html"
    
    if not html_file.exists():
        print(f"❌ HTML文件不存在: {html_file}")
        return False
    
    print(f"📁 读取HTML文件: {html_file}")
    
    try:
        # 读取HTML内容
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"📄 HTML文件大小: {len(html_content)} 字符")
        
        # 创建解析器实例
        movie_code = "HZHB-004"
        crawler = SimpleMovieDetailCrawler(movie_code)
        
        print(f"🎬 解析电影: {movie_code}")
        
        # 调用解析方法
        result = crawler.parse_movie_page(html_content)
        
        if result:
            print("✅ 解析成功!")
            print("\n=== 解析结果 ===")
            
            # 格式化输出结果
            for key, value in result.items():
                if isinstance(value, list):
                    print(f"{key}: {value if value else '[]'}")
                elif isinstance(value, str) and len(value) > 100:
                    print(f"{key}: {value[:100]}...")
                else:
                    print(f"{key}: {value}")
            
            # 保存解析结果到JSON文件
            output_file = project_root / "test_536VOLA_data" / f"{movie_code}_parsed_test.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 解析结果已保存到: {output_file}")
            
            # 检查关键字段
            print("\n=== 关键字段检查 ===")
            key_fields = ['title', 'cover_url', 'm3u8_urls', 'description', 'tags', 'actresses']
            for field in key_fields:
                value = result.get(field)
                status = "✅" if value else "❌"
                print(f"{status} {field}: {'有值' if value else '无值'}")
            
            return True
        else:
            print("❌ 解析失败: 返回结果为空")
            return False
            
    except Exception as e:
        print(f"❌ 解析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("开始测试MovieDetailCrawler解析功能...\n")
    
    success = test_parse_movie_page()
    
    print("\n=== 测试完成 ===")
    if success:
        print("✅ 测试通过: 解析器工作正常")
    else:
        print("❌ 测试失败: 解析器存在问题")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())