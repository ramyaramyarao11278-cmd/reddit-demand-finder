const API_BASE = "http://localhost:8000";
let allPosts = [];
let allTasks = [];
let currentMode = "demand"; // "demand" or "task"

// ========== Mode Switching ==========

function switchMode(mode, tabEl) {
    currentMode = mode;
    document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
    tabEl.classList.add("active");

    document.getElementById("demandPanel").style.display = mode === "demand" ? "flex" : "none";
    document.getElementById("taskPanel").style.display = mode === "task" ? "flex" : "none";
    document.getElementById("stats").style.display = "none";
    document.getElementById("taskStats").style.display = "none";
    document.getElementById("demandFilters").style.display = mode === "demand" ? "flex" : "none";
    document.getElementById("taskFilters").style.display = mode === "task" ? "flex" : "none";
    document.getElementById("results").innerHTML = "";
}

// ========== Demand Finder (original) ==========

async function scan() {
    const subreddit = document.getElementById("subreddit").value.trim();
    const keyword = document.getElementById("keyword").value.trim();
    const timeFilter = document.getElementById("timeFilter").value;
    const limit = document.getElementById("limit").value;
    const btn = document.getElementById("scanBtn");

    btn.disabled = true;
    btn.textContent = "Scanning...";
    document.getElementById("loading").style.display = "block";
    document.getElementById("results").innerHTML = "";
    document.getElementById("stats").style.display = "none";

    try {
        const params = new URLSearchParams({ subreddit, keyword, limit, time_filter: timeFilter });
        const res = await fetch(`${API_BASE}/api/scan?${params}`);
        const data = await res.json();

        allPosts = data.posts;
        renderStats(data.stats);
        renderPosts(allPosts);
    } catch (err) {
        document.getElementById("results").innerHTML =
            `<div style="color:#d63031;text-align:center;padding:20px;">Request failed: ${err.message}<br>Please make sure backend is running</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "Scan";
        document.getElementById("loading").style.display = "none";
    }
}

function renderStats(stats) {
    document.getElementById("stats").style.display = "flex";
    document.getElementById("statNeed").textContent = stats.product_needs;
    document.getElementById("statPersonal").textContent = stats.personal_issues;
    document.getElementById("statWorth").textContent = stats.worth_looking || 0;
    document.getElementById("statUnclear").textContent = stats.unclear;
    document.getElementById("statTotal").textContent = stats.total;
}

function renderPosts(posts) {
    const container = document.getElementById("results");

    if (posts.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:#666;padding:40px;">No results found</div>';
        return;
    }

    container.innerHTML = posts.map(post => {
        const categoryLabel = {
            product_need: "Product Need",
            personal_issue: "Personal Issue",
            worth_looking: "Worth Looking",
            unclear: "Unclear"
        }[post.category];

        const confLevel = post.confidence >= 0.7 ? "high" : post.confidence >= 0.4 ? "med" : "low";
        const textPreview = post.text ? post.text.substring(0, 150) + (post.text.length > 150 ? "..." : "") : "";
        const date = new Date(post.created * 1000).toLocaleDateString("en-US");

        return `
            <div class="post-card ${post.category}">
                <div class="post-header">
                    <a class="post-title" href="${post.url}" target="_blank">${escapeHtml(post.title)}</a>
                    <span class="post-badge ${post.category}">${categoryLabel}</span>
                </div>
                ${textPreview ? `<div class="post-text">${escapeHtml(textPreview)}</div>` : ""}
                <div class="post-meta">
                    <span>↑ ${post.score}</span>
                    <span>💬 ${post.num_comments}</span>
                    <span>${date}</span>
                    <span>
                        Confidence
                        <span class="confidence-bar">
                            <span class="confidence-fill ${confLevel}" style="width:${post.confidence * 100}%"></span>
                        </span>
                        ${Math.round(post.confidence * 100)}%
                    </span>
                    <span>Need: ${post.need_score} | Personal: ${post.personal_score}</span>
                </div>
            </div>
        `;
    }).join("");
}

function filterPosts(category, tabEl) {
    document.querySelectorAll("#demandFilters .tab").forEach(t => t.classList.remove("active"));
    tabEl.classList.add("active");

    if (category === "all") {
        renderPosts(allPosts);
    } else {
        renderPosts(allPosts.filter(p => p.category === category));
    }
}

// ========== Task Hunter (new) ==========

async function scanTasks() {
    const subreddits = document.getElementById("taskSubreddits").value.trim();
    const timeFilter = document.getElementById("taskTimeFilter").value;
    const limit = document.getElementById("taskLimit").value;
    const btn = document.getElementById("taskScanBtn");

    btn.disabled = true;
    btn.textContent = "Hunting...";
    document.getElementById("loading").style.display = "block";
    document.getElementById("results").innerHTML = "";
    document.getElementById("taskStats").style.display = "none";

    try {
        const params = new URLSearchParams({ subreddits, limit, time_filter: timeFilter });
        const res = await fetch(`${API_BASE}/api/tasks?${params}`);
        const data = await res.json();

        allTasks = data.posts;
        renderTaskStats(data.stats);
        renderTasks(allTasks);
    } catch (err) {
        document.getElementById("results").innerHTML =
            `<div style="color:#d63031;text-align:center;padding:20px;">Request failed: ${err.message}<br>Please make sure backend is running</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "Hunt Tasks";
        document.getElementById("loading").style.display = "none";
    }
}

