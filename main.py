#!/usr/bin/env python3
"""
AI News Digest Bot - メインパイプライン

使い方:
    python main.py                    # デフォルト(tech)カテゴリで実行
    python main.py --category ai      # AIカテゴリで実行
    python main.py --category business # ビジネスカテゴリで実行
    python main.py --dry-run          # API呼び出しなしでテスト
    python main.py --cost             # 累計コストを表示
    python main.py --build-site       # 静的サイトを構築
    python main.py --all -c ai        # パイプライン実行 + サイト構築
    python main.py --setup            # セットアップ手順を表示
"""

import argparse
import json
import os
import sys
from datetime import datetime

from config import OUTPUT_DIR, NEWS_CATEGORY, SITE_DIR, SITE_NAME, SITE_URL
from scraper import fetch_news
from summarizer import summarize_articles
from publisher import publish_html, publish_markdown, publish_sns


def show_cost():
    """累計API使用コストを表示（収益推計付き）"""
    cost_file = os.path.join(OUTPUT_DIR, "cost_log.json")
    if not os.path.exists(cost_file):
        print("コストログがまだありません。")
        return

    with open(cost_file, "r") as f:
        log = json.load(f)

    print("\n" + "=" * 60)
    print("  API使用コスト & 収益シミュレーション")
    print("=" * 60)
    print(f"\n累計コスト: ${log['total_usd']:.6f} (約{log['total_usd'] * 150:.2f}円)")
    print(f"\n日別明細:")
    print(f"{'日付':<12} {'記事数':>6} {'入力トークン':>12} {'出力トークン':>12} {'コスト':>10}")
    print("-" * 58)
    for date, d in sorted(log.get("daily", {}).items()):
        print(f"{date:<12} {d['articles']:>6} {d['input_tokens']:>12,} {d['output_tokens']:>12,} ${d['cost_usd']:>9.6f}")

    # 月額推計
    days = len(log.get("daily", {}))
    if days > 0:
        avg_daily = log["total_usd"] / days
        monthly_cost = avg_daily * 30
        monthly_cost_jpy = monthly_cost * 150

        print(f"\n{'─' * 58}")
        print(f"  月額推計コスト: ${monthly_cost:.4f} (約{monthly_cost_jpy:.0f}円)")
        print(f"  1日あたり: ${avg_daily:.6f} (約{avg_daily * 150:.2f}円)")

        # 収益シミュレーション
        print(f"\n{'─' * 58}")
        print(f"  収益シミュレーション（月間）")
        print(f"{'─' * 58}")
        print(f"  ■ AdSense（RPM ¥200想定）")
        scenarios = [
            ("1,000 PV/月", 1000, 200),
            ("5,000 PV/月", 5000, 200),
            ("10,000 PV/月", 10000, 200),
            ("50,000 PV/月", 50000, 200),
        ]
        for label, pv, rpm in scenarios:
            revenue = (pv / 1000) * rpm
            profit = revenue - monthly_cost_jpy
            status = "黒字" if profit > 0 else "赤字"
            print(f"    {label:<16} → 収益 ¥{revenue:>8,.0f} | 利益 ¥{profit:>8,.0f} ({status})")

        print(f"\n  ■ アフィリエイト（月間成約想定）")
        print(f"    書籍紹介(3%) 5件  → 約 ¥{5 * 1500 * 0.03:>6,.0f}")
        print(f"    スクール(¥5000) 1件 → 約 ¥5,000")
        print(f"    証券口座(¥3000) 1件 → 約 ¥3,000")

        breakeven_pv = monthly_cost_jpy / (200 / 1000) if monthly_cost_jpy > 0 else 0
        print(f"\n  損益分岐点: 約 {breakeven_pv:,.0f} PV/月（AdSenseのみ）")
        print(f"  ※ アフィリエイト併用で実質 数百PV/月 で黒字化可能")
    print()


def run_pipeline(category: str, dry_run: bool = False):
    """メインパイプライン実行"""
    print("\n" + "=" * 50)
    print(f"  AI News Digest - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  カテゴリ: {category}")
    print("=" * 50)

    # Step 1: ニュース取得
    print("\n  Step 1: ニュース取得中...")
    articles = fetch_news(category)

    if not articles:
        print("[INFO] 新着記事がありません。終了します。")
        return

    print(f"  → {len(articles)}件の記事を取得")
    for a in articles[:5]:
        print(f"    [{a['source']}] {a['title'][:50]}")
    if len(articles) > 5:
        print(f"    ... 他{len(articles) - 5}件")

    if dry_run:
        print("\n[DRY RUN] API呼び出しをスキップします。")
        return

    # Step 2: AI要約
    print("\n  Step 2: AI要約中...")
    result = summarize_articles(articles)
    print(f"  → 見出し: {result['headline']}")
    print(f"  → コスト: ${result['cost_usd']:.6f}")

    # Step 2.5: JSONデータ保存（サイト生成用）
    from site_generator import _save_article_json
    json_path = _save_article_json(result)
    print(f"  → JSON保存: {json_path}")

    # Step 3: 記事生成
    print("\n  Step 3: 記事生成中...")

    # 関連記事を取得（サイト生成用JSONから）
    from site_generator import _load_all_articles
    all_days = _load_all_articles()
    related = [d for d in all_days if d.get("date") != result["date"]][:5]

    html_path = publish_html(result, related_articles=related)
    md_path = publish_markdown(result)
    sns = publish_sns(result)

    # 完了レポート
    print("\n" + "=" * 50)
    print("  完了！")
    print("=" * 50)
    print(f"  HTML:     {html_path}")
    print(f"  Markdown: {md_path}")
    sns_file = os.path.join(OUTPUT_DIR, f"sns_{result['date']}.json")
    print(f"  SNS投稿:  {sns_file}")
    print(f"  JSON:     {json_path}")
    print(f"\n  API コスト: ${result['cost_usd']:.6f} (約{result['cost_usd'] * 150:.4f}円)")
    print(f"  トークン: 入力{result['tokens']['input']:,} + 出力{result['tokens']['output']:,}")

    print(f"\n  X/Twitter投稿文:")
    print(f"  {sns['twitter'][:100]}...")

    print(f"\n  次のステップ:")
    print(f"  1. {html_path} をブラウザで確認")
    print(f"  2. python main.py --build-site でサイトを構築")
    print(f"  3. docs/ をGitHub Pagesにデプロイ")
    print()


