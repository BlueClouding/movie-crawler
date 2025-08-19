# 无头浏览器模拟登录使用指南

本项目提供了多种方式使用无头浏览器进行模拟登录并获取cookie。

## 文件说明

### 1. `feed_service.py`
- **完整的登录服务类**: `PlaywrightLoginService`
- **功能**: 包含cookie缓存机制、错误处理、日志记录
- **适用场景**: 集成到其他应用中，需要稳定的登录服务

### 2. `test_login.py`
- **测试脚本**: 全面测试登录功能
- **功能**: 测试登录、缓存、强制刷新、缓存失效等功能
- **适用场景**: 验证登录服务是否正常工作

### 3. `simple_login.py`
- **简化登录脚本**: 快速获取cookie
- **功能**: 最小化的登录实现，易于理解和修改
- **适用场景**: 快速获取cookie，或作为学习示例

## 安装依赖

```bash
# 安装Python包
pip install playwright requests beautifulsoup4

# 安装浏览器
playwright install chromium
```

## 使用方法

### 方法1: 使用简化脚本快速获取cookie

```bash
python simple_login.py
```

获取的cookie会保存到 `cookies.txt` 文件中。

### 方法2: 在代码中导入使用

```python
# 使用简化版本
from simple_login import get_login_cookies

cookies = get_login_cookies()
print(f"获取的cookies: {cookies}")
```

```python
# 使用完整版本（带缓存）
from feed_service import PlaywrightLoginService

login_service = PlaywrightLoginService()
cookies = login_service.get_auth_cookies()
print(f"获取的cookies: {cookies}")
```

### 方法3: 运行完整测试

```bash
python test_login.py
```

## 登录配置

默认登录凭据:
- **用户名**: `12345`
- **密码**: `kongqy`
- **网站**: `https://123av.com`

### 修改登录凭据

#### 在 `simple_login.py` 中:
```python
# 方法1: 修改默认值
service = SimpleLoginService(username="你的用户名", password="你的密码")

# 方法2: 使用便捷函数
cookies = get_login_cookies(username="你的用户名", password="你的密码")
```

#### 在 `feed_service.py` 中:
```python
# 修改 PlaywrightLoginService 类的 __init__ 方法
self.login_username = "你的用户名"
self.login_password = "你的密码"
```

## 功能特性

### 1. 无头浏览器登录
- 使用Playwright控制Chromium浏览器
- 模拟真实用户行为
- 支持JavaScript渲染的页面

### 2. API端点登录
- 直接调用 `/ja/ajax/user/signin` 接口
- 发送JSON格式的登录数据
- 避免复杂的表单操作

### 3. Cookie管理
- 自动提取登录后的cookies
- 格式化为HTTP头格式
- 支持cookie缓存（1小时有效期）

### 4. 错误处理
- 网络超时处理
- 登录失败检测
- 详细的日志记录

## 常见问题

### Q: 登录失败怎么办？
A: 检查以下几点：
1. 网络连接是否正常
2. 登录凭据是否正确
3. 网站是否可以正常访问
4. Playwright浏览器是否正确安装

### Q: 如何查看详细的登录过程？
A: 运行 `test_login.py` 可以看到完整的登录流程和日志。

### Q: Cookie多长时间有效？
A: 
- 网站cookie的有效期由网站决定
- 本地缓存的cookie有效期为1小时
- 可以通过 `force_refresh=True` 强制刷新

### Q: 如何在其他项目中使用？
A: 将 `simple_login.py` 或 `feed_service.py` 复制到你的项目中，然后导入使用。

## 技术细节

### 登录流程
1. 启动无头浏览器（Chromium）
2. 访问网站主页获取基础cookies
3. 通过API端点发送登录请求
4. 等待登录响应和cookies更新
5. 提取并格式化cookies
6. 关闭浏览器

### 异步处理
- 使用 `async/await` 进行异步操作
- 支持在同步环境中调用异步函数
- 使用线程池避免事件循环冲突

### 浏览器配置
- User-Agent: Chrome 139.0.0.0
- 无头模式运行
- 30秒超时设置

## 示例输出

成功登录后的cookie格式:
```
locale=ja; x-token=941abd54a0482a0c42d83f175edd510e; session=nDG89rleGn8h9LGHrluMHoPkgXTikN0Bwx3zA7tO; _ga=GA1.1.448883851.1754897735; _ga_VZGC2QQBZ8=GS2.1.s1754897735$o1$g0$t1754897735$j60$l0$h0
```

关键cookie字段:
- `x-token`: 认证令牌
- `session`: 会话ID
- `locale`: 语言设置
- `_ga`: Google Analytics

## 注意事项

1. **合法使用**: 请确保你有权限访问目标网站
2. **频率限制**: 避免过于频繁的登录请求
3. **隐私保护**: 不要在代码中硬编码敏感信息
4. **依赖管理**: 确保所有依赖包都已正确安装
5. **网络环境**: 某些网络环境可能需要代理设置

## 扩展功能

你可以基于现有代码扩展以下功能:
- 支持代理服务器
- 添加验证码处理
- 支持多账户登录
- 集成到定时任务中
- 添加cookie持久化存储