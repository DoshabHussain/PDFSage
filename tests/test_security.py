import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["PDFSAGE_EMBEDDER"] = "tfidf"
import app as A

LAN = {"REMOTE_ADDR": "192.168.1.50"}


def test_remote_access_with_token(monkeypatch):
    monkeypatch.setattr(A, "TOKEN", "s3cret-token")
    monkeypatch.setattr(A, "ALLOWED_HOSTS", A.ALLOWED_HOSTS | {"192.168.1.20"})
    c = A.app.test_client()
    kw = dict(base_url="http://192.168.1.20:5000", environ_base=LAN)
    assert c.get("/api/status", **kw).status_code == 401                   # no token
    assert c.get("/?token=wrong", **kw).status_code == 401                 # wrong token
    r = c.get("/?token=s3cret-token", **kw)                                # login sets cookie
    assert r.status_code == 302 and "HttpOnly" in r.headers["Set-Cookie"] and "SameSite=Strict" in r.headers["Set-Cookie"]
    assert c.get("/api/status", **kw).status_code == 200                   # cookie accepted


def test_static_assets_and_headers():
    c = A.app.test_client()
    assert c.get("/static/app.js").status_code == 200 and c.get("/static/style.css").status_code == 200
    h = c.get("/").headers
    assert "script-src" not in h["Content-Security-Policy"] and "default-src 'self'" in h["Content-Security-Policy"]
    assert b"<script>" not in c.get("/").data          # no inline script, so CSP blocks injected scripts


def test_same_origin_post_allowed():
    c = A.app.test_client()
    assert c.post("/api/model", json={"model": "qwen2.5:3b"}, headers={"Origin": "http://localhost"}).status_code == 200
