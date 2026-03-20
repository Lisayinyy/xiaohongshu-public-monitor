#!/usr/bin/env python3
"""
小红书搜索脚本 - 基于 Playwright 持久化浏览器
特点：
  - 用浏览器内置登录态，登录一次永久有效
  - 支持滚动翻页，突破22条限制
  - 支持时间筛选+排序
  - headless 模式，不弹窗

用法：
  # 首次登录（会弹窗，扫码后关闭）
  python3 xhs_search_playwright.py login

  # 搜索（headless，不弹窗）
  python3 xhs_search_playwright.py search "MiniMax" --scroll 5
  
  # 批量搜索多个关键词
  python3 xhs_search_playwright.py batch "MiniMax" "大模型 对比" "AI模型 测评" "国产AI 排名" --scroll 5
"""

import json, sys, time, argparse, datetime, os
from playwright.sync_api import sync_playwright

# 浏览器数据目录（持久化登录态）
BROWSER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "browser_data")


def get_context(playwright, headless=True):
    """获取持久化浏览器上下文"""
    os.makedirs(BROWSER_DATA_DIR, exist_ok=True)
    
    # 始终用完整 Chrome（不是 headless-shell），保证 browser_data 兼容
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    context = playwright.chromium.launch_persistent_context(
        BROWSER_DATA_DIR,
        headless=headless,
        executable_path=chrome_path,
        viewport={"width": 1440, "height": 900},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        args=["--disable-blink-features=AutomationControlled"]
    )
    return context


def do_login():
    """打开浏览器让用户扫码登录（有窗口）"""
    print("🔐 打开浏览器，请扫码登录小红书...", file=sys.stderr)
    
    with sync_playwright() as p:
        context = get_context(p, headless=False)
        page = context.new_page()
        page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=30000)
        
        print("  浏览器已打开，请在页面上扫码登录", file=sys.stderr)
        print("  登录成功后，在终端按回车继续...", file=sys.stderr)
        input()
        
        context.close()
    
    print("✅ 登录完成，后续搜索将自动使用此登录态", file=sys.stderr)


def close_popups(page):
    """关闭小红书的各种弹窗"""
    try:
        page.evaluate("""() => {
            // 移除遮罩层
            document.querySelectorAll('.reds-mask, [class*="mask"]').forEach(el => el.remove());
            // 点击关闭按钮
            document.querySelectorAll('[aria-label="关闭"], .close-button, [class*="close-icon"]').forEach(btn => {
                try { btn.click(); } catch(e) {}
            });
            // 移除弹窗容器
            document.querySelectorAll('[class*="modal"], [class*="dialog"], [class*="popup"]').forEach(el => el.remove());
        }""")
    except:
        pass


def extract_notes(page):
    """从页面提取笔记数据"""
    return page.evaluate("""() => {
        const results = [];
        const seen = new Set();
        
        // 获取所有笔记链接
        const links = document.querySelectorAll('a[href*="/explore/"], a[href*="/search_result/"]');
        
        links.forEach(link => {
            try {
                const href = link.href || '';
                const match = href.match(/explore\\/([a-f0-9]{24})/);
                if (!match) return;
                
                const feedId = match[1];
                if (seen.has(feedId)) return;
                seen.add(feedId);
                
                // 找到包含此链接的笔记卡片
                const card = link.closest('section') || link.closest('[class*="note"]') || link.parentElement;
                if (!card) return;
                
                // 提取标题
                const titleEl = card.querySelector('.title, span.title, .note-title, a .title');
                const title = titleEl ? titleEl.textContent.trim() : '';
                
                // 提取作者
                const authorEl = card.querySelector('.author-wrapper .name, .author .name, [class*="author"] .name, .name');
                const author = authorEl ? authorEl.textContent.trim() : '';
                
                // 提取点赞数（在 like-wrapper 下的 span.count）
                const likeEl = card.querySelector('.like-wrapper .count, span.count');
                let likesText = likeEl ? likeEl.textContent.trim() : '0';
                
                if (title || author) {
                    results.push({
                        feed_id: feedId,
                        title: title,
                        author: author,
                        likes_text: likesText,
                        url: 'https://www.xiaohongshu.com/explore/' + feedId
                    });
                }
            } catch(e) {}
        });
        
        return results;
    }""")


