import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String, Line

out, tests = sys.argv[1], sys.argv[2]
ss = getSampleStyleSheet()
P = colors.HexColor("#3b2fb5")
H1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=P, fontSize=16)
B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=10.5, leading=15)
C = ParagraphStyle("c", parent=B, fontSize=9, leading=12)


def tbl(rows, widths):
    t = Table([[Paragraph(str(c), C) for c in r] for r in rows], colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7e4ff")),
                           ("GRID", (0, 0), (-1, -1), .4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def box(d, x, y, w, h, label, fill):
    d.add(Rect(x, y, w, h, rx=6, ry=6, fillColor=colors.HexColor(fill), strokeColor=P))
    lines = label.split("\n")
    for i, l in enumerate(lines):
        d.add(String(x + w / 2, y + h / 2 + (len(lines) - 1) * 5.5 - i * 11 - 3, l, fontSize=8, textAnchor="middle"))


d = Drawing(480, 330)
box(d, 150, 285, 180, 36, "User (Browser)", "#dbeafe")
box(d, 110, 220, 260, 44, "Flask Web UI\nindex.html + REST API (app.py)", "#ede9fe")
box(d, 10, 130, 140, 56, "Ingestion\nPyMuPDF + Tesseract OCR\nCleaner > Chunker", "#fef3c7")
box(d, 170, 130, 140, 56, "Retriever\nEmbeddings (MiniLM / TF-IDF)\nCosine search", "#dcfce7")
box(d, 330, 130, 140, 56, "Feature Layer\nSummary - Questions\nMCQs - RAG Q&A", "#fee2e2")
box(d, 250, 30, 220, 56, "Local LLM (Ollama)\nQwen 2.5 3B / Qwen3 / Llama 3.2\nlocalhost:11434", "#fce7f3")
box(d, 10, 30, 210, 56, "In-memory Document Store\nchunks + vectors", "#e5e7eb")
for x1, y1, x2, y2 in [(240, 285, 240, 264), (200, 220, 80, 186), (240, 220, 240, 186), (280, 220, 400, 186),
                       (400, 130, 380, 86), (80, 130, 110, 86), (240, 130, 150, 86)]:
    d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#555555")))

mods = [["Module", "File", "Responsibility", "NLP concept"],
        ["PDF Loader", "backend/pdf_loader.py", "Text extraction with PyMuPDF; OCR for scanned pages; cleaning", "Preprocessing, OCR"],
        ["Chunker", "backend/chunker.py", "Sentence-aware ~180-word chunks, 1-sentence overlap", "Segmentation"],
        ["Retriever", "backend/retriever.py", "Embeds chunks, cosine search, representative/spread sampling", "Semantic search"],
        ["LLM Client", "backend/llm.py", "Talks to local Ollama; JSON mode; strips reasoning tags", "LLM, text generation"],
        ["Features", "backend/features.py", "Summary, questions, MCQs, grounded answers; JSON repair + retry", "Summarization, QG, RAG"],
        ["Web App", "app.py, templates/index.html", "Flask REST API and dark responsive UI", "-"]]
api = [["Endpoint", "Method", "Purpose"],
       ["/api/status", "GET", "Ollama online, installed models, loaded document info"],
       ["/api/model", "POST", "Switch local model"],
       ["/api/upload", "POST", "PDF > extract/OCR > chunk > embed"],
       ["/api/summary", "POST", "Bullet-point summary"], ["/api/questions", "POST", "Study questions (n)"],
       ["/api/mcqs", "POST", "MCQs: 4 options + answer index (n)"], ["/api/chat", "POST", "RAG answer + source passages"]]
tc = [["Test", "Verifies (design element)"],
      ["test_text_extraction", "PDF Loader: text layer, page count"],
      ["test_ocr_on_scanned_pdf", "PDF Loader: OCR of an image-only PDF (PyMuPDF + Tesseract)"],
      ["test_chunking_and_retrieval", "Chunker + Retriever: relevant chunk ranked first"],
      ["test_features", "Feature layer: summary, questions, MCQs, RAG answer"],
      ["test_bad_json_is_handled", "Robustness: malformed LLM JSON repaired or safely empty"],
      ["test_ollama_client_against_fake_server", "LLM client: payload (JSON mode, think off), tag stripping, model list"],
      ["test_ollama_offline_message", "LLM client: clear error when Ollama is not running"],
      ["test_flask_end_to_end", "REST API: upload validation, all features, error codes"]]
result = open(tests).read().strip().splitlines()[-1]

s = [Spacer(1, 3 * cm), Paragraph("Department of Computer Science, University of Karachi", ParagraphStyle("t0", parent=B, alignment=1, fontSize=13)),
     Spacer(1, .6 * cm), Paragraph("<b>PDFSage: An NLP-Based Intelligent PDF Assistant</b>", ParagraphStyle("t1", parent=ss["Title"], textColor=P)),
     Paragraph("System Design &amp; Test Report", ParagraphStyle("t2", parent=B, alignment=1, fontSize=14)), Spacer(1, 1.2 * cm),
     tbl([["Course", "CSSE 606: Topic of Current Interest III"], ["Submitted to", "Dr. M. Saeed"],
          ["Group members", "Alishna Azhar (B2211016013)<br/>Doshab Hussain (B2211016021)<br/>Huzaifa Arain (B2211016028)<br/>Hassaan Mushtaq (B2211016049)"]],
         [4 * cm, 11 * cm]), PageBreak(),
     Paragraph("1. Overview", H1),
     Paragraph("PDFSage turns a PDF (ideally 20-25 pages) into a summary, study questions, MCQs and a chat interface grounded in the document. "
               "Everything runs locally: a small LLM (about 3B parameters, e.g. Qwen 2.5 3B) served by Ollama, PyMuPDF for parsing and OCR, and a Flask web UI. No external API or key is used.", B),
     Paragraph("2. Architecture", H1), d, Paragraph("3. Components", H1), tbl(mods, [2.4 * cm, 4 * cm, 6.6 * cm, 3 * cm]),
     PageBreak(), Paragraph("4. Data Flow", H1),
     Paragraph("<b>Ingest:</b> upload > PyMuPDF text; pages with under 40 characters are OCR'd (Tesseract) > clean > chunk > embed > in-memory store.<br/>"
               "<b>Summary:</b> chunks closest to the document centroid (extractive selection) > LLM writes bullets (abstractive).<br/>"
               "<b>Questions / MCQs:</b> chunks sampled evenly across the document > LLM in JSON mode > validated (4 options, valid answer index), retried once on failure.<br/>"
               "<b>Chat (RAG):</b> query embedding > top-3 chunks > LLM answers using only that context; sources are shown in the UI.", B),
     Paragraph("5. REST API", H1), tbl(api, [3.4 * cm, 2 * cm, 10.6 * cm]), Paragraph("6. Design Decisions", H1),
     Paragraph("- Small local model: context kept to 4096 tokens, so prompts use 3-6 chunks of ~180 words.<br/>- JSON mode plus validation makes a 3B model reliable for MCQs.<br/>"
               "- Embeddings: MiniLM (sentence-transformers) with automatic TF-IDF fallback.<br/>- Single-user in-memory state is enough for a local desktop tool.", B),
     PageBreak(), Paragraph("7. Testing Against the Design", H1), tbl(tc, [6 * cm, 10 * cm]), Spacer(1, .4 * cm),
     Paragraph("<b>Result:</b> " + result, B),
     Paragraph("The Ollama protocol is tested against a mock server; output quality of the real model depends on the model installed on your PC.", B),
     Paragraph("8. Limitations and Future Work", H1),
     Paragraph("English-only OCR by default; one document at a time; long documents are summarized from representative chunks (map-reduce would improve coverage); add FAISS and multi-PDF support.", B)]
SimpleDocTemplate(out, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm).build(s)
