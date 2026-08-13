#!/usr/bin/env python3
"""
autobricksai.com 全自动注册 + 获取 API Key
引擎: YesCaptcha (付费)  |  2次过盾/账号  (signup + login)
邮箱: mail.tm (免费临时邮箱，返回完整HTML)
"""
import re
import time
import json
import requests
import secrets
import string
import sys

YESCAPTCHA_KEY = "YOUR_YESCAPTCHA_CLIENT_KEY"
YESCAPTCHA_URL = "https://api.yescaptcha.com"
SITEKEY = "0x4AAAAAADmmEIagJZYlezBx"
SITE_URL = "https://creators.autobricksai.com"
MAILTM_URL = "https://api.mail.tm"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"


def log(msg, level="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}")


# ── Turnstile (via YesCaptcha — PAID) ─────────────────
def solve_turnstile(timeout=120):
    resp = requests.post(f"{YESCAPTCHA_URL}/createTask", json={
        "clientKey": YESCAPTCHA_KEY,
        "task": {"type": "TurnstileTaskProxyless", "websiteURL": SITE_URL, "websiteKey": SITEKEY}
    }, timeout=15)
    data = resp.json()
    if data.get("errorId") != 0:
        raise RuntimeError(f"YesCaptcha createTask failed: {data}")
    task_id = data["taskId"]
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        resp = requests.post(f"{YESCAPTCHA_URL}/getTaskResult", json={
            "clientKey": YESCAPTCHA_KEY,
            "taskId": task_id
        }, timeout=15)
        data = resp.json()
        if data.get("status") == "ready":
            log(f"  Turnstile solved ({time.time()-start:.1f}s) [YesCaptcha]")
            return data["solution"]["token"]
        if data.get("status") == "CAPTCHA_FAIL":
            raise RuntimeError(f"YesCaptcha solve failed: {data}")
    raise TimeoutError("Turnstile timeout")


# ── Temp Email (mail.tm) ──────────────────────────────
def create_temp_email():
    """Create a mail.tm account. Returns (address, jwt_token). Retries on failure."""
    for attempt in range(5):
        try:
            resp = requests.get(f"{MAILTM_URL}/domains", timeout=10)
            domains = resp.json().get("hydra:member", [])
            if not domains:
                raise RuntimeError("mail.tm: no domains available")
            domain = domains[0]["domain"]

            username = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(10))
            mail_password = secrets.token_hex(8)
            address = f"{username}@{domain}"

            resp = requests.post(f"{MAILTM_URL}/accounts", json={
                "address": address, "password": mail_password
            }, timeout=10)
            if resp.status_code != 201:
                log(f"  mail.tm 创建失败 (attempt {attempt+1}): {resp.status_code}", "WARN")
                time.sleep(3)
                continue

            resp = requests.post(f"{MAILTM_URL}/token", json={
                "address": address, "password": mail_password
            }, timeout=10)
            jwt = resp.json()["token"]

            log(f"  邮箱: {address}")
            return address, jwt
        except Exception as e:
            log(f"  mail.tm 异常 (attempt {attempt+1}): {e}", "WARN")
            if attempt < 4:
                time.sleep(3)

    raise RuntimeError("mail.tm: 所有重试均失败")


