"""SNS自動投稿 - X (Twitter) & Threads & Bluesky"""

import json
import os
import re
from datetime import datetime, timezone

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

# ─── Bluesky (AT Protocol) ───
BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE", "")
BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD", "")


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


def _extract_hashtag_facets(text: str) -> list:
    """テキストからハッシュタグを抽出してBluesky facetオブジェクトを生成"""
    facets = []
    text_bytes = text.encode("utf-8")
    for match in re.finditer(r"#(\w+)", text):
        tag = match.group(1)
        # バイト単位でのオフセットを計算（AT Protocolの仕様）
        start = len(text[: match.start()].encode("utf-8"))
        end = len(text[: match.end()].encode("utf-8"))
        facets.append(
            {
                "index": {"byteStart": start, "byteEnd": end},
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#tag",
                        "tag": tag,
                    }
                ],
            }
        )
    return facets


def post_to_bluesky(text: str) -> dict:
    """Bluesky (AT Protocol) で投稿"""
    if not all([BLUESKY_HANDLE, BLUESKY_APP_PASSWORD]):
        print("[SKIP] Bluesky: 認証情報が未設定です")
        return {"status": "skipped", "reason": "no_credentials"}

    base = "https://bsky.social/xrpc"

    # Step 1: セッション作成（ログイン）
    try:
        login_resp = requests.post(
            f"{base}/com.atproto.server.createSession",
            json={
                "identifier": BLUESKY_HANDLE,
                "password": BLUESKY_APP_PASSWORD,
            },
            timeout=30,
        )
    except requests.RequestException as e:
        print(f"[ERROR] Bluesky ログイン通信エラー: {e}")
        return {"status": "error", "step": "login", "detail": str(e)}

    if login_resp.status_code != 200:
        print(f"[ERROR] Bluesky ログイン失敗: {login_resp.status_code} {login_resp.text}")
        return {"status": "error", "step": "login", "code": login_resp.status_code, "detail": login_resp.text}

    session = login_resp.json()
    access_token = session["accessJwt"]
    did = session["did"]

    # Step 2: 投稿作成
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
    }

    # ハッシュタグのfacetを追加
    facets = _extract_hashtag_facets(text)
    if facets:
        record["facets"] = facets

    try:
        post_resp = requests.post(
            f"{base}/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
            timeout=30,
        )
    except requests.RequestException as e:
        print(f"[ERROR] Bluesky 投稿通信エラー: {e}")
        return {"status": "error", "step": "post", "detail": str(e)}

    if post_resp.status_code == 200:
        data = post_resp.json()
        uri = data.get("uri", "")
        cid = data.get("cid", "")
        # URIからpost IDを抽出してWebのURLを構築
        # uri形式: at://did:plc:xxx/app.bsky.feed.post/yyy
        post_id = uri.rsplit("/", 1)[-1] if uri else ""
        web_url = f"https://bsky.app/profile/{BLUESKY_HANDLE}/post/{post_id}" if post_id else ""
        print(f"[OK] Bluesky投稿成功: {web_url or uri}")
        return {"status": "success", "uri": uri, "cid": cid, "url": web_url}
    else:
        print(f"[ERROR] Bluesky投稿失敗: {post_resp.status_code} {post_resp.text}")
        return {"status": "error", "step": "post", "code": post_resp.status_code, "detail": post_resp.text}


def auto_post(date: str) -> dict:
    """指定日付のSNS投稿文を読み込んで自動投稿"""
    sns_file = os.path.join(OUTPUT_DIR, f"sns_{date}.json")
    if not os.path.exists(sns_file):
        print(f"[ERROR] SNSファイルが見つかりません: {sns_file}")
        return {"x": {"status": "error"}, "threads": {"status": "error"}, "bluesky": {"status": "error"}}

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
    bluesky_result = post_to_bluesky(x_text)

    # 結果を保存
    result = {"date": date, "x": x_result, "threads": threads_result, "bluesky": bluesky_result}
    result_file = os.path.join(OUTPUT_DIR, f"post_result_{date}.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[INFO] 投稿結果: {result_file}")
    return result
