---
name: "job-crawler"
description: "Crawls job postings from Liepin, Boss Zhipin, and Zhaopin. Invoke when user requests multi-site recruitment data collection or automated job search."
level: "advanced"
version: "1.0.0"
tags:
  - "Playwright（浏览器自动化）"
  - "pandas（数据处理）"
  - "Excel（表格输出）"
  - "Strategy Pattern（策略模式）"
  - "Session Isolation（会话隔离）"
  - "Captcha（验证码处理）"
keywords:
  - 招聘
  - 职位
  - 岗位
  - 爬虫
  - 数据采集
---

# 职位信息通用爬取器（Job Crawler）

该技能用于从主流招聘网站（猎聘、Boss直聘、智联招聘）批量抓取职位信息，并保存为 Excel（电子表格）文件。底层实现基于 Playwright（浏览器自动化）与 pandas（数据处理），调用本地脚本 [crawl_jobs.py](file:///Users/chenyufan/Desktop/工作实习/2026.01%20新希望/2026.0204%20爬虫/crawl_jobs.py)。

## 适用场景（When to Invoke）
- 需要跨平台（猎聘/Boss直聘/智联招聘）抓取招聘数据时调用。
- 用户希望指定关键词、会话隔离，并自动保存为 Excel 时调用。
- 需要浏览器自动化（Playwright）且可能涉及验证码处理时调用。

## 关键技能点（Key Skills）
- 多站点策略模式（Strategy Pattern）：站点逻辑解耦、易扩展。
- 浏览器自动化（Playwright）：持久化上下文、无头/有头切换。
- 会话隔离（Session Isolation）：避免“顶号”、持久登录状态。
- 验证码处理（Captcha）：有头模式下人工介入与继续。
- 数据去重与排序（pandas）：按公司/链接去重，按薪资排序。
- 文件输出（Excel）：生成 `job_info.xlsx` 或自定义文件名。

## 前置条件（Prerequisites）
- 安装 Python 3.8+ 与基础命令行环境。
- 首次使用运行安装脚本以准备依赖与浏览器驱动。
- 具备对应网站账号以便登录查看更多职位。

## 使用步骤（Usage）

```bash
# 第一次使用：一键初始化环境
./setup.sh
```

### 基础用法（猎聘）

```bash
./run.sh --keywords "产品经理"
```

### Boss直聘

```bash
./run.sh --site boss --keywords "数据分析"
```

### 智联招聘

```bash
./run.sh --site zhaopin --keywords "Java 开发"
```

### 进阶用法

**With Session ID (Recommended for multi-agent/multi-user):**

```bash
./run.sh --site liepin --session user123 --keywords "Python"
```

**Headless Mode (Automated):**

```bash
./run.sh --headless --keywords "前端"
```

## 参数说明（Parameters）

| Argument | Description | Default |
|----------|-------------|---------|
| `--site` | 目标站点（`liepin`、`boss`、`zhaopin`） | `liepin` |
| `--keywords` | 搜索关键词（逗号分隔或引号包裹的空格分隔） | 交互输入 |
| `--session` | 会话 ID（隔离用户数据与登录态） | `default` |
| `--headless` | 无头模式（不显示浏览器窗口） | `False`（默认有头） |
| `--output` | 输出文件名（Excel） | `job_info.xlsx` |
| `--browser-path` | 浏览器可执行文件路径 | 使用 Playwright 内置 |

## 输出结果（Outputs）

- **Data File**: `job_info.xlsx`（或自定义文件名）
- **User Data**: `user_data/<session_id>/`（保存登录态与 Cookie）

## 工作流说明（Workflow）
- 启动浏览器并创建持久化上下文（避免频繁登录）。
- 打开站点首页并执行关键词搜索。
- 提示用户完成登录/验证码与筛选后，按 Enter 开始。
- 抓取当前列表页职位链接，逐一打开详情页提取信息。
- 自动去重与排序，实时写入 Excel 文件。
- 自动翻页直至达到页数上限或无更多数据。

## 错误处理与反爬（Error Handling）
- 验证码出现：使用有头模式（Headed）手动完成后继续。
- 列表为空：自动刷新一次页面并重试；仍为空则尝试翻页。
- 站点变更：若选择器失效，请反馈具体站点以更新策略。
- 会话冲突：使用 `--session` 区分不同任务/用户，避免“顶号”。

## 依赖（Dependencies）

Ensure the following packages are installed:
- `playwright`
- `pandas`
- `openpyxl`

安装方式：

```bash
./setup.sh
```
