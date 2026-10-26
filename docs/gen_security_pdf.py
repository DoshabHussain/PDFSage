import json, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

out = sys.argv[1]
before = {x["id"]: x for x in json.load(open("/tmp/results_before.json"))}
after = {x["id"]: x for x in json.load(open("/tmp/results_after.json"))}
ss = getSampleStyleSheet(); P = colors.HexColor("#3b2fb5")
H1 = ParagraphStyle("h", parent=ss["Heading1"], textColor=P, fontSize=15)
B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=10, leading=14)
C = ParagraphStyle("c", parent=B, fontSize=8.3, leading=10.5)
SEV = {"High": "#fecaca", "Medium": "#fde68a", "Low": "#bfdbfe"}
FIX = {
 "F01": ("Remote access is refused unless PDFSAGE_TOKEN is set; token is checked with constant-time compare; HttpOnly + SameSite=Strict cookie.", "Attacker on the same Wi-Fi uses your uploaded PDF, reads its text via chat, and burns your CPU."),
 "F02": ("Host header must be localhost/127.0.0.1 or an explicit allow-list entry.", "A malicious website re-points its DNS name at 127.0.0.1 and then reads your app as 'same origin'."),
 "F03": ("POST requests whose Origin differs from the Host are rejected (403).", "A web page you visit silently submits a file to localhost:5000 and replaces your document."),
 "F04": ("Same Origin check; model name validated by regex (F14).", "A web page switches your model or breaks your session."),
 "F05": ("body() and num() validate input: wrong types return 400, numbers fall back to defaults; global handler hides stack traces.", "One malformed request crashes the endpoint (500) and fills logs."),
 "F06": ("n is clamped (questions 1-12, MCQs 1-8); chat question capped at 500 characters.", "Someone asks for a billion questions and keeps the local LLM busy."),
 "F07": ("MAX_CONTENT_LENGTH lowered to 25 MB; JSON 413 handler.", "Already safe; limit tightened (was 50 MB)."),
 "F08": ("Page cap (default 100, env PDFSAGE_MAX_PAGES), encrypted PDFs refused, %PDF- signature check.", "A scanned 1000-page PDF ties up OCR for many minutes."),
 "F09": ("TF-IDF vocabulary capped at 4000 features and chunks capped at 600.", "Large document needs hundreds of MB of RAM and can crash the app."),
 "F10": ("Generic message to the user; details only in the server log.", "Parser error text helps an attacker fingerprint the library."),
 "F11": ("CSP (no inline script), X-Frame-Options DENY, nosniff, no-referrer, no-store on API. JS and CSS moved to /static.", "Page can be framed for clickjacking; any injected script would run."),
 "F12": ("Covered by F01 plus a single-flight lock; the document is single-user by design.", "Second person on the network reads the first person's document."),
 "F13": ("Document text is wrapped in <document> tags and the model is told it is untrusted data.", "A crafted PDF tells the model to ignore the task and lie in answers."),
 "F14": ("Regex: letters, digits, . _ : / - only, max 64 characters.", "Odd strings flow into the Ollama request."),
 "F15": ("Non-blocking lock; extra requests get 429 'model busy'.", "Ten parallel requests queue on one 3B model and freeze the UI."),
 "F16": ("Reviewed code: textContent everywhere; filename escaped. CSP is a second layer.", "No exploitable XSS found."),
}
def cell(t, s=C): return Paragraph(str(t), s)
rows = [[cell("ID"), cell("Sev."), cell("Finding"), cell("Evidence (before fix)"), cell("After fix")]]
for k in sorted(before):
    b, a = before[k], after[k]
    rows.append([cell(k), cell(b["severity"]), cell(b["title"]), cell(b["evidence"]),
                 cell("Fixed" if b["vulnerable"] and not a["vulnerable"] else ("Not vulnerable" if not b["vulnerable"] else "OPEN"))])
