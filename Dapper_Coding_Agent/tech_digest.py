"""
Learning Scout v2 - Tech Digest 模块
======================================

每天采集 AI 领域最新资讯，LLM 整理成一篇简报推送�?

流程：采�?�?阅读筛�?�?整理简�?�?推�?�?闭环
"""

import hashlib as hashlib_lib
import json
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import requests

# 企业微信应用客户�?
try:
    from weixin_client import get_weixin_client, WeiXinArticle
    WEIXIN_CLIENT = None  # 延迟初始�?
except ImportError:
    WEIXIN_CLIENT = None
    WeiXinArticle = None
import trafilatura

try:
    from tavily import TavilyClient
except Exception:
    TavilyClient = None

# 复用 learning_scout �?.env 加载和环境变�?
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from learning_scout import (
    load_local_env, resolve_env_file, build_request_kwargs,
    parse_simple_yaml_feeds, fetch_feed, extract_content,
    generate_summary_and_tags, sanitize_message_text,
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_SIMULATE,
    EXTERNAL_TIMEOUT, DB_PATH, FEEDS_PATH, TAVILY_API_KEY,
    env_bool, save_items, init_learning_scout_db,
)
from memory import (
    get_profile, update_profile, update_热度权重,
    record_reading, record_digest, get_user_clicked_items,
    get_latest_digest, init_memory_db,
)

# 确保 .env 加载
load_local_env()

# ============================================================
# 配置
# ============================================================

WEIXIN_WEBHOOK_URL = os.getenv("WEIXIN_WEBHOOK_URL", "").strip()
DIGEST_DAILY_LIMIT = max(5, min(int(os.getenv("DIGEST_DAILY_LIMIT", "10") or "10"), 20))
DIGEST_MAX_ARTICLES = max(3, min(int(os.getenv("DIGEST_MAX_ARTICLES", "10") or "10"), 20))
DIGEST_CONTENT_MAX_LENGTH = int(os.getenv("DIGEST_CONTENT_MAX_LENGTH", "1000") or "1000")
DIGEST_TAVILY_ENABLED = env_bool("DIGEST_TAVILY_ENABLED", True)

# LLM 配置
LLM_DIGEST_TEMPERATURE = float(os.getenv("LLM_DIGEST_TEMPERATURE", "0.3"))
LLM_DIGEST_MAX_TOKENS = max(500, min(int(os.getenv("LLM_DIGEST_MAX_TOKENS", "1500") or "1500"), 3000))

# ============================================================
# 数据模型
# ============================================================

@dataclass
class Article:
    """文章"""
    title: str
    url: str
    source: str  # 订阅源名�?
    published_at: str
    summary: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at,
            "summary": self.summary,
            "tags": self.tags,
        }


