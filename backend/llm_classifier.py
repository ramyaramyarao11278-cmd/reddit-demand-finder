"""
LLM 二次分类器
对正则匹配后的 skill_match / maybe_match 帖子进行深度分析
输出：具体需要什么技能、预估工时、建议报价、回复建议
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# 支持 OpenAI 兼容的 API（OpenAI、DeepSeek、Groq、本地 Ollama 等）
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are a freelance project analyst. You help a developer decide whether to take on Reddit freelance tasks.

The developer's skills are:
- Web scraping (Python, Selenium, Playwright, BeautifulSoup)
- Browser extensions (Chrome extensions)
- Automation workflows (n8n, Make, Zapier)
- Web apps (Python FastAPI, JavaScript, React, Node.js)
- AI integrations (OpenAI API, RAG, chatbots)
- Data extraction and processing
- Telegram/Discord bots
- APIs and integrations

Analyze the task post and respond in JSON format ONLY, no markdown, no explanation outside JSON:
{
    "worth_taking": true/false,
    "confidence": 0.0-1.0,
    "required_skills": ["skill1", "skill2"],
    "estimated_hours": number,
    "suggested_bid_usd": number,
    "difficulty": "easy" / "medium" / "hard",
    "red_flags": ["flag1"] or [],
    "summary": "One sentence summary of what the client needs",
    "reply_draft": "A short, professional reply you can post on Reddit to express interest"
}

Rules:
- If the task involves anything illegal, unethical, or accessing someone else's accounts, set worth_taking to false and explain in red_flags
- Be realistic about hours and pricing - this is r/slavelabour level, not enterprise
- suggested_bid_usd should be competitive but not too low (minimum $20 for any task)
- reply_draft should be casual, friendly, and show you understand the task
- Keep reply_draft under 100 words
"""


def analyze_task_with_llm(post):
    """
    用 LLM 分析单个 TASK 帖子
    返回分析结果 dict，失败返回 None
    """
    if not LLM_API_KEY:
        print("[LLM] API key not configured, skipping LLM analysis")
        return None

    user_message = f"""Reddit Post from r/{post.get('subreddit', 'unknown')}:

Title: {post['title']}

Content: {post.get('text', 'No content')[:800]}

Post score: {post.get('score', 0)} | Comments: {post.get('num_comments', 0)}
Budget mentioned: ${post.get('budget', 'Not specified')}
Freshness: {post.get('freshness_label', 'Unknown')}"""

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }

    try:
        resp = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"].strip()

        # 清理可能的 markdown 包裹
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        result = json.loads(content)
        print(f"[LLM] Analysis complete for: {post['title'][:50]}...")
        return result

    except json.JSONDecodeError as e:
        print(f"[LLM] Failed to parse JSON response: {e}")
        print(f"[LLM] Raw response: {content[:200]}")
        return None
    except requests.RequestException as e:
        print(f"[LLM] API request failed: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"[LLM] Unexpected response format: {e}")
        return None


def enrich_tasks_with_llm(posts, max_analyze=5):
    """
    对帖子列表中的 skill_match 和 maybe_match 帖子进行 LLM 分析
    - max_analyze: 最多分析几个帖子（控制 API 费用）
    - 只分析最新的、最相关的帖子
    """
    if not LLM_API_KEY:
        print("[LLM] No API key, returning posts without LLM enrichment")
        return posts

    # 筛选需要分析的帖子
    to_analyze = [
        p for p in posts
        if p.get("task_category") in ("skill_match", "maybe_match")
    ]

    # 优先分析 skill_match，然后 maybe_match，都按新鲜度排序
    to_analyze.sort(key=lambda x: (
        0 if x.get("task_category") == "skill_match" else 1,
        x.get("freshness_minutes", 9999),
    ))

    analyzed_count = 0
    for post in to_analyze:
        if analyzed_count >= max_analyze:
            break

        result = analyze_task_with_llm(post)
        if result:
            post["llm_analysis"] = result
            analyzed_count += 1

            # 如果 LLM 说不值得接，降级分类
            if not result.get("worth_taking", True):
                post["task_category"] = "irrelevant"
                post["llm_rejected"] = True

    print(f"[LLM] Analyzed {analyzed_count} posts")
    return posts
