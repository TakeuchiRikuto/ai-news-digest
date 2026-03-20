"""記事をHTML・Markdown・SNS投稿用に変換"""

import json
import os
from datetime import datetime
from jinja2 import Template
from config import OUTPUT_DIR, AFFILIATE_LINKS, SITE_NAME, SITE_URL, SITE_DESCRIPTION, ADSENSE_CLIENT_ID


def _get_affiliate_html(categories: list[str]) -> str:
    """記事カテゴリに合ったアフィリエイトリンクをHTML化"""
    links = []
    seen = set()
    for cat in categories:
        for link in AFFILIATE_LINKS.get(cat, AFFILIATE_LINKS["default"]):
            if link["url"] not in seen:
                links.append(link)
                seen.add(link["url"])

    if not links:
        links = AFFILIATE_LINKS["default"]

    html = '<div class="affiliate-box">\n'
    html += '  <div class="affiliate-label">PR</div>\n'
    for link in links[:3]:
        html += f'  <a href="{link["url"]}" target="_blank" rel="noopener sponsored" class="affiliate-link">'
        html += f'{link["text"]}</a>\n'
        html += f'  <small class="affiliate-desc">{link["description"]}</small>\n'
    html += "</div>\n"
    return html


def _adsense_head() -> str:
    """AdSenseスクリプトタグ（IDが設定されている場合のみ）"""
    if ADSENSE_CLIENT_ID:
        return f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT_ID}" crossorigin="anonymous"></script>'
    return ""


def _adsense_unit() -> str:
    """AdSense広告ユニット挿入用HTML"""
    if ADSENSE_CLIENT_ID:
        return """<div class="ad-unit">
    <ins class="adsbygoogle" style="display:block" data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>"""
    return ""


def _json_ld(data: dict, article_url: str = "") -> str:
    """JSON-LD構造化データを生成"""
    ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": data["headline"],
        "datePublished": data["date"],
        "dateModified": data["date"],
        "description": data["daily_digest"][:200],
        "author": {
            "@type": "Organization",
            "name": SITE_NAME,
        },
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
        },
    }
    if article_url:
        ld["mainEntityOfPage"] = {"@type": "WebPage", "@id": article_url}
    return f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'


def _nav_html(current_date: str = "") -> str:
    """ナビゲーションHTML"""
    return f"""<nav class="site-nav">
    <a href="{SITE_URL}/" class="nav-home">{SITE_NAME}</a>
    <div class="nav-links">
        <a href="{SITE_URL}/">トップ</a>
        <a href="{SITE_URL}/categories/ai/">AI</a>
        <a href="{SITE_URL}/categories/tech/">テクノロジー</a>
        <a href="{SITE_URL}/categories/business/">ビジネス</a>
    </div>
</nav>"""


