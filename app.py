import hmac
import logging
import os
import threading
from urllib.parse import urlparse
from flask import Flask, jsonify, redirect, render_template, request
from backend.pdf_loader import extract_text, PDFError
from backend.chunker import chunk_text
from backend.retriever import VectorStore
from backend.llm import OllamaLLM, LLMError
from backend import features

# --- Security configuration -------------------------------------------------
# By default only this PC (localhost) can use the app. To use it from a phone, set:
#   PDFSAGE_TOKEN=<long random secret>   PDFSAGE_ALLOWED_HOSTS=<this PC's LAN IP>
TOKEN = os.getenv("PDFSAGE_TOKEN", "")
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"} | {h.strip().lower() for h in os.getenv("PDFSAGE_ALLOWED_HOSTS", "").split(",") if h.strip()}
LOCAL_IPS = {"127.0.0.1", "::1"}
MAX_MB = int(os.getenv("PDFSAGE_MAX_MB", "25"))
MAX_CHUNKS = 600
MODEL_RE = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024
log = logging.getLogger("pdfsage")
STATE = {"llm": OllamaLLM(), "store": None, "info": {}}  # single local user
LLM_LOCK = threading.Lock()


class ApiError(Exception):
    def __init__(self, msg, status=400):
        self.msg, self.status = msg, status


@app.errorhandler(ApiError)
def _api(e):
    return jsonify(error=e.msg), e.status


@app.errorhandler(LLMError)
def _llm(e):
    return jsonify(error=str(e)), 503


@app.errorhandler(413)
def _big(e):
    return jsonify(error=f"File too large (max {MAX_MB} MB)."), 413


@app.errorhandler(Exception)
def _any(e):
    if hasattr(e, "code") and isinstance(e.code, int) and e.code < 500:
        return jsonify(error=getattr(e, "name", "Bad request")), e.code
    log.exception("Unhandled error")
    return jsonify(error="Internal server error."), 500


@app.before_request
def guard():
    host = (urlparse("//" + request.host).hostname or "").lower()
    if host not in ALLOWED_HOSTS:                       # blocks DNS-rebinding
        raise ApiError("Host not allowed.", 403)
    if request.remote_addr not in LOCAL_IPS:            # remote devices need the token
        if not TOKEN:
            raise ApiError("Remote access is disabled. Set PDFSAGE_TOKEN to enable it.", 403)
        qt = request.args.get("token", "")
        if qt and hmac.compare_digest(qt, TOKEN):
            resp = redirect("/")
            resp.set_cookie("pdfsage_token", TOKEN, httponly=True, samesite="Strict", max_age=86400)
            return resp
        if not hmac.compare_digest(request.cookies.get("pdfsage_token", ""), TOKEN):
            raise ApiError("Unauthorized.", 401)
    if request.method == "POST":                        # blocks cross-site (CSRF) requests
        origin = request.headers.get("Origin")
        if origin and urlparse(origin).netloc.lower() != request.host.lower():
            raise ApiError("Cross-origin request blocked.", 403)


@app.after_request
def headers(r):
    r.headers["Content-Security-Policy"] = ("default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "no-referrer"
    if request.path.startswith("/api/"):
        r.headers["Cache-Control"] = "no-store"
    return r


def body() -> dict:
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        raise ApiError("Expected a JSON object.")
    return d


def num(d, key, default, lo, hi) -> int:
    try:
        v = int(d.get(key, default))
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


class busy:
    """Only one heavy job at a time (the local LLM is a single shared resource)."""
    def __enter__(self):
        if not LLM_LOCK.acquire(blocking=False):
            raise ApiError("The model is busy. Please wait for the current task.", 429)

    def __exit__(self, *a):
        LLM_LOCK.release()


def need_doc():
    if STATE["store"] is None:
        raise ApiError("Upload and process a PDF first.", 409)
    return STATE["store"], STATE["llm"]


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    llm = STATE["llm"]
    return jsonify(ollama=llm.is_up(), models=llm.models(), model=llm.model,
                   loaded=STATE["store"] is not None, info=STATE["info"])


@app.post("/api/model")
def set_model():
    import re
    m = body().get("model")
    if not isinstance(m, str) or not re.match(MODEL_RE, m):
        raise ApiError("Invalid model name.")
    STATE["llm"].model = m
    return jsonify(model=m)


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".pdf"):
        raise ApiError("Please upload a PDF file.")
    data = f.read()
    if b"%PDF-" not in data[:1024]:
        raise ApiError("This file is not a valid PDF.")
    with busy():
        try:
            text, info = extract_text(data)
        except PDFError as e:
            raise ApiError(str(e), 422)
        except Exception:
            log.exception("PDF parse failed")
            raise ApiError("Could not read this PDF.")
        chunks = chunk_text(text)[:MAX_CHUNKS]
        if not chunks:
            raise ApiError("No text found. " + (info["warning"] or ""), 422)
        store = VectorStore(chunks)
        STATE["store"] = store
        STATE["info"] = {**info, "name": os.path.basename(f.filename)[:80], "words": len(text.split()),
                         "chunks": len(chunks), "embedder": store.kind}
    return jsonify(STATE["info"])


@app.post("/api/summary")
def summary():
    s, l = need_doc()
    with busy():
        try:
            return jsonify(summary=features.summarize(s, l))
        except LLMError:
            raise
        except Exception as e:
            log.exception("Summary generation failed")
            raise LLMError(f"Failed to generate summary: {e}")


@app.post("/api/questions")
def questions():
    d = body(); s, l = need_doc()
    with busy():
        try:
            return jsonify(questions=features.generate_questions(s, l, num(d, "n", 6, 1, 12)))
        except LLMError:
            raise
        except Exception as e:
            log.exception("Question generation failed")
            raise LLMError(f"Failed to generate questions: {e}")


@app.post("/api/mcqs")
def mcqs():
    d = body(); s, l = need_doc()
    with busy():
        try:
            return jsonify(mcqs=features.generate_mcqs(s, l, num(d, "n", 4, 1, 8)))
        except LLMError:
            raise
        except Exception as e:
            log.exception("MCQ generation failed")
            raise LLMError(f"Failed to generate MCQs: {e}")


@app.post("/api/chat")
def chat():
    d = body(); s, l = need_doc()
    q = d.get("question")
    if not isinstance(q, str) or not q.strip():
        raise ApiError("Empty question.")
    with busy():
        try:
            reply, ctx = features.answer(s, l, q.strip()[:500])
        except LLMError:
            raise
        except Exception as e:
            log.exception("Chat answer failed")
            raise LLMError(f"Failed to get answer: {e}")
    return jsonify(answer=reply, sources=ctx)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
