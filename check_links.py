import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

# ===== 配置区域（按需修改）=====
# 你的网盘链接列表
LINKS = [
    {"name": "UC网盘", "url": "https://drive.uc.cn/s/8df281ec6dd54?public=1"},
    {"name": "夸克网盘", "url": "https://pan.quark.cn/s/4a67f42952f3"},
    {"name": "百度网盘", "url": "https://pan.baidu.com/s/1YRSttwYqv3smFsTSql4u5A?pwd=42fy"},
    {"name": "迅雷下载", "url": "https://pan.xunlei.com/s/VONV1pd7HvwnZNMYqmDDTcRQA1?pwd=fnux#"},
    {"name": "梯子工具", "url": "https://www.nfsq.us/#/register?code=Msqx2m4g"},
]

# 邮箱配置（用你的163邮箱）
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465
SENDER_EMAIL = "lxy_3621@163.com"
SENDER_PASSWORD = "QTYb9UdqkMghV6if"  # ⚠️ 稍后告诉你哪里获取
RECEIVER_EMAIL = "lxy_3621@163.com"

# 失效关键词（页面出现这些就算失效）
KEYWORDS = ["失效", "已取消", "不存在", "404", "not found", "过期", "删除"]
# ===== 配置结束 =====

def check_link(name, url):
    """检查单个链接是否有效"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        print(f"正在检查: {name}")
        r = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
        
        # 检查HTTP状态码
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        
        # 检查页面内容是否包含失效关键词
        text = r.text.lower()
        for kw in KEYWORDS:
            if kw in text:
                return False, f"页面包含关键词: {kw}"
        
        return True, "正常"
    except Exception as e:
        return False, f"连接失败: {str(e)}"

def send_email(broken_links):
    """发送邮件通知"""
    subject = f"【宇少数字网】链接失效检测报告 - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    body += "=" * 50 + "\n\n"
    
    if not broken_links:
        body += "✅ 所有链接均正常，无需处理。\n"
    else:
        body += "⚠️ 以下链接可能已失效，请及时处理：\n\n"
        for link in broken_links:
            body += f"🔴 {link['name']}\n"
            body += f"   链接: {link['url']}\n"
            body += f"   原因: {link['reason']}\n\n"
    
    body += "=" * 50 + "\n"
    body += "本邮件由 GitHub Actions 自动发送，请勿回复。"
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("邮件发送成功")
        return True
    except Exception as e:
        print(f"邮件发送失败: {str(e)}")
        return False

def main():
    print("=" * 50)
    print("链接失效检测开始")
    print("=" * 50)
    
    broken_links = []
    
    for link in LINKS:
        is_ok, reason = check_link(link['name'], link['url'])
        if not is_ok:
            broken_links.append({
                'name': link['name'],
                'url': link['url'],
                'reason': reason
            })
        time.sleep(2)  # 礼貌性延迟，避免被封
    
    print("=" * 50)
    if broken_links:
        print(f"发现 {len(broken_links)} 个失效链接")
        send_email(broken_links)
    else:
        print("所有链接正常")
        # 也可以每天发一封“一切正常”的邮件，让你安心
        # send_email([])
    print("检测完成")

if __name__ == "__main__":
    main()