# TASK_CURRENT.md

## Context
- Cloud server: `root@8.162.10.45`, code at `/opt/Dapper_Coding_Agent/dapper_coding_agent.py`
- 企业微信回调: `POST/GET https://8.162.10.45:8000/weixin/callback`
- Working directory (local): `C:\Users\Dapper\.openclaw\workspace-architect`

## Goal
修复企业微信回调解密 bug，使 "我想学AI" 等消息能正常被 LearningAgent 处理并回复用户。

## Constraints
- 不修改任务范围外的代码
- 遵循现有代码风格
- 每次修改后验证语法

## Problem Statement

企业微信回调解密函数 `weixin_decrypt_echo()` 有两个 bug：

**Bug 1: 自定义的 PKCS7 padding 校验不可靠**
```python
# 原代码：读取最后一个字节作为 padding length
pad_len = decrypted[-1]
if pad_len > 16 or pad_len == 0:
    raise ValueError("Invalid padding length: %d" % pad_len)
# 问题：文字内容的最后一个字节可能 > 16，被误判为无效 padding
# 修复：用 Crypto.Util.Padding.unpad() 标准函数
```

**Bug 2: msg_len 偏移错误**
```python
# 原代码：从字节 0 读取 msg_len（错误）
msg_len = struct.unpack(">I", decrypted[0:4])[0]
msg = decrypted[4:4+msg_len]  # 错误：前16字节是 random，msg 从字节 20 开始

# 修复：
msg_len = struct.unpack(">I", decrypted[16:20])[0]
msg = decrypted[20:20+msg_len]
```

## Known Fixes Applied

1. Bug 1 已修复：替换为 `from Crypto.Util.Padding import unpad; decrypted = unpad(decrypted, 16)`
2. Bug 2 已修复：`msg_len` 偏移 16→20，`msg` 偏移 4→20

## Current Symptom
- "你好" → 解密成功 ✅ → LearningAgent ✅ → 回复用户 ✅
- "我想学AI" → `Invalid padding length: 28` ❌ → 解密失败，不回复

## Steps
1. [待Supervisor审查] 检查 `weixin_decrypt_echo()` 函数当前代码是否正确修复
2. [待Supervisor审查] 验证修复后 "我想学AI" 能否解密成功
3. [如需] 根据 Supervisor 反馈修复
4. [完成后] 重启服务并通知用户测试