def build_site():
    """静的サイトを構築"""
    from site_generator import build_site as _build
    _build()


def show_setup():
    """セットアップ手順をターミナルに表示"""
    print("""
================================================================
  AI News Digest - セットアップガイド
================================================================

【1. 事前準備】

  1) Python 3.10+ をインストール
  2) 依存パッケージをインストール:
     pip install -r requirements.txt
  3) .env.example を .env にコピーして設定:
     cp .env.example .env

【2. APIキー設定】

  .env ファイルに以下を設定:
    ANTHROPIC_API_KEY=sk-ant-xxxxx  ← Anthropic Console で取得

【3. 基本的な使い方】

  # ニュース取得＆AI要約（AIカテゴリ）
  python main.py -c ai

  # テクノロジーカテゴリ
  python main.py -c tech

  # 静的サイト構築
  python main.py --build-site

  # パイプライン + サイト構築を一括実行
  python main.py --all -c ai

  # APIを呼ばずにテスト
  python main.py --dry-run

  # コスト確認
  python main.py --cost

【4. GitHub Pages デプロイ】

  1) GitHubリポジトリを作成
  2) Settings > Pages で Source を「Deploy from branch」、
     Branch を「main」、フォルダを「/docs」に設定
  3) リポジトリの Secrets に設定:
     - ANTHROPIC_API_KEY: Anthropic APIキー
  4) リポジトリの Variables に設定（任意）:
     - SITE_URL: https://yourusername.github.io/ai-news-digest
  5) .github/workflows/daily.yml が毎朝7時(JST)に自動実行

【5. アフィリエイト設定】

  .env ファイルにアフィリエイトリンクを設定:
    AFFILIATE_AI_LEARNING=https://...  (A8.net等のリンク)
    AFFILIATE_AI_PC=https://...        (Amazonアソシエイトリンク)
    AFFILIATE_TECH_BOOKS=https://...
    AFFILIATE_PROG_SCHOOL=https://...
    AFFILIATE_FINANCE=https://...
    AFFILIATE_BIZ_BOOKS=https://...
    AFFILIATE_KINDLE=https://...

【6. AdSense 設定】

  Google AdSense 承認後に .env に追加:
    ADSENSE_CLIENT_ID=ca-pub-XXXXX

【7. コスト目安】

  Claude Haiku使用:
  - 1日あたり: 約 $0.001〜0.005 (約0.15〜0.75円)
  - 月額: 約 $0.03〜0.15 (約5〜23円)
  - AdSense + アフィリエイトで数百PV/月で黒字化可能

================================================================
""")


def main():
    parser = argparse.ArgumentParser(description="AI News Digest Bot")
    parser.add_argument("--category", "-c", default=NEWS_CATEGORY,
                       choices=["tech", "business", "general", "ai"],
                       help="ニュースカテゴリ")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="API呼び出しなしでテスト")
    parser.add_argument("--cost", action="store_true",
                       help="累計コストを表示")
    parser.add_argument("--build-site", action="store_true",
                       help="静的サイトを構築")
    parser.add_argument("--all", action="store_true",
                       help="パイプライン実行 + サイト構築")
    parser.add_argument("--post", action="store_true",
                       help="SNS自動投稿（X, Threads）")
    parser.add_argument("--setup", action="store_true",
                       help="セットアップ手順を表示")

    args = parser.parse_args()

    if args.setup:
        show_setup()
        return

    if args.post:
        from auto_poster import auto_post
        today = datetime.now().strftime("%Y-%m-%d")
        auto_post(today)
        return

    if args.cost:
        show_cost()
        return

    if args.build_site:
        build_site()
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.all:
        run_pipeline(args.category, args.dry_run)
        if not args.dry_run:
            build_site()
            # SNS自動投稿（キーが設定されている場合のみ）
            from auto_poster import auto_post
            today = datetime.now().strftime("%Y-%m-%d")
            auto_post(today)
        return

    run_pipeline(args.category, args.dry_run)


if __name__ == "__main__":
    main()
