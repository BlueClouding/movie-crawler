# MissAV 批量电影爬虫使用说明

## 功能特点

- ✅ **无头模式运行**：浏览器在后台运行，不显示界面
- ✅ **批量处理**：支持一次性爬取多个电影代码
- ✅ **智能重试**：自动处理网络错误和页面加载问题
- ✅ **详细日志**：实时显示爬取进度和结果统计
- ✅ **数据保存**：自动保存HTML和解析后的JSON数据
- ✅ **Cloudflare绕过**：自动绕过网站的反爬虫保护

## 使用方法

### 1. 交互式批量爬取（推荐）

```bash
python test_ja_only_536VOLA_001.py batch
```

运行后会提示你输入电影代码：
```
=== MissAV 批量电影爬虫 ===
请输入要爬取的电影代码，每行一个，输入空行结束：
电影代码: VOLA-001
电影代码: HZHB-004
电影代码: ABCD-123
电影代码: [直接按回车结束输入]

将要爬取 3 个电影: VOLA-001, HZHB-004, ABCD-123
确认开始爬取？(y/N): y
```

### 2. 示例模式

```bash
python test_ja_only_536VOLA_001.py example
```

这会运行预设的示例电影代码列表。

### 3. 原有测试模式

```bash
python test_ja_only_536VOLA_001.py
```

运行原有的单个电影测试。

## 编程方式使用

你也可以在代码中直接使用 `BatchMovieCrawler` 类：

```python
from test_ja_only_536VOLA_001 import BatchMovieCrawler

# 创建爬虫实例
crawler = BatchMovieCrawler(language="ja")

# 定义要爬取的电影代码列表
movie_codes = [
    "VOLA-001",
    "HZHB-004",
    "ABCD-123",
    # 添加更多电影代码...
]

# 执行批量爬取
results = crawler.crawl_movies(movie_codes)

# 查看结果
print(f"成功: {len(results['success'])} 个")
print(f"失败: {len(results['failed'])} 个")
print(f"成功列表: {results['success']}")
print(f"失败列表: {results['failed']}")
```

## 输出文件

爬取完成后，会在 `test_536VOLA_data/` 目录下生成以下文件：

- `{电影代码}_ja.html` - 原始HTML页面内容
- `{电影代码}_ja_parsed.json` - 解析后的电影信息JSON

例如：
- `VOLA-001_ja.html`
- `VOLA-001_ja_parsed.json`

## 解析的电影信息包括

- 电影标题（日语）
- 封面图片URL
- 发布日期
- 视频时长
- 制作商/厂商
- 系列信息
- 标签列表
- 详细描述
- M3U8流媒体URL（多个分辨率）
- 爬取时间戳

## 注意事项

1. **请求频率**：程序会在每个电影之间自动添加2秒延迟，避免请求过快被网站封禁
2. **网络环境**：确保网络连接稳定，能够正常访问 missav.ai
3. **电影代码格式**：请使用正确的电影代码格式，如 `VOLA-001`、`HZHB-004` 等
4. **存储空间**：每个电影会保存HTML和JSON文件，请确保有足够的磁盘空间
5. **运行时间**：批量爬取需要时间，请耐心等待完成

## 错误处理

程序会自动处理以下错误情况：
- 网络连接超时
- 页面加载失败
- Cloudflare保护触发
- 电影代码不存在
- 页面结构变化

所有错误都会记录在日志中，并在最终统计中显示失败的电影代码。

## 日志输出示例

```
INFO - 开始批量爬取 3 个电影
INFO - [1/3] 正在处理: VOLA-001
INFO - 访问URL: https://missav.ai/ja/VOLA-001
INFO - ✅ VOLA-001 爬取成功
INFO - [2/3] 正在处理: HZHB-004
INFO - 访问URL: https://missav.ai/ja/HZHB-004
ERROR - ❌ HZHB-004 爬取失败：页面加载超时
INFO - [3/3] 正在处理: ABCD-123
INFO - 访问URL: https://missav.ai/ja/ABCD-123
INFO - ✅ ABCD-123 爬取成功

INFO - === 批量爬取完成 ===
INFO - 总数: 3
INFO - 成功: 2
INFO - 失败: 1
INFO - 成功列表: VOLA-001, ABCD-123
INFO - 失败列表: HZHB-004
```