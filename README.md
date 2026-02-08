# RedditMiner

从 Reddit 中挖掘真实产品需求 + 自动化接单工具。

## 两大模式

### Demand Finder（需求挖掘）
- 搜索指定 Subreddit 中的帖子
- 自动分类：产品需求 vs 个人问题 vs 待定
- 可视化统计结果
- 按置信度和需求分数排序

### Task Hunter（自动接单）
- 自动扫描 r/slavelabour、r/forhire、r/hiring、r/freelance
- 技能匹配分类：匹配你技能的 TASK 帖子自动高亮
- 危险/不相关帖子自动过滤（adult content, hack 等）
- 新鲜度排序：优先展示最新帖子，标注"10 min ago - GO NOW!"
- 预算提取：自动从帖子中提取 $金额
- 定时扫描：每 30 分钟自动扫描一次
- Telegram 通知：发现匹配帖子立即推送到手机

## 技术栈

- **后端**: Python FastAPI（Reddit 公开 JSON API，无需凭证）
- **前端**: 原生 HTML/CSS/JavaScript
- **分类**: 基于正则表达式的 NLP 分类器
- **通知**: Telegram Bot API

## 快速开始

### 1. 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件：
```
# Reddit（可选，目前使用公开 JSON API）
REDDIT_CLIENT_ID=你的reddit_app_id
REDDIT_CLIENT_SECRET=你的reddit_app_secret

# Telegram 通知（可选，不配置则不发通知）
TELEGRAM_BOT_TOKEN=你的telegram_bot_token
TELEGRAM_CHAT_ID=你的telegram_chat_id

# 定时扫描
SCAN_INTERVAL_MINUTES=30
AUTO_SCAN_ON_START=false
```

### 2. 获取 Telegram Bot Token（可选）

1. 在 Telegram 搜索 @BotFather
2. 发送 `/newbot`，按指引创建 Bot，获得 Token
3. 给你的 Bot 发一条消息
4. 访问 `https://api.telegram.org/bot<TOKEN>/getUpdates` 获取 `chat_id`

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

后端将在 http://localhost:8000 运行

### 4. 启动前端

```bash
cd frontend
python -m http.server 3000
```

打开 http://localhost:3000

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/scan` | GET | 原始需求扫描 |
| `/api/tasks` | GET | TASK 帖子扫描 |
| `/api/tasks/scan-now` | POST | 手动触发扫描+Telegram通知 |
| `/api/scheduler/start` | POST | 启动定时扫描 |
| `/api/scheduler/stop` | POST | 停止定时扫描 |

### 外部定时调用（n8n / cron）

```bash
# 每 30 分钟调一次，自动扫描+发 Telegram 通知
curl -X POST http://localhost:8000/api/tasks/scan-now
```

## 使用说明

### Demand Finder 模式
1. 输入目标 Subreddit（如 SideProject, smallbusiness）
2. 输入搜索关键词（如 "I wish", "need a tool"）
3. 选择时间范围和数量
4. 点击 Scan

### Task Hunter 模式
1. 切换到 Task Hunter 标签
2. 输入要扫描的 Subreddit（默认: slavelabour, forhire, hiring, freelance）
3. 选择时间范围（建议 Past Day 或 Past Hour）
4. 点击 Hunt Tasks 手动扫描
5. 或点击 **Auto ON** 启动自动扫描（每 30 分钟）
6. 或点击 **Scan & Notify** 立即扫描并发 Telegram 通知

## 分类逻辑

### 需求分类（Demand Finder）
- **Product Need**: 匹配 "I wish", "I'd pay", "someone should build" 等
- **Personal Issue**: 匹配 "help me", "can't log in", "not working" 等
- **Worth Looking**: 高互动但信号不明确的帖子

### 技能匹配（Task Hunter）
- **Skill Match**: 匹配 scrape, automate, bot, chrome extension, python, API 等
- **Maybe**: 只匹配 1 个技能词
- **Danger**: 匹配 adult content, hack, fake account 等危险词
- **Irrelevant**: 不匹配任何技能词

## 后续扩展

- [ ] 接入 LLM 做更精准的分类
- [ ] 导出 CSV 功能
- [ ] 收藏/标记功能
- [ ] 历史趋势追踪
- [ ] 微信通知支持
- [ ] 自动生成回复模板
