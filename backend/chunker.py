import re


def chunk_text(text: str, max_words: int = 180, overlap: int = 1) -> list[str]:
    """Sentence-aware chunks with small overlap."""
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if s.strip()]
    chunks, cur, n = [], [], 0
    for s in sents:
        w = len(s.split())
        if n + w > max_words and cur:
            chunks.append(" ".join(cur))
            cur = cur[-overlap:] if overlap else []
            n = sum(len(x.split()) for x in cur)
        cur.append(s)
        n += w
    if cur:
        chunks.append(" ".join(cur))
    return chunks