def wait_for_confirm_link(mail_jwt, timeout=180):
    """Poll mail.tm inbox for Supabase confirmation email. Returns the verify URL."""
    log(f"  等待确认邮件 (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(3)
        try:
            resp = requests.get(f"{MAILTM_URL}/messages",
                headers={"Authorization": f"Bearer {mail_jwt}"}, timeout=10)
            msgs = resp.json().get("hydra:member", [])
            for m in msgs:
                if "confirm" in m.get("subject", "").lower():
                    msg_id = m["id"]
                    resp2 = requests.get(f"{MAILTM_URL}/messages/{msg_id}",
                        headers={"Authorization": f"Bearer {mail_jwt}"}, timeout=10)
                    full = resp2.json()
                    html = full.get("html", "")
                    if isinstance(html, list):
                        html = "".join(html)

                    urls = re.findall(r'https?://[^"\'\s<>]+', html)
                    for u in urls:
                        if "verify" in u and "token=" in u:
                            u = u.replace("&amp;", "&")
                            log(f"  确认链接: {u[:100]}...")
                            return u
        except Exception:
            pass
    raise TimeoutError("未收到确认邮件")


# ── Registration Flow ─────────────────────────────────
def main():
    log("=" * 50)
    log("autobricksai.com 全自动: 注册 → API Key")
    log(f"引擎: YesCaptcha (付费)  |  邮箱: mail.tm")
    log("=" * 50)

    password = f"Test{secrets.token_hex(4)}!"

    # Step 1: 临时邮箱
    log("[1/6] 创建临时邮箱...")
    email, mail_jwt = create_temp_email()

    # Step 2: 注册 (Turnstile #1)
    log("[2/6] 注册账号...")
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Origin": SITE_URL})
    session.get(f"{SITE_URL}/signup")

    ts1 = solve_turnstile()
    resp = session.post(f"{SITE_URL}/signup", data={
        "display_name": "TestUser",
        "email": email,
        "password": password,
        "cf-turnstile-response": ts1
    }, allow_redirects=False)

    if "Check your email" not in resp.text:
        log(f"  注册失败: {resp.text[:200]}", "ERROR")
        return {"status": "failed", "response": resp.text[:300]}

    log("  注册成功，等待邮箱确认...")

    # Step 3: 确认邮箱
    log("[3/6] 确认邮箱...")
    confirm_url = wait_for_confirm_link(mail_jwt)
    resp = session.get(confirm_url, allow_redirects=True)
    log(f"  邮箱已确认 → {resp.url[:80]}")

    # Step 4: 登录 (Turnstile #2)
    log("[4/6] 登录...")
    ts2 = solve_turnstile()
    resp = session.post(f"{SITE_URL}/login", data={
        "email": email,
        "password": password,
        "cf-turnstile-response": ts2
    }, allow_redirects=True)

    abai_token = None
    for cookie in session.cookies:
        if cookie.name == "abai_token":
            abai_token = cookie.value
            break

    if not abai_token:
        log("  登录失败: 未获取到 abai_token", "ERROR")
        return {"status": "login_failed"}

    log("  登录成功!")

    # Step 5: 创建 API Key
    log("[5/6] 创建 API Key...")
    resp = session.get(f"{SITE_URL}/account/api-keys")
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    if not csrf:
        csrf = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', resp.text)
    if not csrf:
        log("  获取CSRF失败", "ERROR")
        return {"status": "csrf_failed"}
    csrf_token = csrf.group(1)

    resp = session.post(f"{SITE_URL}/account/api-keys/keys", data={
        "csrf_token": csrf_token,
        "name": "my-api-key"
    }, headers={"x-csrf-token": csrf_token}, allow_redirects=False)

    # Extract full API key
    api_key = None
    codes = re.findall(r'<code[^>]*>([^<]*)</code>', resp.text)
    for c in codes:
        m = re.match(r'(abai_sk_live_[a-zA-Z0-9_\-]{40,60})', c.strip())
        if m:
            api_key = m.group(1)
            break

    if not api_key:
        flashes = re.findall(r'abai_sk_live_([a-zA-Z0-9_\-]{40,60})', resp.text)
        if flashes:
            api_key = f"abai_sk_live_{flashes[0]}"

    # Step 6: 结果
    log("[6/6] 完成!")
    if api_key:
        log("=" * 50)
        log("✅ 注册成功！", "SUCCESS")
        log(f"  邮箱:    {email}")
        log(f"  密码:    {password}")
        log(f"  API Key: {api_key}")
        log(f"  过盾: YesCaptcha x2")
        log("=" * 50)
        return {
            "status": "success",
            "email": email,
            "password": password,
            "api_key": api_key,
            "turnstile_count": 2
        }
    else:
        log(f"  无法提取API Key", "ERROR")
        return {
            "status": "key_not_found",
            "email": email,
            "password": password,
            "turnstile_count": 2
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="autobricksai.com 全自动注册 (YesCaptcha)")
    parser.add_argument("-n", "--count", type=int, default=1, help="注册账号数量")
    args = parser.parse_args()

    results = []
    for i in range(args.count):
        if i > 0:
            time.sleep(5)
        log(f"\n{'#'*50}")
        log(f" 第 {i+1}/{args.count} 个账号")
        log(f"{'#'*50}")
        try:
            r = main()
            results.append(r)
        except Exception as e:
            log(f"异常: {e}", "ERROR")
            results.append({"status": "error", "error": str(e)})

    log(f"\n{'='*50}")
    success = sum(1 for r in results if r.get("api_key"))
    log(f"完成: {success}/{len(results)} 成功")
    for r in results:
        if r.get("api_key"):
            log(f"  {r['email']} → {r['api_key']}")
    log(f"{'='*50}")
    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))
