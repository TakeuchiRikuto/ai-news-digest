"""設定ファイル - RSSフィード、APIモデル、コスト管理、サイト設定"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Claude API ───
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Haikuが最もコスパ良い（入力$0.80/1M、出力$4.00/1M）
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 4096

# ─── サイト設定 ───
SITE_NAME = "AI News Digest"
SITE_URL = os.getenv("SITE_URL", "https://takeuchirikuto.github.io/ai-news-digest")
SITE_DESCRIPTION = "AIが厳選・要約する最新テクノロジーニュース"
SITE_DIR = os.getenv("SITE_DIR", "./docs")  # GitHub Pages用
ARTICLES_PER_PAGE = 10

# ─── Google AdSense ───
ADSENSE_CLIENT_ID = os.getenv("ADSENSE_CLIENT_ID", "")  # ca-pub-XXXXX

# ─── RSSフィード設定 ───
RSS_FEEDS = {
    "tech": [
        {
            "name": "NHK 科学・文化",
            "url": "https://www.nhk.or.jp/rss/news/cat3.xml",
            "category": "テクノロジー",
        },
        {
            "name": "ITmedia NEWS",
            "url": "https://rss.itmedia.co.jp/rss/2.0/itmedia_news.xml",
            "category": "テクノロジー",
        },
        {
            "name": "GIGAZINE",
            "url": "https://gigazine.net/news/rss_2.0/",
            "category": "テクノロジー",
        },
        {
            "name": "Impress Watch",
            "url": "https://www.watch.impress.co.jp/data/rss/1.0/ipw/feed.rdf",
            "category": "テクノロジー",
        },
        {
            "name": "CNET Japan",
            "url": "https://japan.cnet.com/rss/index.rdf",
            "category": "テクノロジー",
        },
        {
            "name": "Google News テクノロジー",
            "url": "https://news.google.com/rss/search?q=テクノロジー+OR+AI+OR+プログラミング&hl=ja&gl=JP&ceid=JP:ja",
            "category": "テクノロジー",
        },
    ],
    "business": [
        {
            "name": "NHK 経済",
            "url": "https://www.nhk.or.jp/rss/news/cat5.xml",
            "category": "ビジネス",
        },
        {
            "name": "Google News ビジネス",
            "url": "https://news.google.com/rss/search?q=ビジネス+OR+経済+OR+株式&hl=ja&gl=JP&ceid=JP:ja",
            "category": "ビジネス",
        },
    ],
    "general": [
        {
            "name": "NHK 主要ニュース",
            "url": "https://www.nhk.or.jp/rss/news/cat0.xml",
            "category": "総合",
        },
        {
            "name": "NHK 社会",
            "url": "https://www.nhk.or.jp/rss/news/cat1.xml",
            "category": "社会",
        },
        {
            "name": "NHK 国際",
            "url": "https://www.nhk.or.jp/rss/news/cat6.xml",
            "category": "国際",
        },
        {
            "name": "Hatena Bookmark",
            "url": "https://b.hatena.ne.jp/hotentry.rss",
            "category": "話題",
        },
    ],
    "ai": [
        {
            "name": "Google News AI",
            "url": "https://news.google.com/rss/search?q=人工知能+OR+ChatGPT+OR+Claude+OR+生成AI&hl=ja&gl=JP&ceid=JP:ja",
            "category": "AI",
        },
        {
            "name": "Google News AI(英語)",
            "url": "https://news.google.com/rss/search?q=artificial+intelligence+OR+LLM+OR+OpenAI+OR+Anthropic&hl=en&gl=US&ceid=US:en",
            "category": "AI(海外)",
        },
    ],
}

# ─── 記事設定 ───
MAX_ARTICLES_PER_FEED = 5      # 各フィードから取得する最大記事数
MAX_TOTAL_ARTICLES = 20        # 1日の最大記事数
ARTICLE_MIN_LENGTH = 30        # タイトル+説明のmin文字数（ゴミフィルタ）

# ─── 出力設定 ───
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
NEWS_CATEGORY = os.getenv("NEWS_CATEGORY", "tech")

# ─── コスト追跡 ───
# Haiku: 入力 $0.80/1M tokens, 出力 $4.00/1M tokens
COST_PER_INPUT_TOKEN = 0.80 / 1_000_000
COST_PER_OUTPUT_TOKEN = 4.00 / 1_000_000

# ─── アフィリエイト設定（実際のASPリンクに差し替え） ───
AFFILIATE_LINKS = {
    "AI": [
        {
            "text": "🤖 AIプログラミングを学ぶ",
            "url": os.getenv("AFFILIATE_AI_LEARNING", "#"),
            "description": "Udemyの人気AI講座（A8.net経由）",
            "asp": "a8.net",
        },
        {
            "text": "💻 GPU搭載ノートPC",
            "url": os.getenv("AFFILIATE_AI_PC", "#"),
            "description": "AI開発向けハイスペックPC（Amazonアソシエイト）",
            "asp": "amazon",
        },
    ],
    "テクノロジー": [
        {
            "text": "📚 テック書籍を探す",
            "url": os.getenv("AFFILIATE_TECH_BOOKS", "https://www.amazon.co.jp/b?node=466298&tag=YOUR_TAG"),
            "description": "Amazon テクノロジー書籍",
            "asp": "amazon",
        },
        {
            "text": "🎓 プログラミングスクール",
            "url": os.getenv("AFFILIATE_PROG_SCHOOL", "#"),
            "description": "テックアカデミー（もしもアフィリエイト経由）",
            "asp": "moshimo",
        },
    ],
    "ビジネス": [
        {
            "text": "💰 ネット証券で資産運用",
            "url": os.getenv("AFFILIATE_FINANCE", "#"),
            "description": "SBI証券 口座開設（A8.net経由）",
            "asp": "a8.net",
        },
        {
            "text": "📊 ビジネス書ベストセラー",
            "url": os.getenv("AFFILIATE_BIZ_BOOKS", "https://www.amazon.co.jp/b?node=466282&tag=YOUR_TAG"),
            "description": "Amazon ビジネス書",
            "asp": "amazon",
        },
    ],
    "default": [
        {
            "text": "📱 Kindle Unlimited 無料体験",
            "url": os.getenv("AFFILIATE_KINDLE", "https://www.amazon.co.jp/kindle-dbs/hz/signup?tag=YOUR_TAG"),
            "description": "200万冊以上が読み放題",
            "asp": "amazon",
        },
    ],
}
