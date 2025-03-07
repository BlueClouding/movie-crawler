# 视频应用原型

这是一个高保真视频应用原型，模拟类似 Netflix 的流媒体平台界面。

## 项目结构

```
pic/
├── assets/
│   └── images/     # 图片资源（使用了在线图片，此目录为预留）
├── css/
│   └── styles.css  # 样式文件
├── js/             # JavaScript 文件（预留）
├── index.html      # 主入口页面
├── home.html       # 首页
├── search.html     # 搜索页
├── categories.html # 分类页
├── details.html    # 详情页
├── player.html     # 播放页
├── profile.html    # 个人资料页
└── mylist.html     # 我的列表页
```

## 页面说明

1. **首页 (home.html)**
   - 展示精选内容、热门影片和推荐内容
   - 包含顶部状态栏和底部导航栏

2. **搜索页 (search.html)**
   - 提供搜索功能
   - 展示热门搜索和最近搜索记录
   - 分类浏览入口

3. **分类页 (categories.html)**
   - 按类型分类展示影片
   - 提供特色分类

4. **详情页 (details.html)**
   - 展示影片详细信息
   - 包括演员阵容和相关推荐

5. **播放页 (player.html)**
   - 视频播放界面
   - 播放控制和剧集选择

6. **个人资料页 (profile.html)**
   - 用户信息展示
   - 账户和应用设置

7. **我的列表页 (mylist.html)**
   - 用户收藏的内容
   - 下载管理

## 技术栈

- HTML5
- CSS3
- Tailwind CSS (CDN)
- Font Awesome (CDN)

## 使用方法

直接打开 `index.html` 文件即可查看所有页面的原型。每个页面都是独立的 HTML 文件，可以单独查看。

## 设计特点

- 模拟 iPhone 15 Pro 屏幕尺寸 (390 x 844px)
- 暗色主题设计
- 响应式布局
- 模拟真实应用的交互元素
