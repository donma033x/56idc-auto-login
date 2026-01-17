#!/usr/bin/env python3
"""
56idc 自动登录续期脚本

cron: 0 8 * * 1
new Env('56idc-renew')

功能:
1. 支持多账号
2. 自动通过 Cloudflare Turnstile 验证
3. 自动登录 56idc.net
4. 保存会话供下次使用

环境变量:
    ACCOUNTS_56IDC: 账号配置，格式: 邮箱:密码:2FA密钥,邮箱:密码 (2FA密钥可选)
    STAY_DURATION: 停留时间(秒)，默认10
    TOTP_API_URL: TOTP API地址
    TELEGRAM_BOT_TOKEN: Telegram机器人Token (可选)
    TELEGRAM_CHAT_ID: Telegram聊天ID (可选)
"""

import os
import asyncio
import json
import requests
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# ==================== 从环境变量加载配置 ====================
ACCOUNTS_STR = os.environ.get('ACCOUNTS_56IDC', '')
STAY_DURATION = int(os.environ.get('STAY_DURATION', '10'))
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
TOTP_API_URL = os.environ.get('TOTP_API_URL', '')

LOGIN_URL = "https://56idc.net/login.php"
DASHBOARD_URL = "https://56idc.net/clientarea.php"
SESSION_DIR = Path(__file__).parent / "sessions"

def parse_accounts(accounts_str: str) -> list:
    """解析账号配置，格式: 邮箱:密码:2FA密钥 (2FA密钥可选)"""
    accounts = []
    if not accounts_str:
        return accounts
    for item in accounts_str.split(','):
        item = item.strip()
        if ':' in item:
            parts = item.split(':')
            if len(parts) >= 2:
                email = parts[0].strip()
                password = parts[1].strip()
                totp_secret = parts[2].strip() if len(parts) >= 3 else ''
                accounts.append({
                    'email': email,
                    'password': password,
                    'totp_secret': totp_secret
                })
    return accounts

def get_session_file(email: str) -> Path:
    SESSION_DIR.mkdir(exist_ok=True)
    safe_name = email.replace('@', '_at_').replace('.', '_')
    return SESSION_DIR / f"{safe_name}.json"


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
    
    def send(self, message: str) -> bool:
        if not self.enabled:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except:
            return False


class Logger:
    @staticmethod
    def log(step: str, msg: str, status: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbols = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "WAIT": "⏳"}
        symbol = symbols.get(status, "•")
        print(f"[{timestamp}] [{step}] {symbol} {msg}")


