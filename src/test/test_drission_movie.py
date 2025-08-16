"""
使用 DrissionPage 爬取电影详情页面并支持多语言版本。
"""

import os
import sys
import re
import json
import time
import traceback
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path
from loguru import logger
from bs4 import BeautifulSoup

# 将项目根目录添加到 Python 路径
# sys.path.append(str(Path(__file__).parent.parent))

# 因为是单个文件运行，所以直接导入
from app.utils.drission_utils import CloudflareBypassBrowser
from common.enums.enums import SupportedLanguage


class MovieDetailCrawler:
    """
    电影详情爬虫类，使用 DrissionPage 绕过 Cloudflare 检测
    支持抓取不同语言版本的电影详情页面

    注意：这是一个测试版本。按照模块化设计，该类应分割成：
    1. 解析器部分（parsers/movie_parser.py）
    2. 爬虫核心部分（core/detail_crawler.py）
    3. 数据存储部分（db/operations.py）
    """

    def __init__(self, movie_code: str):
        """
        初始化电影详情爬虫

        Args:
            movie_code: 电影代码，如 'shmo-162'，FC2-PPV-1020621
        """
        self.movie_code = movie_code
        self.language = "ja"  # 默认使用日语

        # 创建浏览器数据持久化目录
        self.user_data_dir = Path.home() / ".cache" / "cloudflare_bypass_browser"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化浏览器
        self.browser = None

        # 支持的所有语言列表
        self.languages = [
            "en",
            "ja",
            "",
            "zh",
            "ko",
            "ms",
            "th",
            "de",
            "fr",
            "vi",
            "id",
            "fil",
            "pt",
            "hi",
        ]

        # 初始化字段模式
        self.field_patterns = self.initialize_field_patterns()

    def setup_browser(self, headless: bool = False):
        """
        设置 CloudflareBypassBrowser

        Args:
            headless: 是否以无头模式运行
        """
        self.browser = CloudflareBypassBrowser(
            headless=headless,
            user_data_dir=str(self.user_data_dir),
            load_images=True,
            timeout=60,
        )
        try:
            self.browser.page.run_js("window.resizeTo(1280, 800);")
        except Exception:
            pass
        logger.info("浏览器初始化完成")

    def get_new_browser_instance(self, headless: bool = True):
        """
        创建新的浏览器实例，用于并行爬取
        """
        try:
            instance_id = int(time.time() * 1000)
            user_data_dir = (
                Path.home()
                / ".cache"
                / f"cloudflare_bypass_browser_parallel_{instance_id}"
            )
            user_data_dir.mkdir(exist_ok=True, parents=True)
            browser = CloudflareBypassBrowser(
                headless=headless,
                user_data_dir=str(user_data_dir),
                load_images=False,
                timeout=30,
            )
            return browser
        except ImportError as e:
            logger.error(f"导入CloudflareBypassBrowser出错: {e}")
            raise
        except Exception as e:
            logger.error(f"创建并行浏览器实例出错: {e}")
            raise

    def get_base_page(self) -> bool:
        """
        访问基础URL并通过Cloudflare挑战
        """
        base_url = f"https://missav.ai/{self.language}/{self.movie_code}"
        try:
            logger.info("访问页面并等待自动通过Cloudflare检测...")
            self.browser.get(base_url, timeout=20)  # 增加超时时间

            # 等待页面加载，CloudflareBypassBrowser会自动处理大部分挑战
            # 不需要额外的等待，get方法已经处理了等待

            # 检查页面是否加载成功
            html = self.browser.html
            if not html or len(html) < 500 or "missav" not in html.lower():
                logger.warning("页面可能未正确加载或被Cloudflare拦截")
                return False

            logger.info("页面加载成功")
            return True

        except Exception as e:
            logger.error(f"访问基础页面时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False

    def crawl(self, headless: bool = False) -> Dict:
        """
        爬取日语版本的电影详情
        """
        # FIX: Initialize base_data to prevent UnboundLocalError
        base_data = {}

        if not self.browser:
            self.setup_browser(headless=headless)

        try:
            base_url = f"https://missav.ai/{self.language}/{self.movie_code}"
            logger.info(f"正在访问URL: {base_url}")

            if not self.get_base_page():
                logger.error("获取基础页面失败，无法继续。")
                return base_data  # Return empty dict

            logger.info("页面已成功加载！正在解析...")
            html = self.browser.html

            # FIX: Correctly call parse_movie_page with 2 arguments (self, html)
            base_data = self.parse_movie_page(html)

            if not base_data.get("title"):
                logger.warning("未能解析出标题，可能页面结构已更改或加载不完整。")
            else:
                title = base_data.get("title", "无标题")
                actresses = ", ".join(base_data.get("actresses", [])[:3])
                if len(base_data.get("actresses", [])) > 3:
                    actresses += "..."
                logger.info(
                    f"- 已解析: {title[:40]}{'...' if len(title) > 40 else ''} | {actresses}"
                )

        except Exception as e:
            logger.error(f"爬虫主流程出错: {e}")
            logger.debug(traceback.format_exc())
        finally:
            # Clean up resources
            try:
                if self.browser:
                    self.browser.close()  # 使用close而不是quit
                    logger.info("浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器出错: {e}")

        return base_data

    def crawl_movie_in_language(self, language: str) -> Optional[Dict]:
        """
        (未使用的方法) 爬取特定语言版本的电影详情以支持并行处理
        """
        lang_browser = None
        try:
            lang_browser = self.get_new_browser_instance(headless=True)
            url = f"https://missav.ai/{language}/{self.movie_code}"
            logger.info(f"并行爬取: 开始访问{language}语言版本: {url}")

            max_retries = 2
            for i in range(max_retries):
                try:
                    lang_browser.get(url, timeout=15)
                    lang_browser.wait.load_start(timeout=5)
                    html = lang_browser.html

                    if not html or len(html) < 1000 or "missav" not in html.lower():
                        logger.warning(
                            f"[{language}]页面可能未正确加载，重试({i+1}/{max_retries})"
                        )
                        time.sleep(2)
                        continue

                    logger.info(f"[{language}]页面加载成功，开始解析内容")
                    result = self.parse_movie_page(html)  # Call fixed method

                    if result and result.get("title"):
                        # FIX: Pass correct arguments to save_to_json
                        self.save_to_json(result, language)
                        return result
                    else:
                        logger.warning(
                            f"[{language}]页面解析失败，重试({i+1}/{max_retries})"
                        )
                        time.sleep(2)

                except Exception as e:
                    logger.error(
                        f"[{language}]访问错误 (尝试 {i+1}/{max_retries}): {str(e)}"
                    )
                    time.sleep(2)

            logger.error(f"[{language}]在{max_retries}次尝试后仍未成功获取数据")
            return None

        except Exception as e:
            logger.error(f"[{language}]并行爬取错误: {str(e)}")
            return None
        finally:
            if lang_browser:
                try:
                    lang_browser.close()  # 使用close而不是quit
                    logger.debug(f"[{language}]已关闭并行爬取浏览器实例")
                except Exception:
                    pass

    def initialize_field_patterns(self) -> Dict[str, List[str]]:
        return {
            "releaseDate": ["配信開始日"],
            "studio": ["メーカー"],
            "series": ["シリーズ"],
            "label": ["レーベル"],
            "genre": ["ジャンル"],
            "actress": ["女優"],
            "director": ["監督"],
        }

    def _extract_info_by_label(self, soup: BeautifulSoup, label: str) -> List[str]:
        values = []
        try:
            label_span = soup.find("span", string=lambda t: t and label in t)
            if label_span:
                container = label_span.parent
                links = container.select("a")
                if links:
                    for link in links:
                        if link.text.strip():
                            values.append(link.text.strip())
        except Exception as e:
            logger.warning(f"提取标签 '{label}' 信息时出错: {e}")
        return values

    def _extract_single_field_by_label(self, soup: BeautifulSoup, label: str) -> str:
        links = self._extract_info_by_label(soup, label)
        return links[0] if links else ""

    def extract_m3u8_info(self, html: str) -> Dict[str, Any]:
        """
        从HTML中提取M3U8加密信息

        Args:
            html: 包含JavaScript加密代码的HTML内容

        Returns:
            Dict: 包含encrypted_code和dictionary的字典
        """
        result = {"encrypted_code": None, "dictionary": None}
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.select("script")

        # 正则表达式模式，匹配加密的JavaScript代码
        # 改进后的正则表达式，使用 ['"] 匹配单引号或双引号
        pattern = re.compile(
            r"eval\(function\(p,a,c,k,e,d\)\{(.+?)\}\(['\"](.+?)['\"],([0-9]+),([0-9]+),['\"](.+?)['\"]\."
            r"((?:split\(['\"]\|['\"]\))|(?:split\(['\"]\|['\"]\),0,\{\}))\)"
)
        for script in scripts:
            script_content = script.string
            if script_content and "eval(function(p,a,c,k,e,d)" in script_content:
                matcher = pattern.search(script_content)
                if matcher:
                    dictionary_str = matcher.group(5)
                    dictionary = dictionary_str.split("|") if dictionary_str else []
                    encrypted_code = matcher.group(2)
                    result["encrypted_code"] = encrypted_code
                    result["dictionary"] = dictionary
                    logger.info(f"成功提取到M3U8加密信息，字典长度: {len(dictionary)}")
                    return result

        logger.warning("未找到M3U8加密信息")
        return result

    def deobfuscate_m3u8(
        self, encrypted_code: Optional[str], dictionary: Optional[List[str]]
    ) -> List[str]:
        """
        解密M3U8 URL信息

        Args:
            encrypted_code: 加密的代码
            dictionary: 用于解密的字典

        Returns:
            List[str]: 解密后的M3U8 URL列表
        """
        if not encrypted_code or not dictionary:
            logger.warning("解密M3U8失败: 加密代码或字典为空")
            return []

        parts = encrypted_code.split(";")
        results = []

        for part in parts:
            if "=" not in part:
                continue

            # 提取值部分，去除引号、反斜杠和空格
            value = (
                part.split("=")[1]
                .replace('"', "")
                .replace("'", "")
                .replace("\\", "")
                .replace(" ", "")
            )

            decoded = ""
            for c in value:
                if c in [".", "-", "/", ":"]:
                    decoded += c
                else:
                    try:
                        number = int(c, 16)
                        if 0 <= number < len(dictionary):
                            decoded += dictionary[number]
                    except ValueError:
                        # 如果不是十六进制字符，保留原字符
                        decoded += c

            if decoded and (".m3u8" in decoded or "/master" in decoded):
                results.append(decoded)
                logger.info(f"解密出M3U8 URL: {decoded[:50]}...")

        return results

    def parse_movie_page(self, html: str) -> Dict:
        """
        分析电影页面HTML以提取详细信息 (日语专用)
        """
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
            # 检查HTML内容的有效性 - 更严格的检查
            if not html or len(html) < 1000:
                logger.error(f"HTML内容长度不足: {len(html) if html else 0}")
                return result

            # # 验证HTML是否包含电影ID
            # if self.movie_code.upper() not in html.upper():
            #     logger.error(f"HTML内容不包含电影ID: {self.movie_code}")
            #     return result

            # 验证不是首页
            if "任意の検索" in html:
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
            else:
                # 尝试从页面元素获取
                for duration_elem in soup.select('span:-soup-contains("長度") + span'):
                    duration_text = duration_elem.text.strip()
                    # 尝试解析例如 '120分钟' 这样的格式
                    if "分" in duration_text:
                        try:
                            minutes = int(re.search(r"(\d+)分", duration_text).group(1))
                            result["duration_seconds"] = minutes * 60
                            logger.info(
                                f"从页面元素获取到视频时长: {result['duration_seconds']}秒"
                            )
                            break
                        except (ValueError, AttributeError):
                            pass

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
            else:
                # 尝试从页面元素获取
                for date_elem in soup.select(
                    'span:-soup-contains("発売日") + span, span:-soup-contains("発売") + span'
                ):
                    date_text = date_elem.text.strip()
                    if date_text and (
                        re.match(r"\d{4}-\d{2}-\d{2}", date_text)
                        or re.match(r"\d{4}/\d{2}/\d{2}", date_text)
                    ):
                        result["release_date"] = date_text
                        logger.info(
                            f"从页面元素获取到发布日期: {result['release_date']}"
                        )
                        break

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
            logger.debug(traceback.format_exc())
        return result

    def close(self):
        if self.browser:
            self.browser.close()  # 使用close而不是quit
            self.browser = None

    def save_to_json(self, movie_info: dict, language: str):
        """
        FIX: Adjusted method to correctly handle language parameter for filename.
        """
        if not movie_info or not movie_info.get("id"):
            logger.warning("没有有效的电影信息可保存。")
            return

        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        filename = f"{self.movie_code}_{language}.json"
        output_file = data_dir / filename

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(movie_info, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存 {language} 版本电影信息到 {output_file}")


def batch_crawl_movies(
    movie_codes, headless=False, max_retries=2, delay_between_movies=0.5
):
    """
    批量爬取多个电影信息

    Args:
        movie_codes: 电影ID列表
        headless: 是否使用无头模式
        max_retries: 最大重试次数
        delay_between_movies: 电影之间的延迟时间(秒)

    Returns:
        爬取结果字典 {movie_code: movie_info}
    """
    results = {}
    browser = None

    try:
        # 创建一个共享的浏览器实例，提高性能
        browser = CloudflareBypassBrowser(
            headless=headless,
            user_data_dir=str(Path.home() / ".cache" / "cloudflare_bypass_browser"),
            load_images=True,  # 加载图片以确保网站正常工作 (Cloudflare可能会检测)
            timeout=30,  # 合理的超时时间
            wait_after_cf=3,  # 缩短 Cloudflare 后的等待时间
        )

        # 先访问一次基础页面，通过Cloudflare挑战
        logger.info("初始化浏览器并通过Cloudflare挑战...")
        browser.get("https://missav.ai/", timeout=60)
        time.sleep(10)  # 提供足够的时间等待Cloudflare挑战完成

        # 优化浏览器性能的JS代码
        performance_js = """
        // 阻止不必要的资源加载
        window.stopUnnecessaryLoading = function() {
            // 阻止视频、音频、大图片等资源
            window._origFetch = window.fetch;
            window.fetch = function(url, options) {
                if (typeof url === 'string') {
                    if (url.includes('.m3u8') || url.includes('.mp4') || 
                        url.includes('.webm') || url.includes('.mp3') || 
                        url.includes('videodelivery') || url.includes('stream')) {
                        return new Promise((resolve) => {
                            resolve(new Response('', {status: 200}));
                        });
                    }
                }
                return window._origFetch(url, options);
            };
            
            // 清理内存
            if (window.gc) window.gc();
            
            // 返回成功
            return true;
        };
        """

        # 执行性能优化JS
        browser.page.run_js(performance_js)

        for i, movie_code in enumerate(movie_codes):
            logger.info(
                f"[{i+1}/{len(movie_codes)}] 开始爬取电影: {movie_code} (日语版本)"
            )

            # 创建爬虫实例但复用已有浏览器
            crawler = MovieDetailCrawler(movie_code=movie_code)
            crawler.browser = browser  # 使用共享浏览器实例

            # 添加重试逻辑
            for attempt in range(max_retries):
                try:
                    # 直接访问电影页面
                    url = f"https://missav.ai/ja/{movie_code}"
                    logger.info(f"正在访问URL: {url}")

                    # 使用优化的页面加载方式
                    browser.get(url, timeout=30)

                    # 等待Cloudflare挑战解决
                    logger.info("等待页面完全加载...")
                    time.sleep(2)  # 增加基本等待时间

                    # 验证当前网址确实是电影页面而不是首页
                    current_url = browser.page.url
                    logger.info(f"当前页面URL: {current_url}")
                    if movie_code not in current_url:
                        logger.warning(
                            f"访问电影页面失败，可能被重定向到首页，重试开启新标签页直接访问"
                        )
                        # 尝试开启新标签页直接访问
                        new_tab = browser.page.new_tab(url, new_window=False)
                        time.sleep(5)  # 等待新标签页加载

                        # 切换到新标签页并确保获取更新后的HTML内容
                        browser.page = new_tab  # 确保 browser.page 引用新标签页
                        time.sleep(2)  # 等待页面加载
                        logger.info(
                            f"After switch, current page URL: {browser.page.url}"
                        )

                    # 检测到重定向，直接继续处理
                    if "dm13" in current_url or "missav.com" in current_url:
                        logger.info("检测到URL重定向，继续处理")

                    # 检查页面是否包含电影标题的关键标记
                    check_js = """
                    function checkPageLoaded() {
                        // 检查电影标题元素
                        let title = document.querySelector('h1');
                        if (title && title.textContent.length > 5 && 
                            !title.textContent.includes('MissAV') && 
                            !title.textContent.includes('オンラインで無料')) {
                            return true;
                        }
                        
                        // 检查影片信息区域
                        let infoSection = document.querySelector('.grid-cols-2') || 
                                          document.querySelector('.movie-info-panel');
                        if (infoSection) {
                            return true;
                        }
                        
                        // 检查是否还在Cloudflare页面
                        if (document.querySelector('#challenge-running')) {
                            return 'cloudflare';
                        }
                        
                        return false;
                    }
                    return checkPageLoaded();
                    """

                    # 重试检查页面是否完全加载
                    max_wait_time = 5  # 最多等待5秒
                    start_time = time.time()
                    page_ready = False

                    while time.time() - start_time < max_wait_time:
                        check_result = browser.page.run_js(check_js)
                        if check_result == True:
                            page_ready = True
                            logger.info("页面已完全加载，检测到电影详情内容")
                            break
                        elif check_result == "cloudflare":
                            logger.info("仍在解决Cloudflare挑战，继续等待...")
                        else:
                            logger.info("页面内容尚未准备好，继续等待...")
                        time.sleep(1)

                    # 执行资源阻止脚本
                    browser.page.run_js(
                        "window.stopUnnecessaryLoading && window.stopUnnecessaryLoading();"
                    )

                    # 获取HTML并确保内容与电影ID相关
                    html = browser.html

                    # 简化的HTML验证逻辑
                    if html and len(html) > 5000:  # 只要页面有足够的内容，就尝试解析
                        movie_info = crawler.parse_movie_page(html)

                        if movie_info:
                            # 保存到JSON文件
                            crawler.save_to_json(movie_info, "ja")
                            results[movie_code] = movie_info

                            if movie_info.get("title"):
                                logger.info(
                                    f"成功爬取电影 {movie_code}，标题: {movie_info.get('title')[:30]}"
                                )
                            else:
                                logger.info(f"部分爬取电影 {movie_code}，但缺失标题")
                            break
                        else:
                            logger.warning(
                                f"爬取电影 {movie_code} 失败，尝试重试 {attempt+1}/{max_retries}"
                            )
                    else:
                        logger.warning(
                            f"获取的HTML内容无效，尝试重试 {attempt+1}/{max_retries}"
                        )

                    if attempt < max_retries - 1:
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"爬取电影 {movie_code} 出错: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"将在1秒后重试...")
                        time.sleep(1)
                    else:
                        logger.error(f"已达到最大重试次数，跳过电影 {movie_code}")

            # 电影之间添加短暂延迟，避免请求过于频繁
            if i < len(movie_codes) - 1:
                time.sleep(delay_between_movies)

    except Exception as e:
        logger.error(f"批量爬取过程中发生错误: {e}", exc_info=True)
    finally:
        # 确保浏览器被关闭
        if browser:
            try:
                browser.close()
                logger.info("浏览器已关闭")
            except:
                pass

    return results


def main():
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    logger.remove()
    logger.add(
        logs_dir / "drission_movie_test.log",
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    import argparse

    parser = argparse.ArgumentParser(description="爬取电影详情信息")
    parser.add_argument(
        "movie_codes",
        nargs="*",
        default=["sdjs-146", "rctd-462"],
        help="要爬取的电影ID，可以提供多个",
    )
    parser.add_argument(
        "--headless", action="store_true", help="使用无头模式运行浏览器"
    )
    parser.add_argument(
        "--max-retries", type=int, default=2, help="每个电影的最大重试次数"
    )
    parser.add_argument(
        "--delay", type=float, default=0.5, help="电影之间的延迟时间(秒)"
    )

    args = parser.parse_args()

    # 批量爬取电影信息
    results = batch_crawl_movies(
        args.movie_codes,
        headless=args.headless,
        max_retries=args.max_retries,
        delay_between_movies=args.delay,
    )

    # 显示结果摘要
    logger.info(f"爬取完成，共成功爬取 {len(results)}/{len(args.movie_codes)} 部电影")
    for movie_code, result in results.items():
        logger.info(f"电影 {movie_code} 日语版本爬取完成")
        logger.info(f"  标题: {result.get('title', '未知')}")
        logger.info(f"  女优: {', '.join(result.get('actresses', ['未知']))}")
        logger.info(f"  时长: {result.get('duration_seconds', '未知')} 秒")
        logger.info(f"  数据已保存到: data/{movie_code}_ja.json")


if __name__ == "__main__":
    # Create a folder 'app/utils' and place a dummy 'drission_utils.py' file there,
    # or install the actual library if you have it.
    class DummyBrowser:
        def __init__(self, *args, **kwargs):
            self.html = ""
            self.page = self
            self.wait = self

        def get(self, *args, **kwargs):
            pass

        def quit(self, *args, **kwargs):
            pass

        def close(self, *args, **kwargs):
            pass

        def run_js(self, *args, **kwargs):
            pass

        def load_start(self, *args, **kwargs):
            pass

    # To make the script runnable, we mock the missing import
    # In your actual environment, you would have this module
    if "app" not in sys.modules:
        sys.modules["app"] = type("module")("app")
        sys.modules["app.utils"] = type("module")("app.utils")
        sys.modules["app.utils.drission_utils"] = type("module")(
            "app.utils.drission_utils"
        )
        setattr(
            sys.modules["app.utils.drission_utils"],
            "CloudflareBypassBrowser",
            DummyBrowser,
        )

    main()
