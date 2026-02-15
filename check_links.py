import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import time
import os
import re

# ===== 配置区域 =====
LINKS = [
    {"name": "UC网盘", "url": "https://drive.uc.cn/s/8df281ec6dd54?public=1"},
    {"name": "夸克网盘", "url": "https://pan.quark.cn/s/4a67f42952f3"},
    {"name": "百度网盘", "url": "https://pan.baidu.com/s/1YRSttwYqv3smFsTSql4u5A?pwd=42fy"},
    {"name": "迅雷下载", "url": "https://pan.xunlei.com/s/VONV1pd7HvwnZNMYqmDDTcRQA1?pwd=fnux#"},
    {"name": "梯子工具", "url": "https://www.nfsq.us/#/register?code=Msqx2m4g"},
]

# 邮箱配置
SMTP_SERVER = "smtp.163.com"
SMTP_PORT = 465
SENDER_EMAIL = "lxy_3621@163.com"
SENDER_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'QTYb9UdqkMghV6if')
RECEIVER_EMAIL = "lxy_3621@163.com"

# 失效关键词
KEYWORDS = ["失效", "已取消", "不存在", "404", "not found", "过期", "删除"]

# 白名单域名（这些网站即使报错也可能是反爬，需要人工确认）
WHITELIST_DOMAINS = ["nfsq.us", "xunlei.com"]

# 状态码白名单（这些状态码不直接判失效）
WHITELIST_CODES = [403, 429, 503]
# ===== 配置结束 =====

def check_link(name, url):
    """
    检查链接状态，返回（等级、原因）
    等级：'good'（正常）、'suspect'（可疑）、'bad'（失效）
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        print(f"正在检查: {name}")

# 特殊处理夸克
if "quark.cn" in url:
    return check_quark_special(name, url, headers)

# 特殊处理迅雷
if "xunlei.com" in url:
    return check_xunlei_special(name, url, headers)

# 判断是否在白名单
is_whitelist = False
for domain in WHITELIST_DOMAINS:
    if domain in url and domain != "xunlei.com":  # 迅雷已单独处理
        is_whitelist = True
        break
        
        # 重试机制
        for i in range(3):
            try:
                r = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
                break
            except Exception as e:
                if i == 2:  # 最后一次重试失败
                    if is_whitelist:
                        return 'suspect', f"白名单域名连接失败（可能反爬）: {str(e)}"
                    else:
                        return 'bad', f"连接失败: {str(e)}"
                time.sleep(2)
        
        # 检查状态码
        if r.status_code == 200:
            # 检查页面内容
            text = r.text.lower()
            for kw in KEYWORDS:
                if kw in text:
                    return 'bad', f"页面包含失效关键词: {kw}"
            return 'good', "正常"
        
        elif r.status_code in WHITELIST_CODES or is_whitelist:
            return 'suspect', f"返回{r.status_code}，可能反爬，需人工确认"
        else:
            return 'bad', f"HTTP {r.status_code}"
            
    except Exception as e:
        if is_whitelist:
            return 'suspect', f"白名单域名异常: {str(e)}"
        else:
            return 'bad', f"异常: {str(e)}"

def check_xunlei_special(name, url, headers):
    """专门处理迅雷链接"""
    try:
        # 尝试用浏览器一样的头信息
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 重试3次
        for i in range(3):
            try:
                r = requests.get(url, timeout=20, headers=headers, allow_redirects=True)
                # 迅雷经常返回非200但实际可用，所以我们只看页面内容
                text = r.text.lower()
                
                # 真正的失效关键词（迅雷特有的）
                xunlei_dead_keywords = ["失效", "已取消", "不存在", "过期", "删除", "文件已删除"]
                
                for kw in xunlei_dead_keywords:
                    if kw in text:
                        return 'bad', f"页面包含失效关键词: {kw}"
                
                # 如果能走到这里，说明大概率可用
                return 'good', "正常（忽略状态码）"
                
            except Exception as e:
                if i == 2:
                    return 'suspect', f"迅雷特殊处理仍失败: {str(e)}"
                time.sleep(3)
                
    except Exception as e:
        return 'suspect', f"迅雷检测异常: {str(e)}"

def send_email(results):
    """发送邮件通知（区分等级）"""
    good = [r for r in results if r['level'] == 'good']
    suspect = [r for r in results if r['level'] == 'suspect']
    bad = [r for r in results if r['level'] == 'bad']
    
    subject = f"【宇少数字网】链接检测报告 - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    body += "=" * 50 + "\n\n"
    
    if bad:
        body += "🔴 以下链接确定失效，请尽快处理：\n\n"
        for link in bad:
            body += f"  • {link['name']}: {link['reason']}\n"
        body += "\n"
    
    if suspect:
        body += "🟡 以下链接状态可疑，建议人工确认：\n\n"
        for link in suspect:
            body += f"  • {link['name']}: {link['reason']}\n"
        body += "\n"
    
    if good:
        body += f"🟢 正常链接 ({len(good)} 个)\n"
    
    if not bad and not suspect:
        body += "✅ 所有链接均正常。\n"
    
    body += "\n" + "=" * 50 + "\n"
    body += "本邮件由 GitHub Actions 自动发送。"
    
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
    print("链接失效检测开始（三档机制）")
    print("=" * 50)
    
    results = []
    for link in LINKS:
        level, reason = check_link(link['name'], link['url'])
        results.append({
            'name': link['name'],
            'url': link['url'],
            'level': level,
            'reason': reason
        })
        print(f"{link['name']}: {level} - {reason}")
        time.sleep(2)
    
    print("=" * 50)
    
    # 只要有可疑或失效就发邮件
    if any(r['level'] in ['suspect', 'bad'] for r in results):
        send_email(results)
        print("邮件已发送")
    else:
        print("所有链接正常，无需邮件")
    
    print("检测完成")

if __name__ == "__main__":
    main()