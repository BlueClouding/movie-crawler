"""Test module for parsing m3u8 URLs from javplayer."""

import unittest
import os
import json
import logging
from datetime import datetime
import urllib.parse
from bs4 import BeautifulSoup
from src.crawler.utils.http import create_session

class TestM3u8Parser(unittest.TestCase):
    """Test case for m3u8 URL parsing."""
    
    def setUp(self):
        """Set up test case."""
        self.logger = logging.getLogger(__name__)
        self.session = create_session(use_proxy=True)
        
        # 设置测试数据文件路径
        self.test_dir = os.path.join('tests', 'data')
        os.makedirs(self.test_dir, exist_ok=True)
        
    def test_parse_m3u8_url(self):
        """Test parsing m3u8 URL from javplayer."""
        # 1. 调用ajax API获取视频URL
        video_id = 180813
        ajax_url = f'https://123av.com/ja/ajax/v/{video_id}/videos'
        
        response = self.session.get(ajax_url)
        self.assertEqual(response.status_code, 200, "Failed to fetch video URLs")
        
        data = response.json()
        self.assertIn('result', data, "Response should contain 'result'")
        self.assertIn('watch', data['result'], "Result should contain 'watch' list")
        
        # 保存ajax响应
        ajax_file = os.path.join(self.test_dir, f'ajax_response_{video_id}.json')
        with open(ajax_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Saved ajax response to {ajax_file}")
        
        # 获取第一个视频URL
        watch_url = data['result']['watch'][0]['url']
        self.assertTrue(watch_url.startswith('https://javplayer.me/e/'), 
                       "Watch URL should be a javplayer URL")
        
        # 2. 构造带cover的URL
        cover_url = "https://cdn.avfever.net/images/7/d7/savr-238/cover.jpg?t=1730570053"
        encoded_cover = urllib.parse.quote(cover_url)
        player_url = f"{watch_url}?poster={encoded_cover}"
        
        # 3. 获取javplayer页面
        response = self.session.get(player_url)
        self.assertEqual(response.status_code, 200, "Failed to fetch javplayer page")
        
        # 保存javplayer响应
        player_file = os.path.join(self.test_dir, f'player_response_{video_id}.html')
        with open(player_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        self.logger.info(f"Saved player response to {player_file}")
        
        # 4. 解析m3u8 URL
        soup = BeautifulSoup(response.text, 'html.parser')
        player_div = soup.find('div', id='player')
        self.assertIsNotNone(player_div, "Player div should exist")
        
        v_scope = player_div.get('v-scope', '')
        self.assertTrue('stream' in v_scope, "Player div should contain stream URL")
        
        # 解析v-scope属性中的JSON
        if not v_scope:
            self.fail("v-scope attribute not found")
            
        try:
            # 找到第二个参数的JSON开始位置
            video_start = v_scope.find('Video(')
            if video_start == -1:
                self.fail("Video() function not found in v-scope")
                
            # 找到第二个参数的开始位置
            first_comma = v_scope.find(',', video_start)
            if first_comma == -1:
                self.fail("Comma not found after first parameter")
                
            json_start = v_scope.find('{', first_comma)
            if json_start == -1:
                self.fail("Opening brace not found for second parameter")
                
            # 找到JSON的结束位置
            brace_count = 1
            json_end = json_start + 1
            while brace_count > 0 and json_end < len(v_scope):
                if v_scope[json_end] == '{':
                    brace_count += 1
                elif v_scope[json_end] == '}':
                    brace_count -= 1
                json_end += 1
                
            if brace_count > 0:
                self.fail("Closing brace not found for JSON")
                
            # 提取JSON字符串
            json_str = v_scope[json_start:json_end]
            self.logger.info(f"Extracted JSON string: {json_str}")
            
            # 替换HTML实体
            json_str = json_str.replace('&quot;', '"')
            self.logger.info(f"After HTML entity replacement: {json_str}")
            
            # 解析JSON
            try:
                stream_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parse error: {e}")
                self.logger.error(f"Problematic JSON string: {json_str}")
                raise
            
            # 验证stream_data的结构
            self.assertIsInstance(stream_data, dict, "stream_data should be a dictionary")
            self.assertIn('stream', stream_data, "stream_data should contain 'stream' key")
            self.assertIn('vtt', stream_data, "stream_data should contain 'vtt' key")
            
            m3u8_url = stream_data['stream']
            vtt_url = stream_data['vtt']
            
            # 验证URL格式
            self.assertTrue(m3u8_url.startswith('http'), "M3U8 URL should start with http")
            self.assertTrue(m3u8_url.endswith('m3u8'), "M3U8 URL should end with m3u8")
            self.assertTrue(vtt_url.startswith('http'), "VTT URL should start with http")
            self.assertTrue(vtt_url.endswith('vtt'), "VTT URL should end with vtt")
            
            # 保存结果
            result = {
                'video_id': video_id,
                'm3u8_url': m3u8_url,
                'vtt_url': vtt_url,
                'source_url': player_url,  # 添加源URL以便调试
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            result_file = os.path.join(self.test_dir, f'm3u8_info_{video_id}.json')
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved m3u8 info to {result_file}")
            self.logger.info(f"M3U8 URL: {m3u8_url}")
            self.logger.info(f"VTT URL: {vtt_url}")
            
        except Exception as e:
            self.logger.error(f"Error processing v-scope: {str(e)}")
            self.logger.error(f"v-scope content: {v_scope}")
            raise

if __name__ == '__main__':
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    unittest.main()
