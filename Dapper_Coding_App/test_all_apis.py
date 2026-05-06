# -*- coding: utf-8 -*-
"""
Learning Scout APP API 自动化测试
"""
import urllib.request
import urllib.error
import json
import time
import sys

BASE = "http://8.162.10.45"
TOKEN = "dev_token_mvp"

def headers():
    return {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=headers(), method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=30)
        return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except:
            return e.code, e.read().decode("utf-8")
    except Exception as e:
        return "ERROR", str(e)

results = []

def test(name, fn):
    print("\n" + "=" * 50)
    print("  " + name)
    print("=" * 50)
    try:
        result = fn()
        status = "PASS" if result is True else ("WARN: " + str(result))
        print("\n  [RESULT] " + status)
        results.append((name, status))
    except Exception as e:
        print("\n  [RESULT] EXCEPTION: " + str(e))
        results.append((name, "EXCEPTION: " + str(e)))

print("\n" + "#" * 60)
print("# Learning Scout APP API Testing")
print("# Time: " + time.strftime("%Y-%m-%d %H:%M:%S"))
print("#" * 60)

# 1. Health
def t_health():
    code, body = req("GET", "/api/conversations")
    if code == 200:
        print("  API Server: OK (200)")
        return True
    print("  API Server: FAIL code=" + str(code))
    return False

test("1. API Server Health", t_health)

# 2. Conversations
def t_conversations():
    code, body = req("GET", "/api/conversations")
    print("  GET /api/conversations -> " + str(code))
    if code == 200:
        print("  Returned: " + str(len(body)) + " sessions")
        for c in body[:3]:
            print("    - id=" + str(c.get("id")) + " messages=" + str(c.get("message_count")))
        return True
    return False

test("2. Conversation List", t_conversations)

# 3. Chat SSE
def t_chat():
    print("  POST /api/chat (streaming test)")
    body = json.dumps({"message": "What is quantum entanglement?", "conversation_id": "test_001"}).encode()
    r = urllib.request.Request(
        BASE + "/api/chat",
        data=body,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"},
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(r, timeout=60)
        print("  HTTP Status: " + str(resp.status))
        full_content = ""
        chunks = 0
        while True:
            line = resp.readline().decode("utf-8")
            if not line:
                break
            if line.startswith("data: "):
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                    delta = event.get("delta", "")
                    if delta:
                        full_content += delta
                        chunks += 1
                except:
                    pass
        resp.close()
        print("  Received chunks: " + str(chunks))
        print("  Response length: " + str(len(full_content)) + " chars")
        print("  Response preview: " + full_content[:150].replace("\n", " "))
        return True if (chunks > 0 and len(full_content) > 0) else "No content"
    except Exception as e:
        return "Exception: " + str(e)

test("3. Chat SSE Streaming", t_chat)

# 4. Graph
def t_graph():
    _, convs = req("GET", "/api/conversations")
    conv_id = str(convs[0]["id"]) if convs else "1"
    print("  Using conversation_id: " + conv_id)
    code, body = req("POST", "/api/graph/generate", {"conversation_id": conv_id})
    print("  POST /api/graph/generate -> " + str(code))
    if code == 200:
        nodes = body.get("nodes", [])
        edges = body.get("edges", [])
        print("  Nodes: " + str(len(nodes)))
        for n in nodes[:4]:
            print("    - id=" + str(n.get("id")) + " label=" + str(n.get("label")) + " x=" + str(n.get("x")) + " y=" + str(n.get("y")) + " mastery=" + str(n.get("mastery")) + " color=" + str(n.get("color")))
        print("  Edges: " + str(len(edges)))
        if len(nodes) > 0 and "x" in nodes[0]:
            print("  x/y/mastery/color fields: PRESENT")
            return True
        return "Missing fields"
    return False

test("4. Knowledge Graph Generate", t_graph)

# 5. Lesson Recommend
def t_lesson():
    code, body = req("GET", "/api/lesson/recommend")
    print("  GET /api/lesson/recommend -> " + str(code))
    if code == 200:
        lesson = body.get("lesson", {})
        review = body.get("review_lesson")
        print("  Daily lesson: " + str(lesson.get("title", "")))
        print("  Key insight: " + str(lesson.get("key_insight", "none")))
        print("  Review lesson: " + str(review.get("title") if review else "none"))
        return True
    return False

test("5. Daily Lesson Recommend", t_lesson)

# 6. Feedback
def t_feedback():
    code, body = req("POST", "/api/lesson/feedback", {
        "lesson_id": "daily_test_001",
        "feedback": "mastered"
    })
    print("  POST /api/lesson/feedback -> " + str(code))
    print("  Response: " + str(body))
    return True if code == 200 else False

test("6. Lesson Feedback", t_feedback)

# 7. User Stats
def t_stats():
    code, body = req("GET", "/api/user/stats")
    print("  GET /api/user/stats -> " + str(code))
    if code == 200:
        for k, v in body.items():
            print("  " + str(k) + " = " + str(v))
        return True if "total_days" in body else False
    return False

test("7. User Learning Stats", t_stats)

# 8. History
def t_history():
    _, convs = req("GET", "/api/conversations")
    conv_id = str(convs[0]["id"]) if convs else "1"
    code, body = req("GET", "/api/conversations/" + conv_id + "/history")
    print("  GET /api/conversations/" + conv_id + "/history -> " + str(code))
    if code == 200:
        print("  Messages: " + str(len(body)))
        if len(body) > 0:
            last = body[-1]
            print("  Latest: [" + str(last.get("role")) + "] " + str(last.get("content", ""))[:80])
        return True
    return False

test("8. Conversation History", t_history)

# Summary
print("\n" + "#" * 60)
print("# SUMMARY")
print("#" * 60)
passed = sum(1 for _, r in results if r is True or r.startswith("WARN"))
for name, result in results:
    status = "PASS" if result is True else "FAIL"
    print("  [" + status + "] " + name)
print("\n  Total: " + str(passed) + "/" + str(len(results)) + " passed")
print("\nAPK: E:\\Study\\Dapper_Coding_App\\app\\build\\outputs\\apk\\debug\\app-debug.apk")
