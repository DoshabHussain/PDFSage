import io, json, threading, shutil, sys, os
from http.server import BaseHTTPRequestHandler, HTTPServer
import pymupdf, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["PDFSAGE_EMBEDDER"] = "tfidf"   # no model download in tests
from backend.pdf_loader import extract_text
from backend.chunker import chunk_text
from backend.retriever import VectorStore
from backend.llm import OllamaLLM, LLMError
from backend import features
import app as appmod

TOPICS = ["Photosynthesis converts light energy into chemical energy inside chloroplasts. ",
          "The French Revolution began in 1789 and transformed European politics. ",
          "Neural networks learn patterns by adjusting weights through backpropagation. ",
          "Plate tectonics explains how continents drift across the earth's mantle. "]


def make_pdf(pages=4, scanned=False):
    doc = pymupdf.open()
    for i in range(pages):
        p = doc.new_page()
        p.insert_textbox(pymupdf.Rect(50, 50, 550, 780), (TOPICS[i % 4] * 6), fontsize=11)
    if scanned:
        out = pymupdf.open()
        for p in doc:
            pix = p.get_pixmap(dpi=200)
            np_ = out.new_page(width=p.rect.width, height=p.rect.height)
            np_.insert_image(np_.rect, pixmap=pix)
        return out.tobytes()
    return doc.tobytes()


class FakeLLM:
    model = "fake"
    def generate(self, prompt, json_mode=False, max_tokens=0):
        if json_mode and "mcqs" in prompt:
            return json.dumps({"mcqs": [{"question": "Q?", "options": ["a", "b", "c", "d"], "answer": 2}]})
        if json_mode:
            return json.dumps({"questions": [{"question": "What is photosynthesis?", "answer": "Photosynthesis converts light energy into chemical energy inside chloroplasts."}, {"question": "When did the revolution begin?", "answer": "The French Revolution began in 1789."}]})
        return "- point one\n- point two"
    def models(self): return ["fake"]
    def is_up(self): return True


@pytest.fixture
def store():
    return VectorStore(chunk_text(extract_text(make_pdf())[0], max_words=60))


def test_text_extraction():
    text, info = extract_text(make_pdf())
    assert info["pages"] == 4 and info["ocr_pages"] == 0 and "Photosynthesis" in text


@pytest.mark.skipif(not shutil.which("tesseract"), reason="Tesseract not installed")
def test_ocr_on_scanned_pdf():
    text, info = extract_text(make_pdf(pages=1, scanned=True))
    assert info["ocr_pages"] == 1 and ("revolution" in text.lower() or "photosynthesis" in text.lower())


def test_chunking_and_retrieval(store):
    assert len(store.chunks) > 3
    assert "Revolution" in store.search("when did the French Revolution begin?", k=1)[0]
    assert 1 <= len(store.representative(3)) <= 3 and len(store.spread(3)) <= 3


def test_features(store):
    llm = FakeLLM()
    assert "point one" in features.summarize(store, llm)
    qs = features.generate_questions(store, llm)
    assert len(qs) == 2
    assert qs[0]["question"] == "What is photosynthesis?"
    assert qs[0]["answer"] == "Photosynthesis converts light energy into chemical energy inside chloroplasts."
    assert features.generate_mcqs(store, llm)[0]["answer"] == 2
    reply, ctx = features.answer(store, llm, "plate tectonics")
    assert reply and ctx


def test_bad_json_is_handled(store):
    class Bad(FakeLLM):
        def generate(self, *a, **k): return "not json at all"
    assert features.generate_questions(store, Bad()) == [] and features.generate_mcqs(store, Bad()) == []
    assert features._parse('noise {"questions": ["x"]} noise', "questions") == ["x"]


def test_ollama_client_against_fake_server():
    seen = {}
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            self.send_response(200); self.end_headers()
            self.wfile.write(json.dumps({"models": [{"name": "qwen2.5:3b"}]}).encode())
        def do_POST(self):
            seen.update(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200); self.end_headers()
            self.wfile.write(json.dumps({"message": {"content": "<think>x</think>hello"}}).encode())
    srv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    llm = OllamaLLM(model="qwen3:4b", host=f"http://127.0.0.1:{srv.server_port}")
    assert llm.is_up() and llm.models() == ["qwen2.5:3b"]
    assert llm.generate("hi", json_mode=True) == "hello"
    assert seen["format"] == "json" and seen["think"] is False and seen["stream"] is False
    srv.shutdown()


def test_ollama_offline_message():
    with pytest.raises(LLMError, match="not running"):
        OllamaLLM(host="http://127.0.0.1:1").generate("hi")


def test_flask_end_to_end():
    appmod.STATE.update(llm=FakeLLM(), store=None, info={})
    c = appmod.app.test_client()
    assert c.get("/").status_code == 200
    assert c.post("/api/summary", json={}).status_code == 409          # no PDF yet
    assert c.post("/api/upload", data={"file": (io.BytesIO(b"x"), "a.txt")}).status_code == 400
    r = c.post("/api/upload", data={"file": (io.BytesIO(make_pdf()), "doc.pdf")})
    assert r.status_code == 200 and r.json["pages"] == 4
    assert c.get("/api/status").json["loaded"] is True
    assert "point one" in c.post("/api/summary", json={}).json["summary"]
    assert len(c.post("/api/questions", json={"n": 2}).json["questions"]) == 2
    assert len(c.post("/api/mcqs", json={"n": 2}).json["mcqs"]) == 1
    ch = c.post("/api/chat", json={"question": "continents drift"}).json
    assert ch["answer"] and ch["sources"]
    assert c.post("/api/chat", json={"question": " "}).status_code == 400