def get_totp_code(secret: str) -> str:
    """从 TOTP API 获取验证码"""
    if not TOTP_API_URL or not secret:
        return ''
    try:
        response = requests.get(f"{TOTP_API_URL}/totp/{secret}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('code', '')
    except Exception as e:
        Logger.log("TOTP", f"获取TOTP失败: {e}", "ERROR")
    return ''


async def wait_for_turnstile(page, timeout: int = 60) -> bool:
    """等待 Turnstile 验证完成"""
    Logger.log("Turnstile", "等待 Cloudflare 验证...", "WAIT")
    
    try:
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            # 检查是否有 turnstile iframe
            frames = page.frames
            for frame in frames:
                if 'turnstile' in frame.url or 'challenges.cloudflare.com' in frame.url:
                    # 尝试点击验证框
                    try:
                        checkbox = await frame.query_selector('input[type="checkbox"]')
                        if checkbox:
                            await checkbox.click()
                            Logger.log("Turnstile", "点击验证框", "INFO")
                    except:
                        pass
            
            # 检查隐藏的 turnstile response
            try:
                response = await page.evaluate('''() => {
                    const input = document.querySelector('input[name="cf-turnstile-response"]');
                    return input ? input.value : '';
                }''')
                if response and len(response) > 10:
                    Logger.log("Turnstile", "验证通过", "OK")
                    return True
            except:
                pass
            
            await asyncio.sleep(1)
        
        Logger.log("Turnstile", "验证超时", "ERROR")
        return False
    except Exception as e:
        Logger.log("Turnstile", f"验证异常: {e}", "ERROR")
        return False


async def login_account(playwright, account: dict, notifier: TelegramNotifier) -> bool:
    """登录单个账号"""
    email = account['email']
    password = account['password']
    totp_secret = account.get('totp_secret', '')
    
    Logger.log("Login", f"开始登录: {email}", "INFO")
    
    browser = None
    try:
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # 加载已保存的 session
        session_file = get_session_file(email)
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                Logger.log("Session", "加载已保存的会话", "OK")
            except:
                pass
        
        # 访问登录页
        Logger.log("Navigate", f"访问 {LOGIN_URL}", "INFO")
        await page.goto(LOGIN_URL, wait_until='networkidle', timeout=60000)
        
        # 检查是否已登录
        if 'clientarea.php' in page.url:
            Logger.log("Login", "已登录，无需重新登录", "OK")
            # 保存 session
            cookies = await context.cookies()
            with open(session_file, 'w') as f:
                json.dump(cookies, f)
            return True
        
        # 等待 Turnstile 验证
        await wait_for_turnstile(page)
        
        # 填写登录表单
        Logger.log("Form", "填写登录表单", "INFO")
        await page.fill('input[name="username"]', email)
        await page.fill('input[name="password"]', password)
        
        # 点击登录按钮
        await page.click('input[type="submit"], button[type="submit"]')
        
        # 等待页面响应
        await asyncio.sleep(3)
        
        # 检查是否需要2FA
        if totp_secret:
            try:
                totp_input = await page.query_selector('input[name="code"], input[name="twoFactorCode"]')
                if totp_input:
                    Logger.log("2FA", "需要2FA验证", "INFO")
                    totp_code = get_totp_code(totp_secret)
                    if totp_code:
                        await totp_input.fill(totp_code)
                        await page.click('input[type="submit"], button[type="submit"]')
                        await asyncio.sleep(3)
                        Logger.log("2FA", "已提交2FA验证码", "OK")
            except:
                pass
        
        # 检查登录结果
        await page.wait_for_load_state('networkidle', timeout=30000)
        
        if 'clientarea.php' in page.url or 'dashboard' in page.url.lower():
            Logger.log("Login", f"登录成功: {email}", "OK")
            
            # 保存 session
            cookies = await context.cookies()
            with open(session_file, 'w') as f:
                json.dump(cookies, f)
            
            # 停留一段时间
            Logger.log("Stay", f"停留 {STAY_DURATION} 秒", "WAIT")
            await asyncio.sleep(STAY_DURATION)
            
            notifier.send(f"✅ 56idc 登录成功\n账号: {email}")
            return True
        else:
            Logger.log("Login", f"登录失败: {email}", "ERROR")
            notifier.send(f"❌ 56idc 登录失败\n账号: {email}")
            return False
            
    except Exception as e:
        Logger.log("Error", f"登录异常: {e}", "ERROR")
        notifier.send(f"❌ 56idc 登录异常\n账号: {email}\n错误: {str(e)}")
        return False
    finally:
        if browser:
            await browser.close()


async def main():
    """主函数"""
    Logger.log("Start", "56idc 自动登录脚本启动", "INFO")
    
    # 检查环境变量
    if not ACCOUNTS_STR:
        Logger.log("Config", "错误: 未设置 ACCOUNTS_56IDC 环境变量", "ERROR")
        return
    
    accounts = parse_accounts(ACCOUNTS_STR)
    if not accounts:
        Logger.log("Config", "错误: 无有效账号配置", "ERROR")
        return
    
    Logger.log("Config", f"共 {len(accounts)} 个账号", "INFO")
    
    notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    
    success_count = 0
    fail_count = 0
    
    async with async_playwright() as playwright:
        for i, account in enumerate(accounts, 1):
            Logger.log("Progress", f"处理第 {i}/{len(accounts)} 个账号", "INFO")
            
            if await login_account(playwright, account, notifier):
                success_count += 1
            else:
                fail_count += 1
            
            # 账号间间隔
            if i < len(accounts):
                Logger.log("Wait", "等待 5 秒后处理下一个账号", "WAIT")
                await asyncio.sleep(5)
    
    # 汇总
    Logger.log("Summary", f"完成: 成功 {success_count}, 失败 {fail_count}", "INFO")
    
    if success_count > 0 or fail_count > 0:
        notifier.send(f"📊 56idc 登录汇总\n成功: {success_count}\n失败: {fail_count}")


if __name__ == '__main__':
    asyncio.run(main())
