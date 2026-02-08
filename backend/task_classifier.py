"""
TASK 帖子技能匹配分类器
判断帖子是否匹配你的技能，并过滤掉危险/不相关的帖子
"""
import re

# ========== 技能匹配信号词 ==========
SKILL_MATCH_SIGNALS = [
    r"scrap(e|ing|er)",
    r"automat(e|ion|ed)",
    r"bot",
    r"script",
    r"chrome extension",
    r"browser extension",
    r"web (app|tool|application|site|scraper)",
    r"api",
    r"data (extract|scrap|collect|min|pars|crawl)",
    r"python",
    r"javascript",
    r"n8n",
    r"make\.com",
    r"zapier",
    r"workflow",
    r"dashboard",
    r"spreadsheet",
    r"csv",
    r"excel",
    r"google sheets",
    r"telegram",
    r"discord bot",
    r"web develop",
    r"full.?stack",
    r"front.?end",
    r"back.?end",
    r"react",
    r"node\.?js",
    r"database",
    r"sql",
    r"mongodb",
    r"lead (gen|list|scrape)",
    r"email (scrape|extract|collect|find|list)",
    r"monitor(ing)?",
    r"alert(s|ing)?",
    r"notif(y|ication)",
    r"cron",
    r"schedul(e|ed|ing)",
    r"pdf",
    r"report",
    r"parse",
    r"crawl",
    r"selenium",
    r"playwright",
    r"puppeteer",
]

# ========== 危险/不相关过滤词 ==========
DANGER_SIGNALS = [
    r"adult content",
    r"nsfw",
    r"remote desktop",
    r"login to my account",
    r"log into my account",
    r"use my account",
    r"access my account",
    r"social media manag",
    r"virtual assistant",
    r"content writ(e|ing|er)",
    r"ghost.?writ",
    r"seo (article|content|blog|writ)",
    r"essay",
    r"homework",
    r"assignment",
    r"exam",
    r"test.?tak",
    r"class.?tak",
    r"catfish",
    r"fake (review|account|profile|identity)",
    r"click.?farm",
    r"like.?farm",
    r"follow.?farm",
    r"vote.?manipulat",
    r"hack",
    r"crack",
    r"pirat",
    r"torrent",
    r"illegal",
    r"personal (info|information|data) of",
    r"dox",
    r"stalk",
    r"spy",
    r"phish",
    r"malware",
    r"ransomware",
    r"crypto pump",
    r"ponzi",
]

# ========== 其他 freelancer 推销帖过滤 ==========
OFFER_SIGNALS = [
    r"\[for hire\]",
    r"\[offer\]",
    r"i (build|create|make|develop|design)",
    r"i (can|will) (build|create|make|develop)",
    r"hire me",
    r"my (services|rates|portfolio)",
    r"i('m| am) (a|an) (developer|designer|freelancer|expert)",
    r"\$\d+/hr",
    r"per hour",
]

# ========== 非技术类任务过滤 ==========
NON_TECH_SIGNALS = [
    r"grow .*(facebook|fb|instagram|ig|tiktok|twitter)",
    r"social media (market|manag|grow)",
    r"follow(ers|ing)",
    r"(get|buy|grow) (likes|followers|subscribers|members)",
    r"content creat",
    r"influencer",
    r"blog (post|writ)",
    r"article writ",
    r"copywriting",
    r"translation",
    r"transcri(be|ption)",
    r"data entry",
    r"virtual assistant",
]

# ========== 预算提取正则 ==========
BUDGET_PATTERNS = [
    r"\$(\d+[\.\d]*)",
    r"(\d+[\.\d]*)\s*(?:usd|dollars?)",
    r"budget[:\s]*\$?(\d+[\.\d]*)",
    r"pay(?:ing)?\s*\$?(\d+[\.\d]*)",
]


def score_text(text, patterns):
    text_lower = text.lower()
    score = 0
    matched = []
    for pattern in patterns:
        if re.search(pattern, text_lower):
            score += 1
            matched.append(pattern)
    return score, matched


