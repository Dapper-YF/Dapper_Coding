"""
企业微信回调处理 - URL 验证版
"""
import base64
import hashlib
import random
import string
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import xml.etree.ElementTree as ET


class WeChatCallback:
    """企业微信回调处理器"""
    
    def __init__(self, token: str, encoding_aes_key: str):
        """
        Args:
            token: 企业微信后台配置的 Token
            encoding_aes_key: 企业微信后台配置的 EncodingAESKey（43字符）
        """
        self.token = token
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
    
    def verify_signature(self, signature: str, timestamp: str, nonce: str, encrypt: str) -> bool:
        """验证签名"""
        # 组合字符串并排序
        sort_str = ''.join(sorted([self.token, timestamp, nonce, encrypt]))
        # SHA1 加密
        hash_obj = hashlib.sha1(sort_str.encode('utf-8'))
        return hash_obj.hexdigest() == signature
    
    def decrypt(self, encrypt_str: str) -> str:
        """AES 解密"""
        encrypted = base64.b64decode(encrypt_str)
        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv=encrypted[:16])
        decrypted = unpad(cipher.decrypt(encrypted[16:]), 16)
        return decrypted.decode('utf-8')
    
    def decrypt_message(self, encrypt_str: str) -> dict:
        """解密消息为 dict"""
        xml_str = self.decrypt(encrypt_str)
        root = ET.fromstring(xml_str)
        return {child.tag: child.text for child in root}


def verify_url(token: str, encoding_aes_key: str, msg_signature: str, 
               timestamp: str, nonce: str, echostr: str) -> str:
    """
    验证 URL 的回调
    
    Returns:
        解密后的 echostr（需要直接返回，不能是 JSON）
    """
    callback = WeChatCallback(token, encoding_aes_key)
    
    # 解密 echostr
    decrypted_echo = callback.decrypt(echostr)
    
    # 返回原始字符串
    return decrypted_echo


# ===================
# 反馈处理
# ===================

def _handle_feedback(user_id: str, feedback_type: str) -> None:
    """
    处理用户反馈：记录事件 + 调整难度 + 回复确认
    """
    try:
        # 懒加载避免循环导入
        from learning_scout import (
            record_learning_event,
            adjust_difficulty_level,
            get_user_current_topic,
        )
        from weixin_client import get_weixin_client

        # 1. 记录事件
        record_learning_event(user_id, feedback_type)

        # 2. 获取 direction 并调整难度
        topic, level, direction = get_user_current_topic(user_id)
        if direction:
            new_level = adjust_difficulty_level(user_id, direction)
            reply = f"✅ 收到反馈！课程难度已调整为 {new_level}"
        else:
            reply = "✅ 收到反馈！等你开始学习后自动调整难度"

        # 3. 回复用户确认
        try:
            client = get_weixin_client()
            if client:
                client.send_text(reply, to_user=user_id)
        except Exception as reply_err:
            print(f"发送反馈确认消息失败: {reply_err}")

    except Exception as exc:
        print(f"处理用户反馈异常: {exc}")


# ===================
# FastAPI 路由
# ===================

def create_weixin_router(token: str, encoding_aes_key: str):
    """创建企业微信回调路由"""
    from fastapi import APIRouter, Request, Query
    from fastapi.responses import PlainTextResponse
    
    router = APIRouter()
    callback = WeChatCallback(token, encoding_aes_key)
    
    @router.get("/weixin/callback")
    def verify_callback(
        msg_signature: str = Query(...),
        timestamp: str = Query(...),
        nonce: str = Query(...),
        echostr: str = Query(...)
    ):
        """企业微信 URL 验证"""
        try:
            # 解密 echostr 并直接返回（必须是纯文本）
            decrypted_echo = callback.decrypt(echostr)
            return PlainTextResponse(decrypted_echo)
        except Exception as e:
            print(f"Verify failed: {e}")
            return PlainTextResponse("error", status_code=500)
    
    @router.post("/weixin/callback")
    async def handle_callback(request: Request,
        msg_signature: str = Query(...),
        timestamp: str = Query(...),
        nonce: str = Query(...)
    ):
        """处理企业微信推送消息"""
        try:
            body = await request.body()
            # 解析 XML
            root = ET.fromstring(body.decode('utf-8'))
            encrypt = root.find('Encrypt')
            if encrypt is None:
                return PlainTextResponse("success")
            
            encrypt_str = encrypt.text
            
            # 解密
            decrypted_xml = callback.decrypt(encrypt_str)
            
            # 解析解密后的消息
            msg_root = ET.fromstring(decrypted_xml)
            msg_type = msg_root.find('MsgType').text
            from_user = msg_root.find('FromUserName').text
            
            if msg_type == 'event':
                event = msg_root.find('Event').text
                event_key = msg_root.find('EventKey').text if msg_root.find('EventKey') is not None else ''
                
                if event == 'CLICK':
                    print(f"User clicked: {event_key} from {from_user}")
                    positive_keys = {'praise', 'thumb_up', 'positive', 'like', 'good', 'good', '有用', '点赞', '棒'}
                    negative_keys = {'negative', 'thumb_down', 'bad', 'dislike', '差', '没用', '一般', '吐槽'}
                    event_key_lower = event_key.lower()
                    if event_key_lower in positive_keys:
                        _handle_feedback(from_user, "positive_feedback")
                    elif event_key_lower in negative_keys:
                        _handle_feedback(from_user, "negative_feedback")
                
                elif event == 'view':
                    print(f"User viewed: {event_key} from {from_user}")
            
            elif msg_type == 'text':
                msg_content = msg_root.find('Content').text or ""
                print(f"User sent text: {msg_content} from {from_user}")
                positive_keys = {'👍', '好', 'good', '有用', '赞', '很棒', '不错', '喜欢', 'like', 'great'}
                negative_keys = {'👎', '差', '没用', '一般', '不好', 'bad', 'dislike', '不喜欢', '失望'}
                content_stripped = msg_content.strip()
                if content_stripped in positive_keys:
                    _handle_feedback(from_user, "positive_feedback")
                elif content_stripped in negative_keys:
                    _handle_feedback(from_user, "negative_feedback")
            
            return PlainTextResponse("success")
            
        except Exception as e:
            print(f"Handle callback failed: {e}")
            return PlainTextResponse("error", status_code=500)
    
    return router


# ===================
# 独立测试
# ===================

if __name__ == "__main__":
    # 测试用（请替换为实际值）
    TOKEN = "your_token_here"
    AES_KEY = "your_aes_key_here"
    
    print("WeChat Callback module loaded")
    print("To use, add to FastAPI app:")
    print(f"  from weixin_callback import create_weixin_router")
    print(f"  app.include_router(create_weixin_router(TOKEN, AES_KEY))")
