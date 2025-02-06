# 123AV 分类数据爬虫

## 项目简介
本项目用于爬取123av.com网站的分类数据，包括分类名称、URL和视频数量等信息。

## 功能特性
- 自动处理日语编码
- 数据保存为CSV格式
- 支持随机延迟防止被封禁

## 环境要求
- Python 3.7+
- 依赖包：requests, beautifulsoup4, lxml, pandas

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法
1. 激活虚拟环境
```bash
source venv/bin/activate
```

2. 运行爬虫
```bash
python main.py
```

3. 查看结果
爬取的数据将保存在data/目录下，文件名为categories_时间戳.csv

## 注意事项
- 请遵守目标网站的robots.txt协议
- 适当调整请求频率，避免对服务器造成过大压力