# ─── 共通CSSスタイル ───
COMMON_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, 'Hiragino Sans', 'Noto Sans JP', 'Segoe UI', sans-serif;
    background: #f5f7fa; color: #333;
    line-height: 1.8;
}
.container {
    max-width: 800px; margin: 0 auto; padding: 20px;
}
/* ナビゲーション */
.site-nav {
    background: #fff; padding: 12px 20px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); position: sticky; top: 0; z-index: 100;
}
.nav-home {
    font-weight: 700; font-size: 1.1em; color: #667eea;
    text-decoration: none;
}
.nav-links { display: flex; gap: 16px; }
.nav-links a {
    color: #555; text-decoration: none; font-size: 0.9em;
    padding: 4px 8px; border-radius: 6px; transition: background 0.2s;
}
.nav-links a:hover { background: #f0f0f5; color: #667eea; }
/* ヘッダー */
header.article-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 30px; border-radius: 12px;
    margin-bottom: 30px;
}
header.article-header h1 { font-size: 1.5em; margin-bottom: 10px; }
header.article-header .date { opacity: 0.8; font-size: 0.9em; }
/* ダイジェスト */
.digest {
    background: white; padding: 25px; border-radius: 12px;
    margin-bottom: 20px; border-left: 4px solid #667eea;
    box-shadow: 0 2px 4px rgba(0,0,0,0.06);
}
.digest h2 { color: #667eea; margin-bottom: 10px; font-size: 1.1em; }
/* 記事カード */
.article-card {
    background: white; padding: 20px; border-radius: 12px;
    margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    transition: transform 0.2s, box-shadow 0.2s;
}
.article-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.article-card h3 { font-size: 1.1em; margin-bottom: 8px; }
.article-card h3 a { color: #333; text-decoration: none; }
.article-card h3 a:hover { color: #667eea; }
.meta { color: #888; font-size: 0.85em; margin-bottom: 8px; }
.meta .source { color: #667eea; font-weight: bold; }
.meta .importance {
    display: inline-block; background: #667eea; color: white;
    padding: 2px 8px; border-radius: 10px; font-size: 0.75em;
}
.tags { margin-top: 10px; }
.tags span {
    display: inline-block; background: #e8eaf6;
    color: #667eea; padding: 3px 10px;
    border-radius: 15px; font-size: 0.8em; margin-right: 5px; margin-bottom: 4px;
}
/* アフィリエイト */
.affiliate-box {
    background: linear-gradient(135deg, #fff8e1 0%, #fff3e0 100%);
    padding: 20px; border-radius: 12px;
    margin: 25px 0; text-align: center;
    border: 1px solid #ffe0b2; position: relative;
}
.affiliate-label {
    position: absolute; top: -8px; left: 16px;
    background: #ff9800; color: white; font-size: 0.7em;
    padding: 1px 8px; border-radius: 4px; font-weight: bold;
}
.affiliate-link {
    display: inline-block; color: #e65100; font-weight: bold;
    text-decoration: none; font-size: 1.05em;
    padding: 8px 16px; margin: 4px;
    border-radius: 8px; background: rgba(255,255,255,0.7);
    transition: background 0.2s;
}
.affiliate-link:hover { background: rgba(255,255,255,1); }
.affiliate-desc { color: #888; display: block; margin-top: 2px; font-size: 0.8em; }
/* 広告 */
.ad-unit { margin: 25px 0; text-align: center; min-height: 90px; }
/* 関連記事 */
.related-section {
    background: white; padding: 25px; border-radius: 12px;
    margin: 25px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.06);
}
.related-section h2 { color: #667eea; margin-bottom: 15px; font-size: 1.1em; }
.related-list { list-style: none; }
.related-list li { padding: 8px 0; border-bottom: 1px solid #f0f0f5; }
.related-list li:last-child { border-bottom: none; }
.related-list a { color: #333; text-decoration: none; }
.related-list a:hover { color: #667eea; }
.related-list .related-date { color: #aaa; font-size: 0.8em; margin-left: 8px; }
/* フッター */
footer.site-footer {
    text-align: center; color: #888;
    padding: 30px 20px; font-size: 0.85em;
    border-top: 1px solid #e0e0e0; margin-top: 40px;
}
footer.site-footer a { color: #667eea; text-decoration: none; }
footer.site-footer .footer-links { margin-bottom: 10px; }
footer.site-footer .footer-links a { margin: 0 8px; }
/* レスポンシブ */
@media (max-width: 600px) {
    .container { padding: 10px; }
    header.article-header { padding: 20px; }
    header.article-header h1 { font-size: 1.2em; }
    .site-nav { flex-direction: column; gap: 8px; }
    .nav-links { gap: 8px; flex-wrap: wrap; justify-content: center; }
}
"""


# ─── HTMLブログ記事テンプレート ───
BLOG_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ headline }} - {{ site_name }} {{ date }}</title>
    <meta name="description" content="{{ daily_digest[:150] }}">
    <link rel="canonical" href="{{ canonical_url }}">
    <meta property="og:title" content="{{ headline }} - {{ site_name }}">
    <meta property="og:description" content="{{ daily_digest[:150] }}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{{ canonical_url }}">
    <meta property="og:site_name" content="{{ site_name }}">
    <meta property="og:locale" content="ja_JP">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{{ headline }} - {{ site_name }}">
    <meta name="twitter:description" content="{{ daily_digest[:150] }}">
    <meta name="robots" content="index, follow">
    {{ adsense_head }}
    {{ json_ld }}
    <style>{{ css }}</style>
</head>
<body>
    {{ nav }}

    <div class="container">
        <header class="article-header">
            <div class="date">{{ date }} のAIニュースダイジェスト</div>
            <h1>{{ headline }}</h1>
        </header>

        <section class="digest">
            <h2>今日のまとめ</h2>
            <p>{{ daily_digest }}</p>
        </section>

        {{ adsense_unit }}

        {{ affiliate_top }}

        {% for article in articles %}
        <article class="article-card">
            <h3>
                <a href="{{ article.link }}" target="_blank" rel="noopener">
                    {{ article.title }}
                </a>
            </h3>
            <div class="meta">
                <span class="source">{{ article.source }}</span>
                ・{{ article.published }}
                {% if article.importance >= 4 %}
                <span class="importance">注目</span>
                {% endif %}
            </div>
            <p>{{ article.ai_summary }}</p>
            <div class="tags">
                {% for tag in article.ai_tags %}
                <span>#{{ tag }}</span>
                {% endfor %}
            </div>
        </article>
        {% if loop.index == 5 %}
        {{ adsense_unit_mid }}
        {% endif %}
        {% endfor %}

        {{ affiliate_bottom }}

        {{ adsense_unit }}

        {{ related_html }}

        <footer class="site-footer">
            <div class="footer-links">
                <a href="{{ site_url }}/">トップ</a>
                <a href="{{ site_url }}/feed.xml">RSS</a>
            </div>
            <p>このニュースダイジェストはAIによって自動生成されています。</p>
            <p>各記事の詳細は出典リンクからご確認ください。</p>
            <p>&copy; {{ date[:4] }} {{ site_name }}</p>
        </footer>
    </div>
</body>
</html>""")


def publish_html(data: dict, related_articles: list[dict] | None = None) -> str:
    """HTMLブログ記事を生成して保存"""
    categories = list({a["category"] for a in data["articles"]})
    affiliate_html = _get_affiliate_html(categories)

    # 記事URL
    date_parts = data["date"].split("-")
    article_url = f"{SITE_URL}/articles/{date_parts[0]}/{date_parts[1]}/{date_parts[2]}/"

    # 関連記事HTML
    related_html = ""
    if related_articles:
        related_html = '<section class="related-section">\n<h2>過去のニュースダイジェスト</h2>\n<ul class="related-list">\n'
        for ra in related_articles[:5]:
            ra_parts = ra["date"].split("-")
            ra_url = f"{SITE_URL}/articles/{ra_parts[0]}/{ra_parts[1]}/{ra_parts[2]}/"
            related_html += f'<li><a href="{ra_url}">{ra["headline"]}</a><span class="related-date">{ra["date"]}</span></li>\n'
        related_html += '</ul>\n</section>'

    html = BLOG_TEMPLATE.render(
        headline=data["headline"],
        date=data["date"],
        daily_digest=data["daily_digest"],
        articles=data["articles"],
        affiliate_top=affiliate_html,
        affiliate_bottom=affiliate_html,
        site_name=SITE_NAME,
        site_url=SITE_URL,
        canonical_url=article_url,
        css=COMMON_CSS,
        nav=_nav_html(data["date"]),
        adsense_head=_adsense_head(),
        adsense_unit=_adsense_unit(),
        adsense_unit_mid=_adsense_unit(),
        json_ld=_json_ld(data, article_url),
        related_html=related_html,
    )

    filename = f"news_{data['date']}.html"
    filepath = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] HTML出力: {filepath}")
    return filepath


def publish_markdown(data: dict) -> str:
    """Markdown記事を生成（note.com投稿用など）"""
    md = f"# {data['headline']}\n\n"
    md += f"*{data['date']} のAIニュースダイジェスト*\n\n"
    md += f"## 今日のまとめ\n\n{data['daily_digest']}\n\n"
    md += "---\n\n"

    for a in data["articles"]:
        stars = "⭐ " if a["importance"] >= 4 else ""
        md += f"### {stars}{a['title']}\n\n"
        md += f"**{a['source']}** | {a['published']}\n\n"
        md += f"{a['ai_summary']}\n\n"
        md += f"[元記事を読む]({a['link']})\n\n"
        if a["ai_tags"]:
            md += " ".join(f"`#{tag}`" for tag in a["ai_tags"]) + "\n\n"
        md += "---\n\n"

    md += "*このニュースダイジェストはAIによって自動生成されています。*\n"
    md += "*各記事の詳細は出典リンクからご確認ください。*\n"

    filename = f"news_{data['date']}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[INFO] Markdown出力: {filepath}")
    return filepath


def publish_sns(data: dict) -> dict:
    """SNS投稿用テキストを生成"""
    # X/Twitter用（280文字以内）
    twitter = data.get("sns_post", "")
    if not twitter:
        twitter = f"📰 {data['headline']}\n\n"
        for a in data["articles"][:3]:
            twitter += f"・{a['title'][:40]}\n"
        twitter += "\n#AIニュース #テックニュース"

    # Threads/Instagram用（もう少し長くてOK）
    threads = f"📰 {data['date']} AIニュースダイジェスト\n\n"
    threads += f"💡 {data['headline']}\n\n"
    for a in data["articles"][:5]:
        threads += f"▶ {a['title'][:50]}\n"
        threads += f"  {a['ai_summary'][:80]}...\n\n"
    threads += "詳しくはプロフのリンクから！\n"
    threads += "#AIニュース #テクノロジー #最新ニュース"

    sns = {"twitter": twitter[:280], "threads": threads}

    filepath = os.path.join(OUTPUT_DIR, f"sns_{data['date']}.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sns, f, indent=2, ensure_ascii=False)

    print(f"[INFO] SNS投稿文出力: {filepath}")
    return sns
