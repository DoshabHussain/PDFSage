# PDFSage – NLP-Based Intelligent PDF Assistant
CSSE 606, University of Karachi · 100% local: Ollama LLM, PyMuPDF OCR, Flask UI. No API keys.

## Setup (once)
1. Install Python 3.10+, [Ollama](https://ollama.com) and [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract) (Windows: UB-Mannheim installer, tick "add to PATH").
2. `ollama pull qwen2.5:3b`   (or `qwen3:4b`, `llama3.2:3b`)
3. `pip install -r requirements.txt`

## Run
```
python app.py        # open http://127.0.0.1:5000
```
Pick the model from the dropdown (top-right). Set `OLLAMA_MODEL` to change the default.

## Test
`python -m pytest -q`   (design report generator: `docs/gen_design_pdf.py`)

## Security (default = localhost only)
Only this PC can open the app. To use an iPhone on your Wi-Fi:
```
set PDFSAGE_TOKEN=<long-random-secret>          (Linux/Mac: export)
set PDFSAGE_ALLOWED_HOSTS=<this PC's LAN IP>
flask --app app run --host 0.0.0.0 --port 5000
```
Then open `http://<LAN IP>:5000/?token=<secret>` once on the phone. Use trusted Wi-Fi only (plain HTTP).
Run `python tests/pentest.py check` to re-run the 16 attack checks.
