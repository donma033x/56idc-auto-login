# 56idc 自动登录脚本

自动登录 56idc.net 并保持会话活跃。

## ✅ 功能

- **多账号支持** - 一次运行可处理多个账号
- **自动登录** - 会话过期时自动重新登录
- **Cloudflare 验证** - 自动通过 Turnstile 人机验证
- **会话持久化** - 每个账号独立保存登录状态
- **Telegram 通知** - 任务完成后发送结果通知

## 📁 文件结构

```
56idc-auto-login/
├── 56idc_login.py    # 主脚本
├── .env.example      # 配置文件模板
├── .env              # 配置文件 (需自己创建)
├── sessions/         # 会话文件目录 (自动生成)
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install playwright requests
playwright install chromium
```

### 2. 配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置
nano .env
```

配置文件内容:

```env
# 账号配置 (支持多账号，用逗号分隔)
# 格式: 邮箱:密码,邮箱:密码,...
ACCOUNTS=user@example.com:password

# 登录后停留时间 (秒，可选)
STAY_DURATION=10

# Telegram 通知 (可选)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. 运行

```bash
xvfb-run python3 56idc_login.py
```

## ⏰ 定时任务

```bash
# 编辑 crontab
crontab -e

# 添加以下行 (每天上午10点运行)
0 10 * * * cd /home/exedev/56idc-auto-login && xvfb-run python3 56idc_login.py >> /tmp/56idc_login.log 2>&1
```

## ⚠️ 注意事项

- 会话 cookie 可能在几小时到几天内过期
- 如果会话过期，脚本会自动重新登录
- `.env` 文件包含敏感信息，请勿提交到版本控制

## 免责声明

此脚本仅供学习网页自动化技术使用，请遵守 56idc 的服务条款。