function renderTaskStats(stats) {
    document.getElementById("taskStats").style.display = "flex";
    document.getElementById("statSkillMatch").textContent = stats.skill_match;
    document.getElementById("statMaybe").textContent = stats.maybe_match;
    document.getElementById("statIrrelevant").textContent = stats.irrelevant;
    document.getElementById("statDanger").textContent = stats.danger;
    document.getElementById("statTaskTotal").textContent = stats.total;
}

function renderTasks(tasks) {
    const container = document.getElementById("results");

    if (tasks.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:#666;padding:40px;">No TASK posts found</div>';
        return;
    }

    container.innerHTML = tasks.map(task => {
        const categoryLabel = {
            skill_match: "Skill Match",
            maybe_match: "Maybe",
            irrelevant: "Irrelevant",
            danger: "Danger"
        }[task.task_category];

        const confLevel = task.confidence >= 0.7 ? "high" : task.confidence >= 0.4 ? "med" : "low";
        const textPreview = task.text ? task.text.substring(0, 200) + (task.text.length > 200 ? "..." : "") : "";
        const budgetStr = task.budget ? `$${task.budget}` : "";
        const freshness = task.freshness_label || "";

        // Freshness urgency class
        let freshnessClass = "stale";
        if (task.freshness_minutes < 10) freshnessClass = "urgent";
        else if (task.freshness_minutes < 30) freshnessClass = "very-fresh";
        else if (task.freshness_minutes < 60) freshnessClass = "fresh";
        else if (task.freshness_minutes < 180) freshnessClass = "ok";
        else if (task.freshness_minutes < 360) freshnessClass = "hurry";

        return `
            <div class="post-card task-card ${task.task_category}">
                <div class="post-header">
                    <a class="post-title" href="${task.url}" target="_blank">${escapeHtml(task.title)}</a>
                    <span class="post-badge ${task.task_category}">${categoryLabel}</span>
                </div>
                <div class="task-freshness-row">
                    <span class="freshness-badge ${freshnessClass}">${freshness}</span>
                    ${budgetStr ? `<span class="budget-badge">Budget: ${budgetStr}</span>` : ""}
                    <span class="subreddit-badge">r/${task.subreddit}</span>
                    ${task.author ? `<span class="author-badge">u/${escapeHtml(task.author)}</span>` : ""}
                </div>
                ${textPreview ? `<div class="post-text">${escapeHtml(textPreview)}</div>` : ""}
                <div class="post-meta">
                    <span>↑ ${task.score}</span>
                    <span>💬 ${task.num_comments}</span>
                    <span>
                        Match
                        <span class="confidence-bar">
                            <span class="confidence-fill ${confLevel}" style="width:${task.confidence * 100}%"></span>
                        </span>
                        ${Math.round(task.confidence * 100)}%
                    </span>
                    <span>Skills: ${task.skill_score}${task.danger_score > 0 ? ` | Danger: ${task.danger_score}` : ""}</span>
                </div>
            </div>
        `;
    }).join("");
}

function filterTasks(category, tabEl) {
    document.querySelectorAll("#taskFilters .tab").forEach(t => t.classList.remove("active"));
    tabEl.classList.add("active");

    if (category === "all") {
        renderTasks(allTasks);
    } else {
        renderTasks(allTasks.filter(t => t.task_category === category));
    }
}

// ========== Scheduler Controls ==========

async function startScheduler() {
    try {
        const res = await fetch(`${API_BASE}/api/scheduler/start`, { method: "POST" });
        const data = await res.json();
        alert(`Auto-scan ${data.status}. Interval: ${data.interval_minutes || "?"} minutes.`);
    } catch (err) {
        alert("Failed to start scheduler: " + err.message);
    }
}

async function stopScheduler() {
    try {
        const res = await fetch(`${API_BASE}/api/scheduler/stop`, { method: "POST" });
        const data = await res.json();
        alert(`Auto-scan ${data.status}.`);
    } catch (err) {
        alert("Failed to stop scheduler: " + err.message);
    }
}

async function scanNowAndNotify() {
    const btn = document.querySelector(".scheduler-btn.notify");
    btn.disabled = true;
    btn.textContent = "Scanning...";

    try {
        const res = await fetch(`${API_BASE}/api/tasks/scan-now`, { method: "POST" });
        const data = await res.json();
        let msg = `Scanned ${data.total_scanned} posts. Found ${data.new_matches} new matches.`;
        if (data.notified) msg += " Telegram notification sent!";
        else if (data.new_matches > 0) msg += " (Telegram not configured)";
        alert(msg);

        if (data.posts && data.posts.length > 0) {
            allTasks = data.posts;
            renderTaskStats({
                total: data.posts.length,
                skill_match: data.posts.filter(p => p.task_category === "skill_match").length,
                maybe_match: data.posts.filter(p => p.task_category === "maybe_match").length,
                irrelevant: 0,
                danger: 0,
            });
            renderTasks(allTasks);
        }
    } catch (err) {
        alert("Scan failed: " + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Scan & Notify";
    }
}

// ========== Utilities ==========

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
