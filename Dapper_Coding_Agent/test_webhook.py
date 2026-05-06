# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
os.chdir('/opt/Dapper_Coding_Agent')

from dotenv import load_dotenv
load_dotenv('/opt/Dapper_Coding_Agent/.env')

import requests
url = os.getenv('WEIXIN_WEBHOOK_URL')
print(f"Webhook URL: {url}")

data = {
    'msgtype': 'text',
    'text': {
        'content': '🔔 Learning Scout 机器人已连接！\n\n这是一条测试消息，明天 08:10 你将收到 AI 简报推送。'
    }
}
resp = requests.post(url, json=data, timeout=10)
print(f'Status: {resp.status_code}')
print(f'Response: {resp.text}')
