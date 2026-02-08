"""Test script to verify classifier improvements"""
from reddit_scraper import scrape_subreddit
from classifier import classify_posts

def safe_print(text):
    """安全打印，处理 Windows 控制台 Unicode 问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode())

# 从多个 subreddit 抓取帖子
posts = []
for subreddit in ['SideProject', 'Entrepreneur', 'SaaS']:
    posts.extend(scrape_subreddit(subreddit, "tool OR app OR build OR need", limit=15, time_filter="week"))
print(f'Total posts: {len(posts)}')

classified = classify_posts(posts)

# Count by category
categories = {}
for p in classified:
    cat = p['category']
    categories[cat] = categories.get(cat, 0) + 1

print(f'\n=== Classification Results ===')
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f'{cat}: {count}')

print(f'\n=== Product Needs ===')
for p in classified:
    if p['category'] == 'product_need':
        safe_print(f"- [score:{p['need_score']}] {p['title'][:70]}...")
        safe_print(f"  Matches: {p['need_matches'][:3]}")

print(f'\n=== Worth Looking ===')
for p in classified:
    if p['category'] == 'worth_looking':
        safe_print(f"- [score:{p['need_score']}] {p['title'][:70]}...")
        safe_print(f"  Comments: {p['num_comments']}, Score: {p['score']}")

print(f'\n=== Unclear ===')
for p in classified:
    if p['category'] == 'unclear':
        safe_print(f"- {p['title'][:70]}...")
