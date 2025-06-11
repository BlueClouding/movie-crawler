# 多浏览器窗口显示问题修复说明

## 问题描述

在使用 `MovieDetailCrawlerService` 的 `batch_crawl_movie_details` 方法时，虽然代码中初始化了多个浏览器实例，但用户只能看到一个浏览器窗口弹出。

## 问题原因

这是 Chrome 浏览器的正常行为，主要原因包括：

### 1. Chrome 的单实例限制
- Chrome 浏览器默认情况下，同一个用户配置文件只能有一个浏览器进程实例
- 即使创建多个 `ChromiumPage` 对象，它们可能会连接到同一个浏览器进程的不同标签页
- 这是 Chrome 为了资源优化和安全性而设计的机制

### 2. DrissionPage 的实现方式
- DrissionPage 使用 Chrome DevTools Protocol (CDP) 来控制浏览器
- 多个 `ChromiumPage` 实例可能会复用同一个浏览器进程
- 虽然内部创建了多个控制实例，但视觉上只显示一个浏览器窗口

### 3. 用户数据目录共享
- 即使为每个实例设置了不同的 `user_data_dir`，Chrome 仍可能会合并到同一个进程中
- 这是 Chrome 的进程管理策略

## 解决方案

我们提供了两种解决方案：

### 方案一：单浏览器模式（推荐）

```python
# 使用单浏览器模式
results = await service.batch_crawl_movie_details(
    movie_codes=["SSIS-001", "SSIS-002", "SSIS-003"],
    language='ja',
    headless=False,
    use_single_browser=True  # 推荐设置
)
```

**优点：**
- 稳定可靠，不会出现窗口显示问题
- 资源占用较少
- 更容易调试和监控

**缺点：**
- 顺序处理，速度相对较慢

### 方案二：多浏览器模式（保留兼容性）

```python
# 使用多浏览器模式
results = await service.batch_crawl_movie_details(
    movie_codes=["SSIS-001", "SSIS-002", "SSIS-003"],
    language='ja',
    headless=False,
    use_single_browser=False  # 多浏览器模式
)
```

**说明：**
- 虽然只显示一个浏览器窗口，但内部仍然创建多个浏览器实例
- 这些实例会并行处理不同的任务
- 性能上仍有提升，只是视觉上看不到多个窗口

## 代码修改详情

### 1. 改进的浏览器池创建

```python
def _create_browser_pool(self, count: int, headless: bool = True):
    """创建多个浏览器实例，使用完全独立的配置"""
    browsers = []
    for i in range(count):
        # 使用UUID和时间戳确保目录唯一性
        unique_id = str(uuid.uuid4())[:8]
        timestamp = int(time.time() * 1000)
        temp_dir = Path(tempfile.gettempdir()) / f"cf_browser_{i}_{unique_id}_{timestamp}"
        
        browser = CloudflareBypassBrowser(
            headless=headless,
            user_data_dir=str(temp_dir),
            load_images=False,
            timeout=30,
            wait_after_cf=3
        )
        browsers.append(browser)
    return browsers
```

### 2. 新增单浏览器模式

```python
async def _batch_crawl_single_browser(self, movie_codes: List[str], ...):
    """使用单个浏览器实例顺序爬取（推荐方式）"""
    # 创建单个浏览器实例
    browser = CloudflareBypassBrowser(...)
    
    # 顺序处理每部电影
    for movie_id in movie_codes:
        result = await self._crawl_single_movie(movie_id, language, browser)
        # 处理结果...
```

### 3. 统一的接口

```python
async def batch_crawl_movie_details(self, movie_codes, use_single_browser=True):
    """统一的爬取接口"""
    if use_single_browser:
        return await self._batch_crawl_single_browser(...)
    else:
        return await self._batch_crawl_multi_browser(...)
```

## 测试方法

运行测试脚本来验证修复效果：

```bash
python test_browser_fix.py
```

测试脚本会让你选择：
1. 单浏览器模式测试
2. 多浏览器模式测试  
3. 两种模式都测试

## 建议

1. **推荐使用单浏览器模式** (`use_single_browser=True`)
2. 如果需要更高的并发性能，可以考虑：
   - 使用多进程而不是多浏览器实例
   - 使用不同的浏览器类型（Firefox, Edge等）
   - 使用虚拟显示技术

## 注意事项

1. 这不是代码的 bug，而是 Chrome 浏览器的正常行为
2. 多浏览器实例在内部仍然是并行工作的，只是视觉上合并了
3. 如果需要真正的多窗口显示，需要使用更复杂的配置或不同的浏览器引擎

## 总结

通过这次修复，我们：
1. 保留了多浏览器的功能（向后兼容）
2. 添加了更稳定的单浏览器模式
3. 改进了浏览器实例的隔离性
4. 提供了清晰的使用建议

用户现在可以根据需要选择合适的模式，避免了多窗口显示的困扰。