@dataclass
class Digest:
    """生成的简�?""
    date: str
    title: str
    content: str  # 简报正文（1000字内�?
    articles: List[Article] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)


# ============================================================
# 工具函数
# ============================================================

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _hash_url(url: str) -> str:
    """简单的 URL 哈希用于去重"""
    return hashlib_lib.md5(url.encode()).hexdigest()


# ============================================================
# 1. 采集 (Collect)
# ============================================================

def collect_articles() -> List[Article]:
    """�?RSS 订阅源采集文�?""
    articles: List[Article] = []
    seen_hashes = set()

    # 加载订阅�?
    try:
        with open(FEEDS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        feeds = parse_simple_yaml_feeds(content)
        # 只取 enabled=True 的源
        feeds = [f for f in feeds if f.get("enabled", True)]
    except Exception as exc:
        logging.warning("读取 feeds.yaml 失败: %s", exc)
        feeds = []

    for feed in feeds:
        feed_name = feed.get("name", "Unknown")
        feed_url = feed.get("url", "")
        feed_tags = feed.get("tags", [])

        if not feed_url:
            continue

        try:
            items = fetch_feed(feed_url)
            for title, url, published_at, raw_content in items:
                content_hash = _hash_url(url)
                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)

                # 生成摘要
                result = generate_summary_and_tags(title, raw_content or "")
                summary = result.get("summary", "")[:200]
                tags = result.get("tags", []) + feed_tags[:3]

                articles.append(Article(
                    title=title,
                    url=url,
                    source=feed_name,
                    published_at=published_at,
                    summary=summary,
                    content=raw_content,
                    tags=list(set(tags)),
                    content_hash=content_hash,
                ))

                if len(articles) >= DIGEST_DAILY_LIMIT * 2:  # 采集足够数量
                    break
        except Exception as exc:
            logging.warning("采集订阅源失�?%s): %s", feed_name, exc)

        if len(articles) >= DIGEST_DAILY_LIMIT * 2:
            break

    logging.info("采集完成: �?%s 篇文�?, len(articles))
    return articles


def collect_tavily_articles(query: str = "AI 人工智能 最新进�?) -> List[Article]:
    """使用 Tavily 搜索最�?AI 资讯"""
    if not DIGEST_TAVILY_ENABLED or not TAVILY_API_KEY:
        return []

    if TavilyClient is None:
        logging.warning("Tavily 未安�?)
        return []

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        results = client.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            include_domains=[
                "jiqizhixin.com",
                "qubit.cn",
                "zhihu.com",
                "36kr.com",
                "segmentfault.com",
                "arxiv.org",
            ],
            time_range="week",
            max_results=5,
        )

        articles = []
        seen_hashes = set()

        for item in results.get("results", []):
            url = item.get("url", "")
            content_hash = _hash_url(url)
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)

            articles.append(Article(
                title=item.get("title", ""),
                url=url,
                source="Tavily",
                published_at=_now(),
                summary=item.get("content", "")[:200],
                content=item.get("content", ""),
                tags=["AI", "最�?],
                content_hash=content_hash,
            ))

        logging.info("Tavily 采集完成: %s 篇文�?, len(articles))
        return articles

    except Exception as exc:
        logging.warning("Tavily 搜索失败: %s", exc)
        return []


# ============================================================
# 2. 筛�?(Filter)
# ============================================================

def filter_relevant_articles(
    articles: List[Article],
    user_id: str,
    max_count: int = 10
) -> List[Article]:
    """根据用户偏好筛选最相关的文�?""
    profile = get_profile(user_id)
    interests = profile.get_关注领域_list()  # ["NLP", "CV"]
    weights = profile.get_热度权重_dict()  # {"NLP": 0.8, "CV": 0.5}

    if not interests:
        # 无偏好时，返回最新文�?
        articles.sort(key=lambda a: a.published_at, reverse=True)
        return articles[:max_count]

    scored = []
    for article in articles:
        score = 0.0

        # 领域匹配
        article_text = f"{article.title} {article.summary} {' '.join(article.tags)}".lower()
        for interest in interests:
            interest_lower = interest.lower()
            if interest_lower in article_text:
                weight = weights.get(interest, 0.5)
                score += weight * 10
                break

        # 热度权重加成
        for tag in article.tags:
            tag_upper = tag.upper()
            if tag_upper in weights:
                score += weights[tag_upper] * 2

        # 来源质量加成
        if article.source in ["机器之心", "量子�?, "知乎"]:
            score += 1.0

        scored.append((article, score))

    # 排序并去�?
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = []
    seen_titles = set()

    for article, score in scored:
        title_key = article.title[:30].lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        selected.append(article)
        if len(selected) >= max_count:
            break

    logging.info("筛选完�? 选出 %s 篇最相关文章", len(selected))
    return selected


# ============================================================
# 3. 整理 (Digest)
# ============================================================

def digest_articles(articles: List[Article], user_id: str) -> Digest:
    """LLM 将多篇文章整理成一篇简�?""
    if not articles:
        return Digest(
            date=_today(),
            title="今日 AI 速报",
            content="今日暂无新资讯�?,
            articles=[],
        )

    profile = get_profile(user_id)
    interests = profile.关注领域 or "AI/机器学习"
    difficulty = profile.难度偏好 or "入门"

    # 构建文章上下�?
    articles_context = []
    for i, article in enumerate(articles[:5], 1):  # 最多用 5 �?
        articles_context.append(f"""
【{i}】{article.title}
来源：{article.source}
摘要：{article.summary[:200]}
链接：{article.url}
""")

    articles_text = "\n".join(articles_context)

    # 构建 Prompt（注意：不在 prompt 中留日期占位符，防止 LLM 填入错误日期�?
    system_prompt = f"""你是一个专业的 AI 技术资讯编辑，负责将多�?AI 新闻整合成一篇简洁的简报�?

要求�?
1. 简�?{DIGEST_CONTENT_MAX_LENGTH} 字以�?
2. 结构清晰，包含：今日头条、重要进展、深度阅读推荐、今日小�?
3. 语言简洁，适合中文读�?
4. 深度阅读推荐要结合用户的学习方向
5. 只输出简报内容，不要解释"""

    user_prompt = f"""用户关注领域：{interests}
用户难度偏好：{difficulty}

以下是今日采集的 AI 资讯�?

{articles_text}

请整合上述资讯，生成一篇【今�?AI 速报】�?
格式如下�?
【今�?AI 速报】{_today()}

🤖 今日头条
{{最重要的一条新闻，2-3句话}}

📰 重要进展
�?{{进展1}}
�?{{进展2}}
�?{{进展3}}

📚 深度阅读推荐
《{{文章标题}}�?
推荐理由：{{为什么推荐这篇，与用户学习方向的关联}}

💬 今日小结
{{今日 AI 圈最大趋势，一句话总结}}"""

    # 调用 LLM
    if LLM_SIMULATE:
        content = f"""【今�?AI 速报】{_today()}

🤖 今日头条
OpenAI 发布 GPT-5，在多个基准测试中超越人类专家水平�?

📰 重要进展
�?Google DeepMind 提出新架构，训练效率提升 40%
�?Meta 开源新模型，支�?100+ 语言的统一表示
�?斯坦福发�?2026 AI Index 报告

📚 深度阅读推荐
《Transformer 的最新演进�?
推荐理由：与你学习的 NLP 方向高度相关

💬 今日小结
今天 AI 圈最火的方向�?高效推理"，多家厂商都在发�?更快更便�?的模型�?""
        return Digest(
            date=_today(),
            title="今日 AI 速报",
            content=content,
            articles=articles,
            topics=["大模�?, "开�?, "AI 研究"],
        )

    if not LLM_API_KEY:
        content = "LLM_API_KEY 未配置，无法生成简报�?
        return Digest(date=_today(), title="今日 AI 速报", content=content, articles=articles)

    try:
        url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": LLM_DIGEST_TEMPERATURE,
            "max_tokens": LLM_DIGEST_MAX_TOKENS,
        }

        resp = requests.post(url, headers=headers, json=body, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        raw_content = data["choices"][0]["message"]["content"]

        # 清理输出
        content = sanitize_message_text(raw_content, fallback="[简报生成失败]", limit=DIGEST_CONTENT_MAX_LENGTH * 2)

        # 修复：LLM 可能填入错误日期（如历史日期），统一将标题行替换为今天的日期
        today_str = _today()
        content = re.sub(
            r"【今�?AI 速报】[^\n]*",
            f"【今�?AI 速报】{today_str}",
            content,
            count=1
        )

        # 提取涵盖的主�?
        topics = []
        for article in articles[:3]:
            topics.extend(article.tags[:1])
        topics = list(set(topics))[:3]

        logging.info("简报生成完成，长度: %s �?, len(content))

        return Digest(
            date=today_str,
            title="今日 AI 速报",
            content=content,
            articles=articles,
            topics=topics,
        )

    except Exception as exc:
        logging.error("LLM 生成简报失�? %s", exc)
        return Digest(
            date=_today(),
            title="今日 AI 速报",
            content="[简报生成失败，请稍后再试]",
            articles=articles,
        )


# ============================================================
# 4. 推�?(Push)
# ============================================================

def push_to_weixin(content: str) -> bool:
    """推送到企业微信群机器人"""
    if not WEIXIN_WEBHOOK_URL:
        logging.warning("WEIXIN_WEBHOOK_URL 未配置，跳过企业微信推�?)
        return False

    try:
        # 分割为合适的大小（企业微信限制）
        max_len = 2000
        if len(content) > max_len:
            # 分段发�?
            parts = [content[i:i+max_len] for i in range(0, len(content), max_len)]
            for part in parts:
                payload = {"msgtype": "text", "text": {"content": part, "mentioned_list": []}}
                resp = requests.post(WEIXIN_WEBHOOK_URL, json=payload, timeout=10)
                if resp.status_code != 200:
                    logging.warning("企业微信推送失�? %s", resp.text)
                    return False
                time.sleep(0.5)
        else:
            payload = {"msgtype": "text", "text": {"content": content, "mentioned_list": []}}
            resp = requests.post(WEIXIN_WEBHOOK_URL, json=payload, timeout=10)
            if resp.status_code != 200:
                logging.warning("企业微信推送失�? %s", resp.text)
                return False

        logging.info("企业微信推送成�?)
        return True

    except Exception as exc:
        logging.error("企业微信推送异�? %s", exc)
        return False




def send_digest_card(title: str, digest_content: str, source_summary: str = "") -> bool:
    """发�?Digest Card 消息（企业微信应用）"""
    global WEIXIN_CLIENT

    if WEIXIN_CLIENT is None:
        WEIXIN_CLIENT = get_weixin_client()

    if not WEIXIN_CLIENT:
        # 降级到普通文本推�?
        content = f"**{title}**\n\n{digest_content}"
        if source_summary:
            content += f"\n\n{source_summary}"
        return push_to_weixin(content)

    # 构建摘要（Card 格式有长度限制）
    desc = digest_content[:100] + "..." if len(digest_content) > 100 else digest_content
    if source_summary:
        desc += f"\n\n{source_summary[:50]}..."

    # 使用 TextCard 格式（支持点击链接）
    # 由于我们没有公开的回�?URL，这里使�?Markdown 格式
    markdown_content = f"""**{title}**

{digest_content}

---
{source_summary if source_summary else '📬 �?Learning Scout v2 为你推�?}"""

    if WEIXIN_CLIENT.send_markdown(markdown_content):
        logging.info("Digest Card 推送成功（Markdown 格式�?)
        return True

    # 最终降�?
    return push_to_weixin(content=markdown_content)



def learn_from_feedback(user_id: str, action: str, feedback_text: str = "") -> None:
    """根据用户反馈更新偏好"""
    if action == "click":
        try:
            from learning_scout import get_user_conversation
            user_data = get_user_conversation(user_id)
            direction = user_data.get("direction", "")
            if direction:
                update_热度权重(user_id, direction, 0.1)
        except Exception:
            pass

    elif action == "like":
        try:
            from learning_scout import get_user_conversation
            user_data = get_user_conversation(user_id)
            direction = user_data.get("direction", "")
            if direction:
                update_热度权重(user_id, direction, 0.2)
        except Exception:
            pass

    elif action == "dislike":
        try:
            from learning_scout import get_user_conversation
            user_data = get_user_conversation(user_id)
            direction = user_data.get("direction", "")
            if direction:
                update_热度权重(user_id, direction, -0.1)
        except Exception:
            pass

    elif action == "too_hard":
        update_profile(user_id, 难度偏好="入门")

    elif action == "too_easy":
        update_profile(user_id, 难度偏好="进阶")

    logging.info("学习反馈: user=%s action=%s", user_id, action)


# ============================================================
# 主流�?
# ============================================================

def run_tech_digest(user_id: str, weixin_webhook: str = "") -> Optional["Digest"]:
    """
    执行 Tech Digest 全流�?
    """
    logging.info("=" * 50)
    logging.info("Tech Digest 开始执�?| user_id=%s", user_id)
    logging.info("=" * 50)

    # 0. 检查是否今日已推�?
    latest = get_latest_digest(user_id)
    if latest and latest.push_date == _today():
        logging.info("今日已推送过 Tech Digest，跳�?)
        return None

    # 1. 采集
    logging.info("[1/4] 采集文章...")
    articles = collect_articles()
    tavily_articles = collect_tavily_articles()
    articles.extend(tavily_articles)

    if not articles:
        logging.warning("今日无新文章可推�?)
        return None

    # 2. 筛�?
    logging.info("[2/4] 筛选相关文�?..")
    selected = filter_relevant_articles(articles, user_id, max_count=DIGEST_MAX_ARTICLES)

    if not selected:
        logging.warning("筛选后无可推送文�?)
        return None

    # 3. 整理
    logging.info("[3/4] 生成简�?..")
    digest = digest_articles(selected, user_id)

    # 4. 推�?
    logging.info("[4/4] 推送简�?..")

    # 优先使用企业微信应用推送（支持 Card 格式�?
    # 降级�?Webhook
    card_sent = send_digest_card(digest.title, digest.content)
    if not card_sent:
        weixin_webhook = weixin_webhook or WEIXIN_WEBHOOK_URL
        if weixin_webhook:
            push_to_weixin(digest.content)


    # 5. 记录到记�?
    record_digest(
        user_id=user_id,
        push_date=digest.date,
        title=digest.title,
        content=digest.content,
        source_articles=[a.to_dict() for a in digest.articles],
    )

    # 更新热度权重
    for topic in digest.topics:
        update_热度权重(user_id, topic, 0.05)

    logging.info("=" * 50)
    logging.info("Tech Digest 执行完成 | %s 字，%s 篇参考文�?, len(digest.content), len(digest.articles))
    logging.info("=" * 50)

    return digest


def run_daily_digest_batch() -> Dict[str, Any]:
    """批量为所有活跃用户执�?Tech Digest"""
    summary: Dict[str, Any] = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
    }

    try:
        from memory import get_all_active_users
        users = get_all_active_users()
        summary["total"] = len(users)
    except Exception as exc:
        logging.warning("获取活跃用户失败: %s", exc)
        users = []

    for user_id in users:
        try:
            digest = run_tech_digest(user_id)
            if digest:
                summary["success"] += 1
            else:
                summary["skipped"] += 1
        except Exception as exc:
            logging.error("Tech Digest 执行失败(user=%s): %s", user_id, exc)
            summary["failed"] += 1
            summary["errors"].append(f"{user_id}: {exc}")

    logging.info("批量执行完成: %s/%s 成功, %s 跳过, %s 失败",
                 summary["success"], summary["total"], summary["skipped"], summary["failed"])

    return summary


# ============================================================
# 自我测试
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("=" * 50)
    print("Tech Digest Module Test")
    print("=" * 50)

    # 初始化数据库
    init_memory_db()
    init_learning_scout_db()

    # 测试用户
    test_user = "test_digest_user"

    # 设置用户偏好
    update_profile(test_user, 关注领域="NLP,机器学习", 难度偏好="入门")
    print("用户偏好设置完成")

    # 执行 Tech Digest（模拟模式）
    digest = run_tech_digest(
        user_id=test_user,
        weixin_webhook="",  # 不填测试
    )

    if digest:
        print("\n" + "=" * 50)
        print("生成的简�?")
        print("=" * 50)
        print(digest.content)
        print("\n参考文章数:", len(digest.articles))
        print("涵盖主题:", digest.topics)
    else:
        print("Tech Digest 未生成（可能今日已推送或无新文章�?)

    print("\n" + "=" * 50)
    print("Tech Digest Module Test DONE")
    print("=" * 50)
