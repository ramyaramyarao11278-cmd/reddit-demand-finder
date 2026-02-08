from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from classifier import classify_posts
from task_scraper import scrape_task_posts, get_freshness_label, DEFAULT_TASK_SUBREDDITS
from task_classifier import classify_task_posts
from notifier import notify_new_tasks
import time
import threading
import os
from dotenv import load_dotenv

load_dotenv()

# ========== 已通知帖子缓存（避免重复通知） ==========
notified_post_ids = set()
notified_lock = threading.Lock()

# ========== 定时扫描器 ==========
scanner_thread = None
scanner_running = False

def auto_scan_loop():
    """后台定时扫描循环"""
    global scanner_running
    interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "30")) * 60
    print(f"[SCHEDULER] Auto-scan started, interval={interval}s")

    while scanner_running:
        try:
            print("[SCHEDULER] Running scheduled scan...")
            posts = scrape_task_posts(time_filter="week")
            classified = classify_task_posts(posts)

            # 过滤出新的 skill_match / maybe_match 帖子
            new_posts = []
            with notified_lock:
                for p in classified:
                    if p["task_category"] in ("skill_match", "maybe_match") and p["id"] not in notified_post_ids:
                        new_posts.append(p)
                        notified_post_ids.add(p["id"])

            if new_posts:
                print(f"[SCHEDULER] Found {len(new_posts)} new matching tasks, sending notification...")
                notify_new_tasks(new_posts)
            else:
                print("[SCHEDULER] No new matching tasks found.")

        except Exception as e:
            print(f"[SCHEDULER] Error during auto-scan: {e}")

        # 等待下一次扫描
        for _ in range(interval):
            if not scanner_running:
                break
            time.sleep(1)

    print("[SCHEDULER] Auto-scan stopped.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 如果配置了 Telegram 则自动启动定时扫描
    global scanner_thread, scanner_running
    auto_start = os.getenv("AUTO_SCAN_ON_START", "false").lower() == "true"
    if auto_start:
        scanner_running = True
        scanner_thread = threading.Thread(target=auto_scan_loop, daemon=True)
        scanner_thread.start()
        print("[STARTUP] Auto-scanner started")
    yield
    # Shutdown
    scanner_running = False
    print("[SHUTDOWN] Stopping auto-scanner...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/api/health")
def health():
    return {"status": "ok"}

# 模拟数据，用于测试 UI
MOCK_POSTS = [
    {
        "id": "mock1",
        "title": "I wish there was a tool that could automatically organize my bookmarks",
        "text": "I have thousands of bookmarks across different browsers and I can't find anything. Someone should build a cross-browser bookmark manager with AI categorization.",
        "score": 156,
        "num_comments": 42,
        "url": "https://reddit.com/r/SideProject/comments/mock1",
        "created": time.time() - 86400 * 3,
    },
    {
        "id": "mock2", 
        "title": "Is there an app that tracks subscription spending automatically?",
        "text": "I'd pay for something that connects to my bank and shows me all my recurring subscriptions in one place. Tired of manually checking statements.",
        "score": 89,
        "num_comments": 23,
        "url": "https://reddit.com/r/SideProject/comments/mock2",
        "created": time.time() - 86400 * 5,
    },
    {
        "id": "mock3",
        "title": "Looking for a tool to manage multiple GitHub accounts",
        "text": "I have personal and work GitHub accounts and switching between them is a pain. Any solution that automates SSH key switching?",
        "score": 67,
        "num_comments": 18,
        "url": "https://reddit.com/r/SideProject/comments/mock3",
        "created": time.time() - 86400 * 7,
    },
    {
        "id": "mock4",
        "title": "Help me fix my laptop - screen flickering",
        "text": "My laptop screen started flickering yesterday. Can't figure out what's wrong. Please help urgent!",
        "score": 12,
        "num_comments": 8,
        "url": "https://reddit.com/r/SideProject/comments/mock4",
        "created": time.time() - 86400 * 2,
    },
    {
        "id": "mock5",
        "title": "Can't log in to my account after password reset",
        "text": "I reset my password but now it says invalid credentials. How do I recover my account?",
        "score": 5,
        "num_comments": 3,
        "url": "https://reddit.com/r/SideProject/comments/mock5",
        "created": time.time() - 86400 * 1,
    },
    {
        "id": "mock6",
        "title": "Someone should build a better alternative to Notion for offline use",
        "text": "Notion is great but requires internet. We need a local-first note-taking app with similar features. I'd pay for this.",
        "score": 234,
        "num_comments": 67,
        "url": "https://reddit.com/r/SideProject/comments/mock6",
        "created": time.time() - 86400 * 10,
    },
    {
        "id": "mock7",
        "title": "Why isn't there a simple invoice generator for freelancers?",
        "text": "All invoice tools are overcomplicated. I just want to enter hours, rate, and generate a PDF. That's it.",
        "score": 45,
        "num_comments": 12,
        "url": "https://reddit.com/r/SideProject/comments/mock7",
        "created": time.time() - 86400 * 4,
    },
    {
        "id": "mock8",
        "title": "My phone battery drains too fast",
        "text": "Phone only lasts 4 hours now. Already tried factory reset. What else can I do?",
        "score": 8,
        "num_comments": 15,
        "url": "https://reddit.com/r/SideProject/comments/mock8",
        "created": time.time() - 86400 * 6,
    },
]

@app.get("/api/scan")
def scan(
    subreddit: str = Query(default="SideProject"),
    keyword: str = Query(default="I wish"),
    limit: int = Query(default=50),
    time_filter: str = Query(default="month"),
    use_mock: bool = Query(default=False),  # 默认使用真实数据
    verify_links: bool = Query(default=True),  # 是否验证链接有效性
    max_verify: int = Query(default=10),  # 验证前 N 个链接
):
    if use_mock:
        posts = MOCK_POSTS[:min(limit, len(MOCK_POSTS))]
    else:
        from reddit_scraper import scrape_subreddit, verify_posts
        posts = scrape_subreddit(subreddit, keyword, limit, time_filter)
        
        # 验证链接有效性
        if verify_links and posts:
            print(f"[DEBUG] Verifying first {max_verify} post URLs...")
            posts = verify_posts(posts, max_verify=max_verify)
    
    if not posts:
        return {
            "stats": {"total": 0, "product_needs": 0, "personal_issues": 0, "worth_looking": 0, "unclear": 0},
            "posts": [],
            "message": "No posts found. Please check subreddit name or keywords."
        }
    
    classified = classify_posts(posts)
    
    stats = {
        "total": len(classified),
        "product_needs": len([p for p in classified if p["category"] == "product_need"]),
        "personal_issues": len([p for p in classified if p["category"] == "personal_issue"]),
        "worth_looking": len([p for p in classified if p["category"] == "worth_looking"]),
        "unclear": len([p for p in classified if p["category"] == "unclear"]),
    }
    
    return {"stats": stats, "posts": classified}


# ========== TASK 扫描接口 ==========

@app.get("/api/tasks")
def scan_tasks(
    subreddits: str = Query(default=""),  # 逗号分隔, 空则用默认
    keyword: str = Query(default=""),     # 空则用默认技能关键词
    limit: int = Query(default=50),
    time_filter: str = Query(default="day"),
):
    """
    扫描 TASK 帖子，分类并返回结果
    """
    sub_list = [s.strip() for s in subreddits.split(",") if s.strip()] or None
    kw = keyword.strip() or None

    posts = scrape_task_posts(subreddits=sub_list, keyword=kw, limit=limit, time_filter=time_filter)

    if not posts:
        return {
            "stats": {"total": 0, "skill_match": 0, "maybe_match": 0, "irrelevant": 0, "danger": 0},
            "posts": [],
            "message": "No TASK posts found."
        }

    classified = classify_task_posts(posts)

    stats = {
        "total": len(classified),
        "skill_match": len([p for p in classified if p["task_category"] == "skill_match"]),
        "maybe_match": len([p for p in classified if p["task_category"] == "maybe_match"]),
        "irrelevant": len([p for p in classified if p["task_category"] == "irrelevant"]),
        "danger": len([p for p in classified if p["task_category"] == "danger"]),
    }

    return {"stats": stats, "posts": classified}


@app.post("/api/tasks/clear-cache")
def clear_cache():
    """清空已通知缓存，下次扫描会重新通知所有匹配帖子"""
    with notified_lock:
        count = len(notified_post_ids)
        notified_post_ids.clear()
    return {"status": "cleared", "removed": count}


@app.post("/api/tasks/scan-now")
def scan_now_and_notify():
    """
    手动触发一次扫描并发送通知
    可用于 n8n / cron 定时调用
    """
    posts = scrape_task_posts(time_filter="week")
    classified = classify_task_posts(posts)

    new_posts = []
    with notified_lock:
        for p in classified:
            if p["task_category"] in ("skill_match", "maybe_match") and p["id"] not in notified_post_ids:
                new_posts.append(p)
                notified_post_ids.add(p["id"])

    notified = False
    if new_posts:
        notified = notify_new_tasks(new_posts)

    return {
        "total_scanned": len(classified),
        "new_matches": len(new_posts),
        "notified": notified,
        "posts": new_posts,
    }


@app.post("/api/scheduler/start")
def start_scheduler():
    """启动定时扫描"""
    global scanner_thread, scanner_running
    if scanner_running:
        return {"status": "already_running"}

    scanner_running = True
    scanner_thread = threading.Thread(target=auto_scan_loop, daemon=True)
    scanner_thread.start()
    interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))
    return {"status": "started", "interval_minutes": interval}


@app.post("/api/scheduler/stop")
def stop_scheduler():
    """停止定时扫描"""
    global scanner_running
    scanner_running = False
    return {"status": "stopped"}
