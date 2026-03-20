"""Claude APIでニュース記事を要約・分析"""

import json
import os
from datetime import datetime
from anthropic import Anthropic
from config import (
    ANTHROPIC_API_KEY,
    MODEL,
    MAX_TOKENS,
    COST_PER_INPUT_TOKEN,
    COST_PER_OUTPUT_TOKEN,
    OUTPUT_DIR,
)


client = Anthropic(api_key=ANTHROPIC_API_KEY)


def _track_cost(input_tokens: int, output_tokens: int):
    """API使用コストを記録"""
    cost_file = os.path.join(OUTPUT_DIR, "cost_log.json")
    today = datetime.now().strftime("%Y-%m-%d")

    if os.path.exists(cost_file):
        with open(cost_file, "r") as f:
            log = json.load(f)
    else:
        log = {"daily": {}, "total_usd": 0.0}

    cost = (input_tokens * COST_PER_INPUT_TOKEN) + (output_tokens * COST_PER_OUTPUT_TOKEN)

    if today not in log["daily"]:
        log["daily"][today] = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "articles": 0}

    log["daily"][today]["input_tokens"] += input_tokens
    log["daily"][today]["output_tokens"] += output_tokens
    log["daily"][today]["cost_usd"] += cost
    log["daily"][today]["articles"] += 1
    log["total_usd"] += cost

    with open(cost_file, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    return cost


def summarize_articles(articles: list[dict]) -> dict:
    """
    記事リストをClaude APIで要約。
    バッチで一括処理してAPI呼び出し回数を最小化。

    Returns:
        {
            "date": "2026-03-21",
            "headline": "今日の注目ニュース一言",
            "articles": [
                {
                    ...original fields...,
                    "ai_summary": "AI要約文",
                    "ai_tags": ["タグ1", "タグ2"],
                    "importance": 1-5
                }
            ],
            "daily_digest": "今日のニュース全体まとめ",
            "sns_post": "X/Twitter向け投稿文",
            "cost_usd": 0.001
        }
    """
    if not articles:
        return {"date": datetime.now().strftime("%Y-%m-%d"), "articles": [], "daily_digest": "本日のニュースはありません。"}

    # 記事データをプロンプト用に整形
    articles_text = ""
    for i, a in enumerate(articles, 1):
        articles_text += f"""
---記事{i}---
タイトル: {a['title']}
出典: {a['source']}
カテゴリ: {a['category']}
日時: {a['published']}
概要: {a['summary']}
URL: {a['link']}
"""

    prompt = f"""以下の{len(articles)}件のニュース記事を分析し、JSON形式で返してください。

{articles_text}

以下のJSON形式で返してください（```json ```で囲まないこと）:
{{
  "headline": "今日の最も重要なニュースを一言で（30文字以内）",
  "articles": [
    {{
      "index": 1,
      "ai_summary": "記事の要点を2-3文で要約（事実のみ、独自表現で）",
      "ai_tags": ["関連タグ", "最大3つ"],
      "importance": 3
    }}
  ],
  "daily_digest": "今日のニュース全体を3-5文でまとめた総括。トレンドや共通テーマを抽出。",
  "sns_post": "X/Twitter向けの投稿文（280文字以内）。ハッシュタグ2-3個付き。興味を引く書き出しで。"
}}

ルール:
- importanceは1(低)〜5(高)で判定
- ai_summaryは元記事の表現をコピーせず、事実を独自の言葉で要約
- sns_postは「続きはプロフリンクから」的な誘導文を含める
- 全て日本語で出力"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    # コスト追跡
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = _track_cost(input_tokens, output_tokens)

    # レスポンスをパース
    raw_text = response.content[0].text.strip()
    # ```json ... ``` が含まれていたら除去
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[WARN] JSONパースに失敗。生テキスト:\n{raw_text[:200]}")
        result = {
            "headline": "ニュースまとめ",
            "articles": [],
            "daily_digest": raw_text[:500],
            "sns_post": "",
        }

    # 元の記事データとAI結果をマージ
    merged_articles = []
    for a in articles:
        idx = articles.index(a)
        ai_data = next((r for r in result.get("articles", []) if r.get("index") == idx + 1), {})
        merged = {
            **a,
            "ai_summary": ai_data.get("ai_summary", a["summary"]),
            "ai_tags": ai_data.get("ai_tags", []),
            "importance": ai_data.get("importance", 3),
        }
        merged_articles.append(merged)

    # 重要度でソート
    merged_articles.sort(key=lambda x: x["importance"], reverse=True)

    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "headline": result.get("headline", ""),
        "articles": merged_articles,
        "daily_digest": result.get("daily_digest", ""),
        "sns_post": result.get("sns_post", ""),
        "cost_usd": round(cost, 6),
        "tokens": {"input": input_tokens, "output": output_tokens},
    }

    print(f"[INFO] AI要約完了 | tokens: {input_tokens}+{output_tokens} | コスト: ${cost:.6f}")
    return output
