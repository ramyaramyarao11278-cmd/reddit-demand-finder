from reddit_scraper import scrape_subreddit, validate_post_url, verify_posts

print("Testing Reddit Scraper with JSON API Validation...")
posts = scrape_subreddit("SideProject", "I wish", 5, "month")

print(f"\n=== Validating Posts via JSON API ===\n")

for i, post in enumerate(posts[:3]):
    post_id = post['id']
    is_valid = validate_post_url(post_id)
    print(f"Post {i+1}: {post['title'][:50]}...")
    print(f"  ID: {post_id}")
    print(f"  URL: {post['url']}")
    print(f"  Valid: {'YES' if is_valid else 'NO'}")
    print()

print("\n=== Testing verify_posts function ===\n")
verified = verify_posts(posts[:3], max_verify=3)
print(f"Verified {len(verified)} out of 3 posts")
