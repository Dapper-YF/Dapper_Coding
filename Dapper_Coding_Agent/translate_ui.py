import re
import codecs
with codecs.open('admin/Web UI.txt', 'r', 'utf-8') as f:
    text = f.read()
translations = {
    "Learning Scout - Dashboard": "Learning Scout - 控制台",
    "Admin Console": "管理控制台",
    "New Report": "新建报告",
    "Home": "首页",
    "Items": "项目库",
    "Feeds": "订阅源",
    "Settings": "设置",
    "Logs": "日志",
    "Search resources...": "搜索资源...",
    "Support": "帮助",
    "Overview": "概览",
    "Monitor your system's extraction performance and health metrics.": "监控系统的抽取性能与健康指标",
    "Run Now": "立即执行",
    "Total Items": "总项目数",
    "from last week": "较上周",
    "New Today": "今日新增",
    "Active Feeds": "活跃订阅源",
    "Success Rate": "成功率",
    "Recent Activity": "近期活动",
    "View All": "查看全部",
    "Filter": "筛选",
    "Item": "项目",
    "Source": "来源",
    "Status": "状态",
    "Time": "时间",
    "Action": "操作",
    "Dashboard": "控制台",
    "Items": "项目",
    "Extracted article on AI trends": "抽取了关于AI趋势的文章",
    "Added new RSS feed": "添加了新的RSS源",
    "Failed to fetch from source": "从源获取失败",
    "Updated system settings": "更新了系统设置",
    "Database backup completed": "数据库备份已完成",
    "Extracted": "成功",
    "System": "系统",
    "Failed": "失败",
    "Just now": "刚刚",
    "2h ago": "2小时前",
    "5h ago": "5小时前",
    "1d ago": "1天前",
    "View": "查看",
    "Retry": "重试",
    "Edit": "编辑"
}
for k, v in translations.items():
    text = text.replace(k, v)
with codecs.open('admin/build/index.html', 'w', 'utf-8') as f:
    f.write(text)
print("Translation applied successfully to index.html")
