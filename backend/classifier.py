import re

# 产品需求信号词
NEED_SIGNALS = [
    r"i wish there was",
    r"i('d| would) pay for",
    r"why (is there no|isn't there|hasn't anyone)",
    r"someone should (build|make|create)",
    r"is there (an app|a tool|a service|software)",
    r"looking for (a tool|an app|a solution|software)",
    r"tired of (manually|doing this|having to)",
    r"there should be",
    r"need a (tool|app|service|solution|way to)",
    r"any (tool|app|service|alternative) (for|to|that)",
    r"how do (you all|y'all|people) (handle|manage|deal with)",
    r"we need",
    r"pain point",
    r"workflow",
    r"automate",
    # 新增: 创业/SaaS 相关信号词
    r"build (a|an|my|the) (saas|app|tool|product|startup)",
    r"pivot",
    r"validat(e|ion)",
    r"side project",
    r"market (research|opportunity|gap|need)",
    r"customer (pain|problem|need|feedback)",
    r"would you (use|pay|buy|switch)",
    r"feedback (on|for|about)",
    r"launch(ed|ing)?|shipp(ed|ing)",
    r"monetiz",
    r"mvp",
    r"indie (hacker|maker|dev)",
    r"saas",
    r"recurring revenue",
    r"finding (users|customers|clients)",
    r"problem worth solving",
    r"lead gen",
]

# 个人问题信号词
PERSONAL_SIGNALS = [
    r"help me",
    r"my (phone|computer|laptop|device|account)",
    r"can't (log in|login|sign in|access|open|unlock)",
    r"how (do i|to) (fix|reset|recover|restore|unlock)",
    r"stopped working",
    r"broken",
    r"error message",
    r"not working",
    r"please help",
    r"urgent",
    r"troubleshoot",
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

def classify_posts(posts):
    results = []
    for post in posts:
        full_text = f"{post['title']} {post['text']}"
        
        need_score, need_matches = score_text(full_text, NEED_SIGNALS)
        personal_score, personal_matches = score_text(full_text, PERSONAL_SIGNALS)
        
        # 评论数和点赞数作为加权因素
        engagement_bonus = 0
        if post["num_comments"] >= 10:
            engagement_bonus += 1
        if post["score"] >= 20:
            engagement_bonus += 1
        
        need_score += engagement_bonus
        
        # 高互动帖子标记
        high_engagement = post["num_comments"] > 20 or post["score"] > 10
        
        if need_score > personal_score and need_score >= 2:
            category = "product_need"
            confidence = min(need_score / 5, 1.0)
        elif personal_score > need_score:
            category = "personal_issue"
            confidence = min(personal_score / 4, 1.0)
        elif high_engagement and need_score >= 1:
            # 高互动 + 至少匹配一个信号词 = 值得看看
            category = "worth_looking"
            confidence = 0.5
        elif high_engagement:
            # 纯粹高互动，没有信号词匹配
            category = "worth_looking"
            confidence = 0.4
        else:
            category = "unclear"
            confidence = 0.3
        
        results.append({
            **post,
            "category": category,
            "confidence": round(confidence, 2),
            "need_score": need_score,
            "personal_score": personal_score,
            "need_matches": need_matches,
            "personal_matches": personal_matches,
        })
    
    # 按需求分数降序排列，product_need 优先，其次 worth_looking
    results.sort(key=lambda x: (
        x["category"] == "product_need",
        x["category"] == "worth_looking",
        x["need_score"]
    ), reverse=True)
    return results