def search_keyword(context, keyword, scroll_times=5, time_filter="一天内", sort_by="最多点赞"):
    """搜索单个关键词"""
    results = []
    seen_ids = set()
    
    page = context.new_page()
    
    try:
        # 通过 URL 参数设置排序（time_descending=按最新，likes_descending=按点赞）
        sort_map = {"综合": "general_v2", "最新": "time_descending", "最多点赞": "likes_descending"}
        sort_param = sort_map.get(sort_by, "time_descending")
        url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes&sort={sort_param}&ext_flags=1"
        
        print(f"\n🔍 搜索: {keyword} | {sort_by} | {time_filter}", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        
        # 关闭弹窗
        close_popups(page)
        time.sleep(1)
        
        # 检查登录状态
        content = page.content()
        if "登录后查看搜索结果" in content:
            print("❌ 未登录，请先运行: python3 xhs_search_playwright.py login", file=sys.stderr)
            page.close()
            return []
        
        # 滚动并收集
        for i in range(scroll_times + 1):
            close_popups(page)
            
            cards = extract_notes(page)
            new_count = 0
            
            for card in cards:
                fid = card.get("feed_id", "")
                if fid and fid not in seen_ids:
                    seen_ids.add(fid)
                    
                    # 解析点赞数
                    likes_text = card.get("likes_text", "0")
                    try:
                        if "万" in likes_text:
                            likes = int(float(likes_text.replace("万", "")) * 10000)
                        elif likes_text.isdigit():
                            likes = int(likes_text)
                        else:
                            likes = 0
                    except:
                        likes = 0
                    
                    # 解码发布时间
                    try:
                        ts = int(fid[:8], 16)
                        publish_dt = datetime.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")
                        publish_ts_ms = ts * 1000
                    except:
                        publish_dt = ""
                        publish_ts_ms = 0
                    
                    results.append({
                        "feed_id": fid,
                        "title": card.get("title", ""),
                        "author": card.get("author", ""),
                        "likes": likes,
                        "publish_dt": publish_dt,
                        "publish_ts": publish_ts_ms,
                        "url": card.get("url", ""),
                        "keyword": keyword
                    })
                    new_count += 1
            
            print(f"  滚动 {i}/{scroll_times} | +{new_count} 新帖 | 累计 {len(results)} 条", file=sys.stderr)
            
            if i < scroll_times:
                page.evaluate("window.scrollBy(0, 1500)")
                time.sleep(2.5)
        
        print(f"  ✅ {keyword}: 共 {len(results)} 条", file=sys.stderr)
        
    except Exception as e:
        print(f"  ❌ 搜索失败: {e}", file=sys.stderr)
    finally:
        page.close()
    
    return results


def batch_search(keywords, scroll_times=5, time_filter="一天内", sort_by="最多点赞", headless=True):
    """批量搜索多个关键词"""
    all_results = []
    
    with sync_playwright() as p:
        context = get_context(p, headless=headless)
        
        for kw in keywords:
            results = search_keyword(context, kw, scroll_times, time_filter, sort_by)
            all_results.extend(results)
            time.sleep(3)
        
        context.close()
    
    # 去重
    seen = set()
    unique = []
    for r in all_results:
        if r["feed_id"] not in seen:
            seen.add(r["feed_id"])
            unique.append(r)
    
    # 按点赞排序
    unique.sort(key=lambda x: x["likes"], reverse=True)
    
    print(f"\n{'='*50}", file=sys.stderr)
    print(f"📊 总计: {len(all_results)} 条 → 去重后 {len(unique)} 条", file=sys.stderr)
    
    return unique


def main():
    parser = argparse.ArgumentParser(description="小红书搜索 (Playwright 持久化浏览器)")
    subparsers = parser.add_subparsers(dest="command")
    
    # login 命令
    subparsers.add_parser("login", help="扫码登录（仅首次需要）")
    
    # search 命令
    search_p = subparsers.add_parser("search", help="搜索单个关键词")
    search_p.add_argument("keyword", help="搜索关键词")
    search_p.add_argument("--scroll", type=int, default=5, help="滚动次数（默认5）")
    search_p.add_argument("--time", default="一天内", help="时间筛选")
    search_p.add_argument("--sort", default="最多点赞", help="排序方式")
    search_p.add_argument("--no-headless", action="store_true", help="显示浏览器")
    
    # batch 命令
    batch_p = subparsers.add_parser("batch", help="批量搜索多个关键词")
    batch_p.add_argument("keywords", nargs="+", help="关键词列表")
    batch_p.add_argument("--scroll", type=int, default=5, help="滚动次数")
    batch_p.add_argument("--time", default="一天内", help="时间筛选")
    batch_p.add_argument("--sort", default="最多点赞", help="排序方式")
    batch_p.add_argument("--no-headless", action="store_true", help="显示浏览器")
    
    args = parser.parse_args()
    
    if args.command == "login":
        do_login()
    elif args.command == "search":
        with sync_playwright() as p:
            context = get_context(p, headless=not args.no_headless)
            results = search_keyword(context, args.keyword, args.scroll, args.time, args.sort)
            context.close()
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.command == "batch":
        results = batch_search(args.keywords, args.scroll, args.time, args.sort, headless=not args.no_headless)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
