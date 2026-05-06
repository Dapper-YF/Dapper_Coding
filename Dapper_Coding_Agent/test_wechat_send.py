# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, '/opt/Dapper_Coding_Agent')
os.chdir('/opt/Dapper_Coding_Agent')

from dotenv import load_dotenv
load_dotenv('/opt/Dapper_Coding_Agent/.env')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', force=True)

print("Testing WeChat send...", flush=True)
from weixin_client import get_weixin_client

client = get_weixin_client()
print(f"WeChat client: {client}", flush=True)

if client:
    print("Testing send_markdown...", flush=True)
    result = client.send_markdown("**测试消息**\n\n这是一条来自 Learning Scout v2 的测试消息。")
    print(f"Result: {result}", flush=True)
else:
    print("No WeChat client - check env vars", flush=True)
    print(f"WEIXIN_CORP_ID: {os.getenv('WEIXIN_CORP_ID')}", flush=True)
    print(f"WEIXIN_AGENT_ID: {os.getenv('WEIXIN_AGENT_ID')}", flush=True)
    print(f"WEIXIN_CORP_SECRET: {'*' * 10}", flush=True)
