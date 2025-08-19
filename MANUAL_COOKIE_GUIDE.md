# 手动Cookie功能使用指南

## 问题说明

您遇到的401循环问题主要有以下几个原因：

### 1. 使用了示例Cookie
测试脚本中的默认cookie包含占位符（`YOUR_SESSION_HERE`、`YOUR_TOKEN_HERE`），这些是无效的cookie，会导致401未授权错误。

### 2. 自动登录重试机制
当使用自动登录模式时，如果遇到401错误，系统会尝试重新登录并重试，但如果连续失败会达到最大重试次数限制。

## 解决方案

### 方案1：使用有效的手动Cookie（推荐）

1. **获取真实Cookie**：
   - 打开浏览器，访问 https://123av.com/ja
   - 登录您的账户
   - 按F12打开开发者工具
   - 切换到"Network"标签页
   - 刷新页面或点击任意链接
   - 在请求列表中找到任意请求，点击查看详情
   - 在"Request Headers"中找到"Cookie"字段
   - 复制完整的Cookie字符串

2. **更新测试脚本**：
   ```python
   # 将这行：
   MANUAL_COOKIE = "_ga=GA1.1.1641394730.1737617680; locale=ja; session=YOUR_SESSION_HERE; x-token=YOUR_TOKEN_HERE;"
   
   # 替换为您的真实cookie，例如：
   MANUAL_COOKIE = "_ga=GA1.1.1641394730.1737617680; locale=ja; session=abcd1234efgh5678; x-token=your_actual_token_here;"
   ```

3. **运行测试**：
   ```bash
   python test_manual_cookie.py
   ```

### 方案2：使用自动登录模式

如果您不想手动管理cookie，可以让系统自动登录：

```python
from feed_service import FeedService

# 不传入manual_cookie参数，使用自动登录
feed_service = FeedService()
total_pages = feed_service.get_total_feed_pages()
```

## 手动Cookie的优势

1. **更快的响应速度**：跳过自动登录过程
2. **更稳定**：避免Playwright登录可能的失败
3. **更少的资源消耗**：不需要启动浏览器
4. **更好的控制**：您可以控制何时更新cookie

## 注意事项

1. **Cookie有效期**：Cookie会过期，通常几小时到几天不等
2. **安全性**：不要在代码中硬编码敏感的cookie，考虑使用环境变量
3. **错误处理**：当手动cookie失效时，系统不会自动重新登录，需要手动更新

## 示例代码

### 基本使用
```python
from feed_service import FeedService

# 使用手动cookie
manual_cookie = "your_real_cookie_here"
feed_service = FeedService(manual_cookie=manual_cookie)

# 获取页面数据
total_pages = feed_service.get_total_feed_pages()
if total_pages > 0:
    movies = feed_service.get_movies_from_feed_page(1)
    print(f"找到 {len(movies)} 个电影")
else:
    print("Cookie可能已失效，请更新cookie")
```

### 使用环境变量（推荐）
```python
import os
from feed_service import FeedService

# 从环境变量读取cookie
manual_cookie = os.getenv('FEED_COOKIE')
if manual_cookie:
    feed_service = FeedService(manual_cookie=manual_cookie)
else:
    # 回退到自动登录
    feed_service = FeedService()
```

设置环境变量：
```bash
export FEED_COOKIE="your_real_cookie_here"
python your_script.py
```

## 故障排除

### 问题：仍然收到401错误
- **原因**：Cookie已过期或格式不正确
- **解决**：重新从浏览器获取最新的cookie

### 问题：无法获取页面数据
- **原因**：网站结构可能发生变化
- **解决**：检查网站是否正常访问，或联系开发者更新代码

### 问题：自动登录失败
- **原因**：网络问题或登录凭据问题
- **解决**：检查网络连接和登录信息，或使用手动cookie方式