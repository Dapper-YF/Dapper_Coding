# REVIEW REPORT
BLOCK
---
weixin_callback.py decrypt function review
---
ISSUE 1 CRITICAL: unpad(decrypted, 32) wrong
AES block size is always 16 bytes
must be unpad(decrypted, 16)
---
ISSUE 2 CRITICAL: no msg extraction
returns entire msgpk instead of extracting msg field
msg_len must be read from bytes 16-20
---
ISSUE 3 WARNING: verify_url returns garbage to WeChat
---
ISSUE 4 WARNING: ET.fromstring(msgpk) fails
msgpk is not pure XML
---
Correct fix:
unpad(decrypted, 16) not 32
struct.unpack to get msg_len
return decrypted[20:20+msg_len]
---