import requests
import time as time_module

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def validate_post_url(post_id, timeout=5):
    """
    验证帖子是否有效（使用 Reddit JSON API）
    """
    try:
        # 使用 Reddit JSON API 检查帖子是否存在
        url = f"https://www.reddit.com/comments/{post_id}.json"
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            # 检查是否是有效的帖子数据
            if data and len(data) > 0:
                return True
        return False
    except requests.RequestException:
        return False

def scrape_subreddit(subreddit_name, keyword, limit, time_filter):
    """
    使用 Reddit 公开 JSON API 抓取帖子，无需 API 凭证
    """
    # 使用 www.reddit.com 的 JSON API
    url = f"https://www.reddit.com/r/{subreddit_name}/search.json"
    params = {
        "q": keyword,
        "restrict_sr": "on",  # 限制在该 subreddit 内搜索
        "sort": "relevance",
        "t": time_filter,     # hour, day, week, month, year, all
        "limit": min(limit, 100),  # Reddit 单次最多返回 100 条
        "type": "link",       # 只搜索帖子，不包括评论
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"Reddit API request failed: {e}")
        return []
    
    posts = []
    children = data.get("data", {}).get("children", [])
    
    print(f"[DEBUG] Found {len(children)} posts from Reddit API")
    
    for item in children:
        # 确保是帖子类型 (t3 = link/post)
        if item.get("kind") != "t3":
            continue
            
        post_data = item.get("data", {})
        
        # 跳过已删除或已移除的帖子
        if post_data.get("removed_by_category") or post_data.get("removed"):
            print(f"[DEBUG] Skipping removed post: {post_data.get('id')}")
            continue
        
        # 获取必要字段，确保数据完整性
        post_id = post_data.get("id", "")
        title = post_data.get("title", "")
        permalink = post_data.get("permalink", "")
        
        if not post_id or not title or not permalink:
            print(f"[DEBUG] Skipping incomplete post: id={post_id}")
            continue
        
        # 构建正确的 URL
        post_url = f"https://www.reddit.com{permalink}"
        
        # 构建帖子对象，确保所有字段来自同一个 post_data
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
        }
        
        posts.append(post)
        
        # 安全打印，避免 Windows 控制台 Unicode 错误
        try:
            print(f"[DEBUG] Added post: {post_id} - {title[:50]}...")
        except UnicodeEncodeError:
            print(f"[DEBUG] Added post: {post_id} - (title contains special chars)")
    
    print(f"[DEBUG] Returning {len(posts)} valid posts")
    return posts

def verify_posts(posts, max_verify=10):
    """
    验证帖子链接是否有效（可选，对前 N 个帖子进行验证）
    """
    verified = []
    for i, post in enumerate(posts):
        if i < max_verify:
            if validate_post_url(post["id"]):
                verified.append(post)
            else:
                print(f"[DEBUG] Invalid post: {post['id']}")
            # 避免请求过快
            time_module.sleep(0.3)
        else:
            # 超过验证数量的帖子直接添加
            verified.append(post)
    return verified
