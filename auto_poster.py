"""SNS自動投稿 - X (Twitter) & Threads"""

import json
import os
import requests
from config import OUTPUT_DIR, SITE_URL

# ─── X (Twitter) API v2 ───
X_API_KEY = os.getenv("X_API_KEY", "")
X_API_SECRET = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET", "")

# ─── Threads API ───
THREADS_USER_ID = os.getenv("THREADS_USER_ID", "")
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN", "")


def post_to_x(text: str) -> dict:
    """X (Twitter) API v2で投稿"""
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET]):
        print("[SKIP] X: APIキーが未設定です")
        return {"status": "skipped", "reason": "no_credentials"}

    from requests_oauthlib import OAuth1

    auth = OAuth1(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
    resp = requests.post(
        "https://api.x.com/2/tweets",
        json={"text": text},
        auth=auth,
        timeout=30,
    )

    if resp.status_code == 201:
        data = resp.json()
        tweet_id = data["data"]["id"]
        print(f"[OK] X投稿成功: https://x.com/i/status/{tweet_id}")
        return {"status": "success", "id": tweet_id, "url": f"https://x.com/i/status/{tweet_id}"}
    else:
        print(f"[ERROR] X投稿失敗: {resp.status_code} {resp.text}")
        return {"status": "error", "code": resp.status_code, "detail": resp.text}


def post_to_threads(text: str) -> dict:
    """Threads APIで投稿（2段階: コンテナ作成 → 公開）"""
    if not all([THREADS_USER_ID, THREADS_ACCESS_TOKEN]):
        print("[SKIP] Threads: APIキーが未設定です")
        return {"status": "skipped", "reason": "no_credentials"}

    base = "https://graph.threads.net/v1.0"

    # Step 1: メディアコンテナ作成
    resp1 = requests.post(
        f"{base}/{THREADS_USER_ID}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )

    if resp1.status_code != 200:
        print(f"[ERROR] Threads コンテナ作成失敗: {resp1.status_code} {resp1.text}")
        return {"status": "error", "step": "create", "code": resp1.status_code, "detail": resp1.text}

    container_id = resp1.json()["id"]

    # Step 2: 公開
    resp2 = requests.post(
        f"{base}/{THREADS_USER_ID}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )

    if resp2.status_code == 200:
        post_id = resp2.json()["id"]
        print(f"[OK] Threads投稿成功: ID={post_id}")
        return {"status": "success", "id": post_id}
    else:
        print(f"[ERROR] Threads公開失敗: {resp2.status_code} {resp2.text}")
        return {"status": "error", "step": "publish", "code": resp2.status_code, "detail": resp2.text}


def auto_post(date: str) -> dict:
    """指定日付のSNS投稿文を読み込んで自動投稿"""
    sns_file = os.path.join(OUTPUT_DIR, f"sns_{date}.json")
    if not os.path.exists(sns_file):
        print(f"[ERROR] SNSファイルが見つかりません: {sns_file}")
        return {"x": {"status": "error"}, "threads": {"status": "error"}}

    with open(sns_file, "r", encoding="utf-8") as f:
        sns = json.load(f)

    # X投稿（サイトURLを追加）
    x_text = sns["twitter"]
    article_url = f"{SITE_URL}/articles/{date.replace('-', '/')}/"
    # URL分の余裕を確保（t.coで23文字）
    if len(x_text) + 25 <= 280:
        x_text += f"\n{article_url}"

    x_result = post_to_x(x_text)
    threads_result = post_to_threads(sns["threads"])

    # 結果を保存
    result = {"date": date, "x": x_result, "threads": threads_result}
    result_file = os.path.join(OUTPUT_DIR, f"post_result_{date}.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[INFO] 投稿結果: {result_file}")
    return result
