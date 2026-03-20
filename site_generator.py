"""静的サイトジェネレーター - 日々の記事出力から完全な静的サイトを構築"""

import glob
import json
import math
import os
import shutil
from datetime import datetime
from jinja2 import Template

from config import (
    SITE_NAME,
    SITE_URL,
    SITE_DESCRIPTION,
    SITE_DIR,
    OUTPUT_DIR,
    ARTICLES_PER_PAGE,
    ADSENSE_CLIENT_ID,
    AFFILIATE_LINKS,
)
from publisher import COMMON_CSS, _adsense_head, _adsense_unit, _nav_html


def _load_all_articles() -> list[dict]:
    """outputディレクトリから全日の記事JSONデータを読み込む"""
    articles = []
    # news_YYYY-MM-DD.html に対応する生データを探す
    # summarizer出力をJSON保存していない場合、HTMLから復元するのは困難
    # → JSONデータファイルを探す。なければHTMLのメタデータから最低限を復元
    json_pattern = os.path.join(OUTPUT_DIR, "news_*.json")
    for path in sorted(glob.glob(json_pattern), reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            articles.append(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[WARN] {path} の読み込みに失敗: {e}")
    return articles


def _save_article_json(data: dict):
    """パイプライン出力をJSONとしても保存（同日データはマージ）"""
    filepath = os.path.join(OUTPUT_DIR, f"news_{data['date']}.json")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # 既存記事IDのセット
        existing_ids = {a.get("id") for a in existing.get("articles", [])}
        # 新規記事のみ追加
        for a in data.get("articles", []):
            if a.get("id") not in existing_ids:
                existing["articles"].append(a)
        # メタデータ更新
        existing["headline"] = data.get("headline", existing.get("headline", ""))
        existing["daily_digest"] = existing.get("daily_digest", "") + "\n\n" + data.get("daily_digest", "")
        existing["daily_digest"] = existing["daily_digest"].strip()
        existing["sns_post"] = data.get("sns_post", existing.get("sns_post", ""))
        existing["cost_usd"] = existing.get("cost_usd", 0) + data.get("cost_usd", 0)
        existing["tokens"] = {
            "input": existing.get("tokens", {}).get("input", 0) + data.get("tokens", {}).get("input", 0),
            "output": existing.get("tokens", {}).get("output", 0) + data.get("tokens", {}).get("output", 0),
        }
        # 重要度で再ソート
        existing["articles"].sort(key=lambda x: x.get("importance", 3), reverse=True)
        data = existing

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


# ─── トップページテンプレート ───
INDEX_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site_name }} - {{ site_description }}</title>
    <meta name="description" content="{{ site_description }}">
    <link rel="canonical" href="{{ site_url }}/">
    <meta property="og:title" content="{{ site_name }}">
    <meta property="og:description" content="{{ site_description }}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ site_url }}/">
    <meta property="og:site_name" content="{{ site_name }}">
    <meta property="og:locale" content="ja_JP">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{{ site_name }}">
    <meta name="twitter:description" content="{{ site_description }}">
    <meta name="robots" content="index, follow">
    <link rel="alternate" type="application/rss+xml" title="{{ site_name }}" href="{{ site_url }}/feed.xml">
    {{ adsense_head }}
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "{{ site_name }}",
        "url": "{{ site_url }}/",
        "description": "{{ site_description }}",
        "publisher": {"@type": "Organization", "name": "{{ site_name }}"}
    }
    </script>
    <style>{{ css }}
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 40px 30px; border-radius: 16px;
        margin-bottom: 30px; text-align: center;
    }
    .hero h1 { font-size: 1.8em; margin-bottom: 8px; }
    .hero p { opacity: 0.9; font-size: 1em; }
    .day-card {
        background: white; padding: 24px; border-radius: 12px;
        margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.06);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .day-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .day-card h2 { font-size: 1.15em; margin-bottom: 6px; }
    .day-card h2 a { color: #333; text-decoration: none; }
    .day-card h2 a:hover { color: #667eea; }
    .day-card .day-date { color: #667eea; font-weight: bold; font-size: 0.85em; margin-bottom: 8px; }
    .day-card .day-digest { color: #666; font-size: 0.92em; line-height: 1.6; }
    .day-card .day-count { color: #aaa; font-size: 0.8em; margin-top: 8px; }
    .pagination { text-align: center; margin: 30px 0; }
    .pagination a, .pagination span {
        display: inline-block; padding: 8px 14px; margin: 2px;
        border-radius: 8px; text-decoration: none; font-size: 0.9em;
    }
    .pagination a { background: white; color: #667eea; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .pagination a:hover { background: #667eea; color: white; }
    .pagination .current { background: #667eea; color: white; }
    @media (max-width: 600px) {
        .hero { padding: 25px 20px; }
        .hero h1 { font-size: 1.4em; }
    }
    </style>
</head>
<body>
    {{ nav }}
    <div class="container">
        <div class="hero">
            <h1>{{ site_name }}</h1>
            <p>{{ site_description }}</p>
        </div>

        {{ adsense_unit }}

        {% for day in days %}
        <div class="day-card">
            <div class="day-date">{{ day.date }}</div>
            <h2><a href="{{ site_url }}/articles/{{ day.date[:4] }}/{{ day.date[5:7] }}/{{ day.date[8:10] }}/">{{ day.headline }}</a></h2>
            <p class="day-digest">{{ day.daily_digest[:200] }}{% if day.daily_digest|length > 200 %}...{% endif %}</p>
            <p class="day-count">{{ day.article_count }}件の記事</p>
        </div>
        {% if loop.index == 3 %}
        {{ affiliate_mid }}
        {% endif %}
        {% if loop.index == 6 %}
        {{ adsense_unit_mid }}
        {% endif %}
        {% endfor %}

        {% if total_pages > 1 %}
        <div class="pagination">
            {% if current_page > 1 %}
            <a href="{{ site_url }}/{% if current_page > 2 %}page/{{ current_page - 1 }}/{% endif %}">&laquo; 前へ</a>
            {% endif %}
            {% for p in range(1, total_pages + 1) %}
                {% if p == current_page %}
                <span class="current">{{ p }}</span>
                {% else %}
                <a href="{{ site_url }}/{% if p > 1 %}page/{{ p }}/{% endif %}">{{ p }}</a>
                {% endif %}
            {% endfor %}
            {% if current_page < total_pages %}
            <a href="{{ site_url }}/page/{{ current_page + 1 }}/">次へ &raquo;</a>
            {% endif %}
        </div>
        {% endif %}

        {{ affiliate_bottom }}

        <footer class="site-footer">
            <div class="footer-links">
                <a href="{{ site_url }}/">トップ</a>
                <a href="{{ site_url }}/privacy/">プライバシーポリシー</a>
                <a href="{{ site_url }}/contact/">お問い合わせ</a>
                <a href="{{ site_url }}/feed.xml">RSS</a>
                <a href="{{ site_url }}/sitemap.xml">サイトマップ</a>
            </div>
            <p>{{ site_description }}</p>
            <p>&copy; {{ year }} {{ site_name }}</p>
        </footer>
    </div>
</body>
</html>""")


# ─── 記事ページテンプレート ───
ARTICLE_PAGE_TEMPLATE = Template("""<!DOCTYPE html>
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

        {% if related %}
        <section class="related-section">
            <h2>過去のニュースダイジェスト</h2>
            <ul class="related-list">
            {% for r in related %}
                <li>
                    <a href="{{ site_url }}/articles/{{ r.date[:4] }}/{{ r.date[5:7] }}/{{ r.date[8:10] }}/">{{ r.headline }}</a>
                    <span class="related-date">{{ r.date }}</span>
                </li>
            {% endfor %}
            </ul>
        </section>
        {% endif %}

        <footer class="site-footer">
            <div class="footer-links">
                <a href="{{ site_url }}/">トップ</a>
                <a href="{{ site_url }}/privacy/">プライバシーポリシー</a>
                <a href="{{ site_url }}/contact/">お問い合わせ</a>
                <a href="{{ site_url }}/feed.xml">RSS</a>
            </div>
            <p>このニュースダイジェストはAIによって自動生成されています。</p>
            <p>各記事の詳細は出典リンクからご確認ください。</p>
            <p>&copy; {{ date[:4] }} {{ site_name }}</p>
        </footer>
    </div>
</body>
</html>""")


# ─── カテゴリページテンプレート ───
CATEGORY_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ category_name }} - {{ site_name }}</title>
    <meta name="description" content="{{ site_name }}の{{ category_name }}カテゴリの記事一覧">
    <link rel="canonical" href="{{ canonical_url }}">
    <meta property="og:title" content="{{ category_name }} - {{ site_name }}">
    <meta property="og:description" content="{{ site_name }}の{{ category_name }}カテゴリの記事一覧">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ canonical_url }}">
    <meta property="og:locale" content="ja_JP">
    <meta name="robots" content="index, follow">
    {{ adsense_head }}
    <style>{{ css }}
    .category-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 30px; border-radius: 12px;
        margin-bottom: 30px; text-align: center;
    }
    .category-header h1 { font-size: 1.5em; }
    .category-article {
        background: white; padding: 16px 20px; border-radius: 10px;
        margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .category-article h3 { font-size: 1em; margin-bottom: 4px; }
    .category-article h3 a { color: #333; text-decoration: none; }
    .category-article h3 a:hover { color: #667eea; }
    .category-article .meta { font-size: 0.82em; }
    </style>
</head>
<body>
    {{ nav }}
    <div class="container">
        <div class="category-header">
            <h1>{{ category_name }}</h1>
        </div>

        {{ adsense_unit }}

        {% for article in articles %}
        <div class="category-article">
            <h3><a href="{{ article.source_link }}" target="_blank" rel="noopener">{{ article.title }}</a></h3>
            <div class="meta">
                <span class="source">{{ article.source }}</span> ・ {{ article.published }}
                ・ <a href="{{ site_url }}/articles/{{ article.day_date[:4] }}/{{ article.day_date[5:7] }}/{{ article.day_date[8:10] }}/" style="color:#667eea;text-decoration:none;">ダイジェストを読む</a>
            </div>
            <p style="font-size:0.9em;color:#555;margin-top:4px;">{{ article.ai_summary[:150] }}{% if article.ai_summary|length > 150 %}...{% endif %}</p>
        </div>
        {% if loop.index == 5 %}
        {{ affiliate_mid }}
        {% endif %}
        {% endfor %}

        {% if not articles %}
        <p style="text-align:center;color:#888;padding:40px;">このカテゴリにはまだ記事がありません。</p>
        {% endif %}

        {{ affiliate_bottom }}

        <footer class="site-footer">
            <div class="footer-links">
                <a href="{{ site_url }}/">トップ</a>
                <a href="{{ site_url }}/privacy/">プライバシーポリシー</a>
                <a href="{{ site_url }}/contact/">お問い合わせ</a>
                <a href="{{ site_url }}/feed.xml">RSS</a>
            </div>
            <p>&copy; {{ year }} {{ site_name }}</p>
        </footer>
    </div>
</body>
</html>""")


# ─── 固定ページテンプレート ───
STATIC_PAGE_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }} - {{ site_name }}</title>
    <meta name="description" content="{{ page_description }}">
    <link rel="canonical" href="{{ canonical_url }}">
    <meta property="og:title" content="{{ page_title }} - {{ site_name }}">
    <meta property="og:description" content="{{ page_description }}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{{ canonical_url }}">
    <meta property="og:site_name" content="{{ site_name }}">
    <meta property="og:locale" content="ja_JP">
    <meta name="robots" content="index, follow">
    {{ adsense_head }}
    <style>{{ css }}
    .static-page-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 30px; border-radius: 12px;
        margin-bottom: 30px; text-align: center;
    }
    .static-page-header h1 { font-size: 1.5em; }
    .static-page-content {
        background: white; padding: 30px; border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06); line-height: 1.9;
    }
    .static-page-content h2 {
        color: #667eea; font-size: 1.15em; margin-top: 28px; margin-bottom: 10px;
        padding-bottom: 6px; border-bottom: 2px solid #e8eaf6;
    }
    .static-page-content h2:first-child { margin-top: 0; }
    .static-page-content p { margin-bottom: 12px; font-size: 0.95em; color: #444; }
    .static-page-content ul { margin: 8px 0 16px 20px; font-size: 0.95em; color: #444; }
    .static-page-content ul li { margin-bottom: 4px; }
    .static-page-content a { color: #667eea; }
    .contact-btn {
        display: inline-block; background: #667eea; color: white !important;
        padding: 12px 28px; border-radius: 8px; text-decoration: none;
        font-weight: bold; margin-top: 10px; transition: background 0.2s;
    }
    .contact-btn:hover { background: #5a6fd6; }
    </style>
</head>
<body>
    {{ nav }}
    <div class="container">
        <div class="static-page-header">
            <h1>{{ page_title }}</h1>
        </div>

        <div class="static-page-content">
            {{ content }}
        </div>

        <footer class="site-footer">
            <div class="footer-links">
                <a href="{{ site_url }}/">トップ</a>
                <a href="{{ site_url }}/privacy/">プライバシーポリシー</a>
                <a href="{{ site_url }}/contact/">お問い合わせ</a>
                <a href="{{ site_url }}/feed.xml">RSS</a>
                <a href="{{ site_url }}/sitemap.xml">サイトマップ</a>
            </div>
            <p>&copy; {{ year }} {{ site_name }}</p>
        </footer>
    </div>
</body>
</html>""")


PRIVACY_POLICY_CONTENT = f"""
<h2>個人情報の取り扱いについて</h2>
<p>当サイト（{SITE_NAME}）（以下「当サイト」）は、ユーザーの個人情報の取り扱いについて、以下の通りプライバシーポリシーを定めます。</p>

<h2>収集する情報</h2>
<p>当サイトでは、お問い合わせの際にお名前、メールアドレス等の個人情報をご提供いただく場合があります。これらの情報は、お問い合わせへの回答およびご連絡のためにのみ使用し、それ以外の目的では利用いたしません。</p>

<h2>Cookie（クッキー）について</h2>
<p>当サイトでは、ユーザーの利便性向上およびアクセス解析のためにCookieを使用する場合があります。Cookieとは、ウェブサイトがユーザーのブラウザに保存する小さなテキストファイルです。</p>
<p>ブラウザの設定により、Cookieの受け入れを拒否することが可能ですが、その場合、サイトの一部機能が正常に動作しない可能性があります。</p>

<h2>アクセス解析ツールについて</h2>
<p>当サイトでは、Googleによるアクセス解析ツール「Google Analytics」を使用する場合があります。Google Analyticsはトラフィックデータの収集のためにCookieを使用しています。このトラフィックデータは匿名で収集されており、個人を特定するものではありません。</p>
<p>この機能はCookieを無効にすることで収集を拒否することができますので、お使いのブラウザの設定をご確認ください。Google Analyticsの利用規約については、<a href="https://marketingplatform.google.com/about/analytics/terms/jp/" target="_blank" rel="noopener">Google アナリティクス利用規約</a>をご覧ください。</p>

<h2>広告配信について（Google AdSense）</h2>
<p>当サイトでは、第三者配信の広告サービス「Google AdSense」を利用する場合があります。広告配信事業者は、ユーザーの興味に応じた商品やサービスの広告を表示するために、当サイトや他のサイトへのアクセスに関する情報（氏名、住所、メールアドレス、電話番号は含まれません）を使用することがあります。</p>
<p>詳細については、<a href="https://policies.google.com/technologies/ads?hl=ja" target="_blank" rel="noopener">Google 広告に関するポリシー</a>をご確認ください。</p>

<h2>アフィリエイトリンクについて</h2>
<p>当サイトでは、Amazon.co.jpアソシエイト、A8.net、もしもアフィリエイトなどのアフィリエイトプログラムに参加しています。記事内にアフィリエイトリンクが含まれる場合があり、リンクを経由して商品を購入された場合、当サイトが報酬を受け取ることがあります。</p>
<p>アフィリエイトリンクは「PR」と明示しています。ユーザーが商品を購入される際の価格への影響はありません。</p>

<h2>AI生成コンテンツに関する免責事項</h2>
<p>当サイトの記事・ニュースダイジェストは、AIによって自動生成されています。コンテンツの正確性には細心の注意を払っておりますが、AI生成の性質上、情報に誤りが含まれる可能性があります。</p>
<ul>
    <li>記事の要約はAIによる自動要約であり、元記事の意図を完全に反映していない場合があります。</li>
    <li>正確な情報については、必ず各記事の出典リンクから元の記事をご確認ください。</li>
    <li>当サイトのコンテンツに基づいて行われた判断や行動について、当サイトは一切の責任を負いかねます。</li>
</ul>

<h2>プライバシーポリシーの変更</h2>
<p>当サイトは、必要に応じて本プライバシーポリシーを変更することがあります。変更後のプライバシーポリシーは、当ページに掲載した時点で効力を生じるものとします。</p>

<p style="margin-top:24px;color:#888;font-size:0.85em;">最終更新日: {datetime.now().strftime("%Y年%m月%d日")}</p>
"""


CONTACT_PAGE_CONTENT = f"""
<h2>お問い合わせ</h2>
<p>当サイト（{SITE_NAME}）へのお問い合わせは、以下の方法でご連絡ください。</p>

<h2>お問い合わせ方法</h2>
<p>以下のGoogleフォームまたはメールにてお問い合わせを受け付けております。</p>

<p style="text-align:center;margin:24px 0;">
    <a href="https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform" class="contact-btn" target="_blank" rel="noopener">
        Googleフォームでお問い合わせ
    </a>
</p>

<p style="text-align:center;color:#888;">または</p>

<p style="text-align:center;margin:16px 0;">
    <a href="mailto:your-email@example.com" class="contact-btn">
        メールでお問い合わせ
    </a>
</p>

<h2>お問い合わせの際のお願い</h2>
<ul>
    <li>お問い合わせの内容によっては、回答にお時間をいただく場合がございます。</li>
    <li>全てのお問い合わせに回答できない場合がございますので、あらかじめご了承ください。</li>
    <li>記事内容の誤りに関するご指摘は、該当記事のURLと合わせてお知らせください。</li>
</ul>

<h2>対応可能なお問い合わせ</h2>
<ul>
    <li>サイトの不具合や表示の問題について</li>
    <li>記事内容の誤りに関するご指摘</li>
    <li>広告掲載に関するお問い合わせ</li>
    <li>その他、当サイトに関するご意見・ご質問</li>
</ul>
"""


def _json_ld_article(data: dict, url: str) -> str:
    """記事ページ用JSON-LD"""
    ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": data.get("headline", ""),
        "datePublished": data.get("date", ""),
        "dateModified": data.get("date", ""),
        "description": data.get("daily_digest", "")[:200],
        "author": {"@type": "Organization", "name": SITE_NAME},
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    }
    return f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'


def build_site():
    """静的サイト全体を構築"""
    print("\n" + "=" * 50)
    print("🏗️  静的サイト構築中...")
    print("=" * 50)

    # サイトディレクトリ準備
    os.makedirs(SITE_DIR, exist_ok=True)

    # 全記事データ読み込み
    all_days = _load_all_articles()
    if not all_days:
        print("[INFO] 記事データがありません。先にパイプラインを実行してください。")
        return

    all_days.sort(key=lambda d: d.get("date", ""), reverse=True)
    print(f"  → {len(all_days)}日分の記事データを検出")

    # 共通テンプレート変数
    adsense_head = _adsense_head()
    adsense_unit = _adsense_unit()
    nav = _nav_html()
    year = datetime.now().strftime("%Y")
    affiliate_default = _get_affiliate_html(["default"])

    # ─── 1. 個別記事ページ生成 ───
    print("  📄 記事ページ生成中...")
    for i, day_data in enumerate(all_days):
        date = day_data.get("date", "")
        if not date:
            continue
        parts = date.split("-")
        if len(parts) != 3:
            continue

        article_dir = os.path.join(SITE_DIR, "articles", parts[0], parts[1], parts[2])
        os.makedirs(article_dir, exist_ok=True)

        # カテゴリ取得
        categories = list({a.get("category", "") for a in day_data.get("articles", [])})
        affiliate_html = _get_affiliate_html(categories) if categories else affiliate_default

        # 関連記事（前後5件）
        related = [d for j, d in enumerate(all_days) if j != i][:5]

        canonical_url = f"{SITE_URL}/articles/{parts[0]}/{parts[1]}/{parts[2]}/"

        html = ARTICLE_PAGE_TEMPLATE.render(
            headline=day_data.get("headline", "ニュースダイジェスト"),
            date=date,
            daily_digest=day_data.get("daily_digest", ""),
            articles=day_data.get("articles", []),
            affiliate_top=affiliate_html,
            affiliate_bottom=affiliate_html,
            affiliate_mid=affiliate_default,
            related=related,
            site_name=SITE_NAME,
            site_url=SITE_URL,
            canonical_url=canonical_url,
            css=COMMON_CSS,
            nav=nav,
            adsense_head=adsense_head,
            adsense_unit=adsense_unit,
            adsense_unit_mid=adsense_unit,
            json_ld=_json_ld_article(day_data, canonical_url),
        )

        with open(os.path.join(article_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    # ─── 2. トップページ（ページネーション付き） ───
    print("  🏠 トップページ生成中...")
    total_pages = max(1, math.ceil(len(all_days) / ARTICLES_PER_PAGE))

    for page in range(1, total_pages + 1):
        start = (page - 1) * ARTICLES_PER_PAGE
        end = start + ARTICLES_PER_PAGE
        page_days = all_days[start:end]

        # ページデータ整形
        day_items = []
        for d in page_days:
            day_items.append({
                "date": d.get("date", ""),
                "headline": d.get("headline", "ニュースダイジェスト"),
                "daily_digest": d.get("daily_digest", ""),
                "article_count": len(d.get("articles", [])),
            })

        html = INDEX_TEMPLATE.render(
            site_name=SITE_NAME,
            site_url=SITE_URL,
            site_description=SITE_DESCRIPTION,
            days=day_items,
            current_page=page,
            total_pages=total_pages,
            year=year,
            css=COMMON_CSS,
            nav=nav,
            adsense_head=adsense_head,
            adsense_unit=adsense_unit,
            adsense_unit_mid=adsense_unit,
            affiliate_mid=affiliate_default,
            affiliate_bottom=affiliate_default,
        )

        if page == 1:
            with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
                f.write(html)
        else:
            page_dir = os.path.join(SITE_DIR, "page", str(page))
            os.makedirs(page_dir, exist_ok=True)
            with open(os.path.join(page_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(html)

    # ─── 3. カテゴリページ生成 ───
    print("  📂 カテゴリページ生成中...")
    category_map = {
        "ai": {"name": "AI", "categories": ["AI", "AI(海外)"]},
        "tech": {"name": "テクノロジー", "categories": ["テクノロジー"]},
        "business": {"name": "ビジネス", "categories": ["ビジネス"]},
    }

    for cat_key, cat_info in category_map.items():
        cat_articles = []
        for day_data in all_days:
            for a in day_data.get("articles", []):
                if a.get("category", "") in cat_info["categories"]:
                    cat_articles.append({
                        **a,
                        "source_link": a.get("link", "#"),
                        "day_date": day_data.get("date", ""),
                    })

        cat_dir = os.path.join(SITE_DIR, "categories", cat_key)
        os.makedirs(cat_dir, exist_ok=True)

        canonical_url = f"{SITE_URL}/categories/{cat_key}/"
        cat_affiliate = _get_affiliate_html([cat_info["name"]])

        html = CATEGORY_TEMPLATE.render(
            category_name=cat_info["name"],
            articles=cat_articles[:50],
            site_name=SITE_NAME,
            site_url=SITE_URL,
            canonical_url=canonical_url,
            year=year,
            css=COMMON_CSS,
            nav=nav,
            adsense_head=adsense_head,
            adsense_unit=adsense_unit,
            affiliate_mid=cat_affiliate,
            affiliate_bottom=cat_affiliate,
        )

        with open(os.path.join(cat_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    # ─── 4. RSS feed.xml ───
    print("  📡 RSS フィード生成中...")
    _generate_feed_xml(all_days[:20])

    # ─── 5. sitemap.xml ───
    print("  🗺️  サイトマップ生成中...")
    _generate_sitemap(all_days, category_map)

    # ─── 6. robots.txt ───
    print("  🤖 robots.txt 生成中...")
    _generate_robots()

    # ─── 7. 固定ページ（プライバシーポリシー・お問い合わせ） ───
    print("  📋 固定ページ生成中...")
    _generate_static_pages(nav, adsense_head, year)

    # 完了
    page_count = len(all_days) + total_pages + len(category_map) + 3 + 2  # 記事+トップ+カテゴリ+feed+sitemap+robots+固定ページ
    print(f"\n✅ サイト構築完了！")
    print(f"  → {page_count}ページを生成")
    print(f"  → 出力先: {os.path.abspath(SITE_DIR)}")
    print(f"  → GitHub Pagesにデプロイするには docs/ をコミットしてください")


def _generate_static_pages(nav: str, adsense_head: str, year: str):
    """プライバシーポリシー・お問い合わせなどの固定ページを生成"""
    pages = [
        {
            "dir": "privacy",
            "title": "プライバシーポリシー",
            "description": f"{SITE_NAME}のプライバシーポリシー。個人情報の取り扱い、Cookie、広告、AI生成コンテンツについて。",
            "content": PRIVACY_POLICY_CONTENT,
        },
        {
            "dir": "contact",
            "title": "お問い合わせ",
            "description": f"{SITE_NAME}へのお問い合わせページ。",
            "content": CONTACT_PAGE_CONTENT,
        },
    ]

    for page in pages:
        page_dir = os.path.join(SITE_DIR, page["dir"])
        os.makedirs(page_dir, exist_ok=True)

        canonical_url = f"{SITE_URL}/{page['dir']}/"

        html = STATIC_PAGE_TEMPLATE.render(
            page_title=page["title"],
            page_description=page["description"],
            content=page["content"],
            site_name=SITE_NAME,
            site_url=SITE_URL,
            canonical_url=canonical_url,
            year=year,
            css=COMMON_CSS,
            nav=nav,
            adsense_head=adsense_head,
        )

        with open(os.path.join(page_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)


def _generate_feed_xml(days: list[dict]):
    """RSSフィード (feed.xml) を生成"""
    now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0900")
    items = ""
    for day_data in days:
        date = day_data.get("date", "")
        if not date:
            continue
        parts = date.split("-")
        url = f"{SITE_URL}/articles/{parts[0]}/{parts[1]}/{parts[2]}/"
        # RFC822 形式の日付
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            pub_date = dt.strftime("%a, %d %b %Y 07:00:00 +0900")
        except ValueError:
            pub_date = now

        desc = day_data.get("daily_digest", "")[:300]
        # XMLエスケープ
        desc = desc.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        headline = day_data.get("headline", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        items += f"""    <item>
      <title>{headline}</title>
      <link>{url}</link>
      <description>{desc}</description>
      <pubDate>{pub_date}</pubDate>
      <guid>{url}</guid>
    </item>
"""

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SITE_NAME}</title>
    <link>{SITE_URL}/</link>
    <description>{SITE_DESCRIPTION}</description>
    <language>ja</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{items}  </channel>
</rss>
"""
    with open(os.path.join(SITE_DIR, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(feed)


def _generate_sitemap(days: list[dict], category_map: dict):
    """sitemap.xmlを生成"""
    now = datetime.now().strftime("%Y-%m-%d")
    urls = []

    # トップページ
    urls.append(f"""  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")

    # 記事ページ
    for day_data in days:
        date = day_data.get("date", "")
        if not date:
            continue
        parts = date.split("-")
        urls.append(f"""  <url>
    <loc>{SITE_URL}/articles/{parts[0]}/{parts[1]}/{parts[2]}/</loc>
    <lastmod>{date}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>""")

    # カテゴリページ
    for cat_key in category_map:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/categories/{cat_key}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.6</priority>
  </url>""")

    # 固定ページ
    for static_page in ["privacy", "contact"]:
        urls.append(f"""  <url>
    <loc>{SITE_URL}/{static_page}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.4</priority>
  </url>""")

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""
    with open(os.path.join(SITE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap)


def _generate_robots():
    """robots.txtを生成"""
    robots = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    with open(os.path.join(SITE_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots)


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


if __name__ == "__main__":
    build_site()