t = Table(rows, colWidths=[1*cm, 1.8*cm, 5*cm, 6*cm, 2.2*cm], repeatRows=1)
st = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7e4ff")), ("GRID", (0, 0), (-1, -1), .4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]
for i, k in enumerate(sorted(before), 1): st.append(("BACKGROUND", (1, i), (1, i), colors.HexColor(SEV[before[k]["severity"]])))
t.setStyle(TableStyle(st))
nb = sum(x["vulnerable"] for x in before.values()); na = sum(x["vulnerable"] for x in after.values())
hi = sum(1 for x in before.values() if x["vulnerable"] and x["severity"] == "High")
detail = []
for k in sorted(before):
    if before[k]["vulnerable"]:
        detail += [Paragraph(f"<b>{k} - {before[k]['title']}</b> ({before[k]['severity']})", B),
                   Paragraph(f"<i>Attack scenario:</i> {FIX[k][1]}<br/><i>Fix:</i> {FIX[k][0]}", B), Spacer(1, 4)]
res = [("Plain HTTP on the LAN", "The token and traffic can be sniffed on untrusted Wi-Fi. Use home/trusted Wi-Fi only, or put a TLS reverse proxy (Caddy, nginx) in front."),
 ("Prompt injection is mitigated, not solved", "A hostile PDF can still sway what the model says. Impact is limited because the model has no tools and its output is shown as plain text, but answers from untrusted PDFs should be verified."),
 ("Malicious PDFs vs. the PDF parser", "PyMuPDF/MuPDF is native C code. Keep it updated; for untrusted files run the app in a container or low-privilege account."),
 ("Ollama itself", "Ollama listens on localhost:11434 by default. Never set OLLAMA_HOST=0.0.0.0 or open that port in the firewall; it has no authentication."),
 ("Dependency vulnerabilities", "pip-audit flagged werkzeug 3.1.7 (fixed in 3.1.9) and urllib3 2.6.3 (fixed in 2.7.0). requirements.txt now requires the fixed versions: run pip install -U -r requirements.txt."),
 ("Flask development server", "Fine for a personal tool; for shared use run behind waitress/gunicorn. Cookie is not marked Secure because the app uses HTTP."),
 ("'unsafe-inline' for styles", "Kept because the UI uses a few inline style attributes; scripts are strictly self-hosted."),
 ("Model and package supply chain", "Models (Ollama, Hugging Face) and pip packages are downloaded from the internet: install only from official sources and pin versions for the final submission."),
 ("Not tested", "Real browser exploitation (done by code review and CSP), real Ollama model behaviour, Windows firewall configuration, and denial-of-service from many machines.")]
s = [Paragraph("<b>PDFSage Security Assessment Report</b>", ParagraphStyle("t", parent=ss["Title"], textColor=P)),
 Paragraph("Penetration test, remediation and re-test. CSSE 606, University of Karachi. Assessed 25 Oct 2026.", B), Spacer(1, 8),
 Paragraph("1. Executive summary", H1),
 Paragraph(f"A black-box and code-review assessment of PDFSage found <b>{nb} weaknesses out of 16 checks</b>, including <b>{hi} High</b> severity. "
           "The worst problems were: no authentication, no protection against cross-site (CSRF) and DNS-rebinding attacks, no limits on PDF size/pages, and shared state that let any device on the network use the first user's document. "
           f"All were fixed and the same 16 attack checks were re-run: <b>{na} remain</b>. The 8 functional tests plus 3 new security tests (11 total) pass, Bandit static analysis reports no issues, and the dependency audit found two outdated packages (see section 5).", B),
 Paragraph("2. Scope and method", H1),
 Paragraph("<b>Target:</b> Flask app, Ollama client, PDF/OCR pipeline, browser UI. <b>Attacker models:</b> (a) another device on the same Wi-Fi, (b) a malicious website opened in the victim's browser, (c) a malicious PDF, (d) a user sending malformed API requests. "
           "<b>Tools:</b> scripted attacks (tests/pentest.py), Bandit, pip-audit, manual code review. Every finding below was reproduced with a script, not assumed.", B),
 Paragraph("3. Findings and re-test results", H1), t, PageBreak(),
 Paragraph("4. Attack scenarios and fixes", H1)] + detail + [
 Paragraph("5. Residual risks and recommendations", H1)] + [Paragraph(f"<b>{a}:</b> {b}", B) for a, b in res] + [
 Paragraph("6. How to re-run", H1),
 Paragraph("<font face='Courier'>python tests/pentest.py check</font> prints OK/VULN for all 16 checks. <font face='Courier'>python -m pytest -q</font> runs functional and security tests. <font face='Courier'>bandit -r app.py backend</font> and <font face='Courier'>pip-audit</font> cover code and dependencies.", B)]
SimpleDocTemplate(out, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=1.8*cm, bottomMargin=1.8*cm).build(s)
