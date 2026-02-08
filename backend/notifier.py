"""
通知模块 - 支持 Telegram + PushPlus（微信）双通道推送
当发现匹配的 TASK 帖子时发送通知
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# PushPlus 配置
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")


def send_telegram_message(text, parse_mode="HTML"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        print("[NOTIFY] Telegram sent")
        return True
    except requests.RequestException as e:
        print(f"[NOTIFY] Telegram failed: {e}")
        return False


def send_pushplus_message(title, content):
    if not PUSHPLUS_TOKEN:
        return False
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html",
    }
    try:
        resp = requests.post(url, json=data, timeout=10)
        result = resp.json()
        if result.get("code") == 200:
            print("[NOTIFY] PushPlus sent")
            return True
        print(f"[NOTIFY] PushPlus error: {result}")
        return False
    except requests.RequestException as e:
        print(f"[NOTIFY] PushPlus failed: {e}")
        return False


def format_task_html(post):
    freshness = post.get("freshness_label", "Unknown")
    budget_str = f"${post['budget']:.0f}" if post.get("budget") else "Not specified"
    skills = ", ".join(post.get("skill_matches", [])[:5]) or "N/A"
    text_preview = post.get("text", "")[:200]

    html = f"""
    <div style="margin-bottom:16px;padding:12px;border-left:3px solid #00ced1;background:#f8f9fa;">
        <h4 style="margin:0 0 8px 0;">{post['title']}</h4>
        <p>r/{post.get('subreddit', '?')} | {freshness} | Budget: {budget_str}</p>
        <p>Regex Skills: {skills}</p>
        <p style="color:#666;">{text_preview}</p>
        <a href="{post['url']}">Open on Reddit</a>
    """

    # 如果有 LLM 分析结果，追加
    llm = post.get("llm_analysis")
    if llm:
        worth = "YES" if llm.get("worth_taking") else "NO"
        worth_color = "#00b894" if llm.get("worth_taking") else "#d63031"
        red_flags = ", ".join(llm.get("red_flags", [])) or "None"

        html += f"""
        <div style="margin-top:10px;padding:10px;background:#eef;border-radius:6px;">
            <p><b>AI Analysis:</b></p>
            <p>Worth taking: <span style="color:{worth_color};font-weight:bold;">{worth}</span></p>
            <p>Difficulty: {llm.get('difficulty', '?')} | Est. hours: {llm.get('estimated_hours', '?')} | Suggested bid: ${llm.get('suggested_bid_usd', '?')}</p>
            <p>Skills needed: {', '.join(llm.get('required_skills', []))}</p>
            <p>Red flags: {red_flags}</p>
            <p>Summary: {llm.get('summary', '')}</p>
            <p style="background:#fff;padding:8px;border-radius:4px;margin-top:6px;">
                <b>Draft reply:</b><br>{llm.get('reply_draft', '')}</p>
        </div>
        """

    html += "</div>"
    return html


def format_task_telegram(post):
    freshness = post.get("freshness_label", "Unknown")
    budget_str = f"${post['budget']:.0f}" if post.get("budget") else "N/A"
    skills = ", ".join(post.get("skill_matches", [])[:5]) or "N/A"
    text_preview = post.get("text", "")[:200]

    msg = (
        f"<b>{post['title']}</b>\n"
        f"r/{post.get('subreddit', '?')} | {freshness}\n"
        f"Budget: {budget_str} | Skills: {skills}\n"
        f"{text_preview}\n"
    )

    llm = post.get("llm_analysis")
    if llm:
        worth = "YES" if llm.get("worth_taking") else "NO"
        msg += (
            f"\n--- AI Analysis ---\n"
            f"Worth: {worth} | {llm.get('difficulty', '?')} | ~{llm.get('estimated_hours', '?')}h | ${llm.get('suggested_bid_usd', '?')}\n"
            f"Summary: {llm.get('summary', '')}\n"
        )

    msg += f"<a href=\"{post['url']}\">Open</a>\n"
    return msg


def notify_new_tasks(posts):
    if not posts:
        return False

    relevant = [p for p in posts if p.get("task_category") in ("skill_match", "maybe_match")]
    if not relevant:
        return False

    success = False

    # 尝试 PushPlus（微信通知）
    if PUSHPLUS_TOKEN:
        html_content = f"<h2>Found {len(relevant)} matching tasks</h2>"
        for post in relevant[:10]:
            html_content += format_task_html(post)
        if send_pushplus_message(f"{len(relevant)} new Reddit tasks", html_content):
            success = True

    # 尝试 Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        if len(relevant) <= 2:
            for post in relevant:
                msg = format_task_telegram(post)
                send_telegram_message(msg)
            success = True
        else:
            lines = [f"<b>Found {len(relevant)} matching tasks</b>\n"]
            for i, post in enumerate(relevant[:10], 1):
                freshness = post.get("freshness_label", "")
                lines.append(f"{i}. <b>{post['title'][:80]}</b>\n   {freshness}\n   <a href=\"{post['url']}\">Open</a>\n")
            send_telegram_message("\n".join(lines))
            success = True

    if not success:
        print("[NOTIFY] No notification channel configured")

    return success
