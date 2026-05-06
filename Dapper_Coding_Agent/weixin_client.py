"""
企业微信应用客户端
Phase A7 - 企业微信深度集成

功能：
1. 获取 Access Token（自动刷新）
2. 发送应用消息（Text / Markdown / News Card）
3. Click-through 回调处理
4. 群聊消息发送（Phase A8）
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class WeiXinArticle:
    """图文消息文章"""
    title: str
    description: str
    url: str
    picurl: str = ""


class WeiXinClient:
    """企业微信应用客户端"""
    
    # API 基础地址
    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"
    
    def __init__(
        self,
        corp_id: str,
        agent_id: str,
        corp_secret: str,
    ):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.corp_secret = corp_secret
        
        # Access Token 缓存
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
    
    def _get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """获取 Access Token（自动缓存和刷新）"""
        now = time.time()
        
        # 检查缓存是否有效（提前 5 分钟刷新）
        if (
            not force_refresh
            and self._access_token
            and now < self._token_expires_at - 300
        ):
            return self._access_token
        
        # 请求新 Token
        url = f"{self.BASE_URL}/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.corp_secret,
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get("errcode") == 0:
                self._access_token = data["access_token"]
                self._token_expires_at = now + data.get("expires_in", 7200)
                logger.info("WeiXin Access Token 获取成功")
                return self._access_token
            else:
                logger.error("WeiXin Access Token 获取失败: %s", data)
                return None
                
        except Exception as exc:
            logger.error("WeiXin Access Token 请求异常: %s", exc)
            return None
    
    def _send_message(self, msg_type: str, content: Any, to_user: str = "@all") -> bool:
        """发送应用消息（通用方法）"""
        token = self._get_access_token()
        if not token:
            return False
        
        url = f"{self.BASE_URL}/message/send"
        params = {"access_token": token}
        
        payload = {
            "touser": to_user,
            "msgtype": msg_type,
            "agentid": int(self.agent_id),
            msg_type: content,
        }
        
        try:
            resp = requests.post(url, params=params, json=payload, timeout=15)
            data = resp.json()
            
            if data.get("errcode") == 0:
                logger.info("WeiXin 消息发送成功 (to=%s, type=%s)", to_user, msg_type)
                return True
            else:
                logger.error("WeiXin 消息发送失败: %s", data)
                # 如果是 token 过期，强制刷新重试一次
                if data.get("errcode") == 40014:
                    token_new = self._get_access_token(force_refresh=True)
                    if token_new:
                        params["access_token"] = token_new
                        resp = requests.post(url, params=params, json=payload, timeout=15)
                        data = resp.json()
                        if data.get("errcode") == 0:
                            return True
                return False
                
        except Exception as exc:
            logger.error("WeiXin 消息发送异常: %s", exc)
            return False

    def _send_chat_message(self, msg_type: str, content: Any, chat_id: str) -> bool:
        """发送群聊消息（通过 chatid）"""
        token = self._get_access_token()
        if not token:
            return False
        
        url = f"{self.BASE_URL}/chat/send"
        params = {"access_token": token}
        
        payload = {
            "chatid": chat_id,
            "msgtype": msg_type,
            "agentid": int(self.agent_id),
            msg_type: content,
        }
        
        try:
            resp = requests.post(url, params=params, json=payload, timeout=15)
            data = resp.json()
            
            if data.get("errcode") == 0:
                logger.info("WeiXin 群聊消息发送成功 (chatid=%s, type=%s)", chat_id, msg_type)
                return True
            else:
                logger.error("WeiXin 群聊消息发送失败: %s", data)
                return False
                
        except Exception as exc:
            logger.error("WeiXin 群聊消息发送异常: %s", exc)
            return False
    
    def send_text(self, content: str, to_user: str = "@all") -> bool:
        """发送文本消息"""
        return self._send_message("text", {"content": content}, to_user)
    
    def send_markdown(self, content: str, to_user: str = "@all") -> bool:
        """发送 Markdown 消息（仅支持部分 Markdown 语法）"""
        return self._send_message("markdown", {"content": content}, to_user)
    
    def send_news(self, articles: List[WeiXinArticle], to_user: str = "@all") -> bool:
        """发送图文消息（News Card）"""
        article_list = [
            {
                "title": a.title,
                "description": a.description,
                "url": a.url,
                "picurl": a.picurl,
            }
            for a in articles
        ]
        return self._send_message("news", {"articles": article_list}, to_user)
    
    def send_textcard(self, title: str, description: str, url: str, to_user: str = "@all") -> bool:
        """发送文本卡片消息（最接近 Card 的方式）"""
        content = {
            "title": title,
            "description": description,
            "url": url,
            "btntxt": "详情",
        }
        return self._send_message("textcard", content, to_user)

    # === Phase A8: 群聊消息发送 ===
    def send_text_to_chat(self, content: str, chat_id: str) -> bool:
        """发送文本消息到群聊"""
        return self._send_chat_message("text", {"content": content}, chat_id)
    
    def send_markdown_to_chat(self, content: str, chat_id: str) -> bool:
        """发送 Markdown 消息到群聊"""
        return self._send_chat_message("markdown", {"content": content}, chat_id)


def get_weixin_client() -> Optional[WeiXinClient]:
    """从环境变量创建企业微信客户端
    
    注意：环境变量需要在调用前通过 app.startup 或主模块加载 .env
    """
    import os
    
    corp_id = os.getenv("WEIXIN_CORP_ID", "")
    agent_id = os.getenv("WEIXIN_AGENT_ID", "")
    corp_secret = os.getenv("WEIXIN_CORP_SECRET", "")
    
    if not all([corp_id, agent_id, corp_secret]):
        logger.warning("企业微信配置不完整，跳过应用推送")
        return None
    
    return WeiXinClient(corp_id, agent_id, corp_secret)


# ===================
# Click 回调处理
# ===================

def parse_weixin_callback(request_body: dict) -> Optional[dict]:
    """解析企业微信回调事件"""
    try:
        msg_type = request_body.get("MsgType", "")
        
        if msg_type == "event":
            event = request_body.get("Event", "")
            if event == "click":
                return {
                    "type": "click",
                    "event_key": request_body.get("EventKey", ""),
                    "from_user": request_body.get("FromUserName", ""),
                }
        elif msg_type == "text":
            return {
                "type": "text",
                "content": request_body.get("Content", ""),
                "from_user": request_body.get("FromUserName", ""),
            }
        
        return None
        
    except Exception as exc:
        logger.error("解析企业微信回调失败: %s", exc)
        return None
