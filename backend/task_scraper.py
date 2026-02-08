"""
TASK 帖子扫描器 - 专门扫描 r/slavelabour, r/forhire 等板块的 [TASK] 帖子
"""
import requests
import time as time_module
import os

def _get_headers():
    ua = os.getenv(
        "REDDIT_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    return {"User-Agent": ua}

# 默认扫描的 subreddit 列表
DEFAULT_TASK_SUBREDDITS = [
    "slavelabour",
    "forhire",
    "hiring",
    "freelance",
]

# 技能相关搜索关键词
SKILL_KEYWORDS = (
    "scrape OR automation OR bot OR script OR chrome extension OR web app "
    "OR tool OR n8n OR workflow OR API OR data extraction OR python "
    "OR javascript OR web scraping OR automate OR dashboard OR telegram bot"
)


def scrape_task_posts(subreddits=None, keyword=None, limit=50, time_filter="day", debug_errors=None):
    """
    扫描多个 subreddit 的 TASK 帖子
    - subreddits: 要扫描的 subreddit 列表，默认使用 DEFAULT_TASK_SUBREDDITS
    - keyword: 搜索关键词，默认使用 SKILL_KEYWORDS
    - limit: 每个 subreddit 的帖子数量限制
    - time_filter: 时间范围 (hour, day, week, month)
    """
    if subreddits is None:
        subreddits = DEFAULT_TASK_SUBREDDITS
    if keyword is None:
        keyword = SKILL_KEYWORDS

    all_posts = []

    for sub in subreddits:
        posts = _fetch_subreddit_tasks(sub, keyword, limit, time_filter, debug_errors=debug_errors)
        all_posts.extend(posts)
        # 避免请求过快被 Reddit 限流
        time_module.sleep(1.0)

    # 按创建时间降序（最新的在前面）
    all_posts.sort(key=lambda x: x["created"], reverse=True)

    # 去重（同一个帖子可能在多个搜索中出现）
    seen_ids = set()
    unique_posts = []
    for post in all_posts:
        if post["id"] not in seen_ids:
            seen_ids.add(post["id"])
            unique_posts.append(post)

    return unique_posts


def _fetch_subreddit_tasks(subreddit_name, keyword, limit, time_filter, debug_errors=None):
    """
    从单个 subreddit 抓取 TASK 帖子
    """
    url = f"https://www.reddit.com/r/{subreddit_name}/search.json"
    params = {
        "q": keyword,
        "restrict_sr": "on",
        "sort": "new",  # 按最新排序，速度很重要
        "t": time_filter,
        "limit": min(limit, 100),
        "type": "link",
    }

    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if debug_errors is not None:
            debug_errors.append({
                "subreddit": subreddit_name,
                "url": url,
                "status": status,
                "error": str(e),
            })
        print(f"[TASK] Failed to fetch r/{subreddit_name} (status={status}): {e}")
        return []
    except requests.RequestException as e:
        if debug_errors is not None:
            debug_errors.append({
                "subreddit": subreddit_name,
                "url": url,
                "status": None,
                "error": str(e),
            })
        print(f"[TASK] Failed to fetch r/{subreddit_name}: {e}")
        return []

    posts = []
    children = data.get("data", {}).get("children", [])
    print(f"[TASK] r/{subreddit_name}: found {len(children)} raw posts")

    for item in children:
        if item.get("kind") != "t3":
            continue

        post_data = item.get("data", {})

        # 跳过已删除或已移除的帖子
        if post_data.get("removed_by_category") or post_data.get("removed"):
            continue

        post_id = post_data.get("id", "")
        title = post_data.get("title", "")
        permalink = post_data.get("permalink", "")

        if not post_id or not title or not permalink:
            continue

        post_url = f"https://www.reddit.com{permalink}"
        link_flair = post_data.get("link_flair_text", "") or ""

        post = {
            "id": post_id,
            "title": title,
            "text": post_data.get("selftext", "")[:500],
            "score": post_data.get("score", 0),
            "num_comments": post_data.get("num_comments", 0),
            "url": post_url,
            "created": post_data.get("created_utc", 0),
            "subreddit": post_data.get("subreddit", subreddit_name),
            "author": post_data.get("author", "[deleted]"),
            "flair": link_flair,
        }

        posts.append(post)

        try:
            print(f"[TASK] Added: [{link_flair}] {title[:60]}...")
        except UnicodeEncodeError:
            print(f"[TASK] Added: {post_id} (title contains special chars)")

    return posts


def get_freshness_label(created_utc):
    """
    根据帖子创建时间返回新鲜度标签和分钟数
    """
    now = time_module.time()
    diff_seconds = now - created_utc
    diff_minutes = int(diff_seconds / 60)

    if diff_minutes < 10:
        return f"{diff_minutes} min ago - GO NOW!", diff_minutes
    elif diff_minutes < 30:
        return f"{diff_minutes} min ago - Very Fresh", diff_minutes
    elif diff_minutes < 60:
        return f"{diff_minutes} min ago - Fresh", diff_minutes
    elif diff_minutes < 120:
        hours = diff_minutes // 60
        return f"{hours}h ago - Still OK", diff_minutes
    elif diff_minutes < 360:
        hours = diff_minutes // 60
        return f"{hours}h ago - Hurry", diff_minutes
    elif diff_minutes < 1440:
        hours = diff_minutes // 60
        return f"{hours}h ago - Late", diff_minutes
    else:
        days = diff_minutes // 1440
        return f"{days}d ago - Probably Too Late", diff_minutes
