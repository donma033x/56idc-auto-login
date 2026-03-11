# 56idc 自动续期脚本

用于自动登录 56idc.net，保持免费机器活跃状态。

## 当前稳定版特性

- 支持多账号批量登录
- 支持 2FA (TOTP)
- 会话持久化，减少重复登录
- 登录后自动提取机器名并汇总
- 支持 QingLong 场景（环境变量+通知）

## QingLong 使用（推荐）

### 环境变量

- `_56IDC_ACCOUNT`（推荐）或 `56IDC_ACCOUNT`
  - 格式：`邮箱:密码:2FA密钥,邮箱2:密码2`
- `STAY_DURATION`（可选，默认 `10`）
- `TOTP_API_URL`（可选；若不填会回退本地 `pyotp`）

### 依赖

Python 依赖：

```txt
playwright
requests
pyotp
```

系统依赖（容器内）：

```bash
apt-get update && apt-get install -y xvfb xauth
```

### 任务命令示例

```bash
python3 /ql/data/scripts/56idc-renew.py
```

## 本地运行

```bash
export _56IDC_ACCOUNT="your@email.com:password:TOTP_SECRET"
export STAY_DURATION=10
xvfb-run -a python3 56idc-renew.py
```

## 注意

- 不要把账号密码提交到仓库
- 建议通过 QingLong 环境变量管理敏感信息

## 许可

MIT License