def extract_budget(text):
    """从帖子文本中提取预算金额"""
    text_lower = text.lower()
    budgets = []
    for pattern in BUDGET_PATTERNS:
        matches = re.findall(pattern, text_lower)
        for m in matches:
            try:
                budgets.append(float(m))
            except ValueError:
                pass
    return max(budgets) if budgets else None


def classify_task_posts(posts):
    """
    对 TASK 帖子进行技能匹配分类
    返回分类后的帖子列表，每个帖子增加:
    - task_category: skill_match / danger / irrelevant
    - skill_score: 技能匹配分数
    - danger_score: 危险信号分数
    - skill_matches: 匹配到的技能词
    - danger_matches: 匹配到的危险词
    - budget: 提取到的预算金额 (可选)
    - freshness_label: 新鲜度标签
    - freshness_minutes: 距离发布的分钟数
    """
    from task_scraper import get_freshness_label

    results = []
    for post in posts:
        full_text = f"{post['title']} {post['text']}"

        # 过滤掉 [For Hire] / [OFFER] 帖子（其他 freelancer 的广告，不是客户需求）
        title_lower = post["title"].lower()
        flair_check = post.get("flair", "").lower()

        is_offer_post = (
            "[for hire]" in title_lower
            or "[offer]" in title_lower
            or "for hire" in flair_check
            or "offer" in flair_check
        )

        if is_offer_post:
            freshness_label, freshness_minutes = get_freshness_label(post["created"])
            results.append({
                **post,
                "task_category": "irrelevant",
                "confidence": 0.1,
                "skill_score": 0,
                "danger_score": 0,
                "skill_matches": [],
                "danger_matches": [],
                "budget": None,
                "freshness_label": freshness_label,
                "freshness_minutes": freshness_minutes,
            })
            continue

        skill_score, skill_matches = score_text(full_text, SKILL_MATCH_SIGNALS)
        danger_score, danger_matches = score_text(full_text, DANGER_SIGNALS)

        budget = extract_budget(full_text)
        freshness_label, freshness_minutes = get_freshness_label(post["created"])

        # 判断 flair 是否是 [TASK] 类型（加分）
        flair = post.get("flair", "").lower()
        is_task_flair = "task" in flair or "hiring" in flair or "job" in flair

        if is_task_flair:
            skill_score += 1

        # 检查是否是其他 freelancer 的推销帖 / 非技术类任务
        offer_score, offer_matches = score_text(full_text, OFFER_SIGNALS)
        non_tech_score, non_tech_matches = score_text(full_text, NON_TECH_SIGNALS)

        # 分类逻辑
        if danger_score > 0:
            task_category = "danger"
            confidence = min(danger_score / 3, 1.0)
        elif offer_score >= 1:
            task_category = "irrelevant"
            confidence = 0.8
        elif non_tech_score >= 1 and skill_score <= 1:
            task_category = "irrelevant"
            confidence = 0.6
        elif skill_score >= 2:
            task_category = "skill_match"
            confidence = min(skill_score / 5, 1.0)
        elif skill_score == 1:
            task_category = "maybe_match"
            confidence = 0.4
        else:
            task_category = "irrelevant"
            confidence = 0.2

        results.append({
            **post,
            "task_category": task_category,
            "confidence": round(confidence, 2),
            "skill_score": skill_score,
            "danger_score": danger_score,
            "skill_matches": skill_matches,
            "danger_matches": danger_matches,
            "budget": budget,
            "freshness_label": freshness_label,
            "freshness_minutes": freshness_minutes,
        })

    # 排序: skill_match 优先, 然后按新鲜度排序（越新越靠前）
    category_order = {"skill_match": 0, "maybe_match": 1, "irrelevant": 2, "danger": 3}
    results.sort(key=lambda x: (
        category_order.get(x["task_category"], 9),
        x["freshness_minutes"],  # 越小越新
    ))

    # ===== LLM 二次分析 =====
    try:
        from llm_classifier import enrich_tasks_with_llm
        results = enrich_tasks_with_llm(results, max_analyze=5)
    except Exception as e:
        print(f"[LLM] Enrichment failed, continuing without LLM: {e}")

    return results
