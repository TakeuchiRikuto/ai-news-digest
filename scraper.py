"""RSSフィードからニュース記事を取得"""

import feedparser
import hashlib
import json
import os
from datetime import datetime, timedelta
from config import (
    RSS_FEEDS,
    MAX_ARTICLES_PER_FEED,
    MAX_TOTAL_ARTICLES,
    ARTICLE_MIN_LENGTH,
    OUTPUT_DIR,
)


def _article_id(title: str, link: str) -> str:
    """重複排除用のID生成"""
    return hashlib.md5(f"{title}{link}".encode()).hexdigest()


def _load_seen_ids(path: str) -> set:
    """過去に取得済みの記事IDを読み込む"""
    if os.path.exists(path):
        with open(path, "r") as f:
            return set(json.load(f))
    return set()


def _save_seen_ids(path: str, ids: set):
    """取得済み記事IDを保存（直近1000件のみ保持）"""
    limited = list(ids)[-1000:]
    with open(path, "w") as f:
        json.dump(limited, f)


def fetch_news(category: str = "tech") -> list[dict]:
    """
    指定カテゴリのRSSフィードからニュースを取得。
    重複排除済み、新しい記事のみ返す。
    """
    feeds = RSS_FEEDS.get(category, RSS_FEEDS["tech"])
    seen_path = os.path.join(OUTPUT_DIR, "seen_articles.json")
    seen_ids = _load_seen_ids(seen_path)

    articles = []

    for feed_info in feeds:
        try:
            feed = feedparser.parse(feed_info["url"])
            count = 0

            for entry in feed.entries:
                if count >= MAX_ARTICLES_PER_FEED:
                    break

                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()

                # HTMLタグを簡易除去
                import re
                summary = re.sub(r"<[^>]+>", "", summary).strip()

                # ゴミフィルタ
                if len(title + summary) < ARTICLE_MIN_LENGTH:
                    continue

                aid = _article_id(title, link)
                if aid in seen_ids:
                    continue

                # 日時パース
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_date = datetime(*published[:6]).strftime("%Y-%m-%d %H:%M")
                else:
                    pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")

                articles.append({
                    "id": aid,
                    "title": title,
                    "link": link,
                    "summary": summary[:500],  # 要約は500文字まで
                    "source": feed_info["name"],
                    "category": feed_info["category"],
                    "published": pub_date,
                })

                seen_ids.add(aid)
                count += 1

        except Exception as e:
            print(f"[WARN] {feed_info['name']} の取得に失敗: {e}")
            continue

    # 新しい順にソート、上限まで
    articles.sort(key=lambda a: a["published"], reverse=True)
    articles = articles[:MAX_TOTAL_ARTICLES]

    # 取得済みID更新
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    _save_seen_ids(seen_path, seen_ids)

    print(f"[INFO] {len(articles)}件の新着記事を取得 (カテゴリ: {category})")
    return articles


if __name__ == "__main__":
    articles = fetch_news("tech")
    for a in articles:
        print(f"  [{a['source']}] {a['title']}")
