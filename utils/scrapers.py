import feedparser
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import json

# 时区常量
TZ_UTC8 = timezone(timedelta(hours=8))


def parse_rss(url, seen_checker, skip_time):
    """通用 RSS 解析"""
    feed = feedparser.parse(url)
    author = feed.feed.get("title", "Unknown")
    new_articles = []

    for entry in feed.entries[::-1]:  # 倒序
        link = entry.get("link")
        if seen_checker(link):
            continue

        # 处理时间 (尝试多种格式，这里简化逻辑)
        published_raw = entry.get("published")
        try:
            # 针对不同 RSS 源可能需要不同解析，这里复用你原来的逻辑
            if "T" in published_raw and "Z" in published_raw:
                published = (
                    datetime.strptime(published_raw, "%Y-%m-%dT%H:%M:%SZ")
                    .replace(tzinfo=timezone.utc)
                    .astimezone(TZ_UTC8)
                )
            else:
                # 简单的容错，具体根据源调整
                published = datetime.now(TZ_UTC8)
        except:
            published = datetime.now(TZ_UTC8)

        if published.timestamp() < skip_time:
            continue

        summary = (entry.get("summary") or "")[:100] + "..."
        new_articles.append(
            {
                "title": entry.get("title"),
                "link": link,
                "time": published.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": summary,
            }
        )
    return author, new_articles


def parse_luogu(uid, data_manager, skip_time):
    """洛谷解析逻辑"""
    result_articles = []
    scraper = cloudscraper.create_scraper()

    last_seen_count = data_manager.get_luogu_count(uid)
    start_page = last_seen_count // 10 + 1

    first_url = f"https://www.luogu.com.cn/user/{uid}/article?page=1&ascending=true"
    try:
        r = scraper.get(first_url)
        if r.status_code != 200:
            return "Luogu Error", []

        soup = BeautifulSoup(r.text, "html.parser")
        script_tag = soup.find("script", id="lentille-context")
        if not script_tag:
            return "Luogu Error", []

        data = json.loads(script_tag.string)

        per_page = data["data"]["articles"]["perPage"]
        total_count = data["data"]["articles"]["count"]
        author_name = data["data"]["user"]["name"]

        # 更新计数
        data_manager.set_luogu_count(uid, total_count)

        if total_count == last_seen_count:
            return f"{author_name} 的洛谷专栏", []

        end_page = (total_count + per_page - 1) // per_page

        # 翻页爬取
        for page in range(start_page, end_page + 1):
            url = f"https://www.luogu.com.cn/user/{uid}/article?page={page}&ascending=true"
            r = scraper.get(url)
            data = json.loads(
                BeautifulSoup(r.text, "html.parser")
                .find("script", id="lentille-context")
                .string
            )

            for a in data["data"]["articles"]["result"]:
                link = f"https://www.luogu.com.cn/article/{a['lid']}"
                if data_manager.is_url_seen(link):
                    continue

                # 标记为已读
                data_manager.add_url(link)

                pub_time = datetime.fromtimestamp(a["time"], tz=TZ_UTC8)
                if pub_time.timestamp() < skip_time:
                    continue

                result_articles.append(
                    {
                        "title": a["title"],
                        "link": link,
                        "time": pub_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "summary": a["content"][:100],
                    }
                )

        return f"{author_name} 的洛谷专栏", result_articles

    except Exception as e:
        print(f"Luogu scrape error for {uid}: {e}")
        return "Error", []
