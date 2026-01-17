# 56idc 自动续期脚本

用于自动登录 56idc.net 以保持账号活跃状态。

## 功能

- 支持多账号批量登录
- 自动处理 Cloudflare Turnstile 验证
- 支持 2FA (TOTP) 验证
- 会话持久化，减少重复登录
- Telegram 通知支持

## 青龙面板使用

### 1. 添加订阅

在青龙面板的「订阅管理」中添加：

- **名称**: 56idc-renew
- **链接**: `https://github.com/donma033x/56idc-renew.git`
- **分支**: main
- **定时规则**: `0 8 * * *`

### 2. 配置环境变量

在青龙面板的「环境变量」中添加：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `ACCOUNTS_56IDC` | 账号配置 | `邮箱:密码:2FA密钥,邮箱2:密码2` |
| `STAY_DURATION` | 停留时间(秒) | `10` |
| `TOTP_API_URL` | TOTP API地址 | `https://tools.example.com` |
| `TELEGRAM_BOT_TOKEN` | TG机器人Token | (可选) |
| `TELEGRAM_CHAT_ID` | TG聊天ID | (可选) |

**账号格式说明**:
- 无2FA: `邮箱:密码`
- 有2FA: `邮箱:密码:TOTP密钥`
- 多账号用逗号分隔

### 3. 安装依赖

在青龙面板的「依赖管理」→「Python3」中安装：

```
playwright
requests
```

### 4. 系统依赖

需要在容器中安装 xvfb (用于无头浏览器):

```bash
apt-get update && apt-get install -y xvfb xauth
```

### 5. 定时任务

任务会自动创建，默认命令:
```
task donma033x_56idc-renew_main/56idc-renew.py
```

如需使用 xvfb-run，可在青龙「配置文件」的 `config.sh` 中设置 `task_before`。

## 手动运行

```bash
# 设置环境变量
export ACCOUNTS_56IDC="your@email.com:password:TOTP_SECRET"
export STAY_DURATION=10
export TOTP_API_URL="https://your-totp-api.com"

# 运行 (需要 xvfb)
xvfb-run python3 56idc-renew.py
```

## 许可

MIT License
