"""Scrape framework docs, chunk them, and embed into ChromaDB.  Run: python -m rag.ingest"""
import hashlib

import chromadb
import requests
from bs4 import BeautifulSoup

import config


def get_collection():
    client = chromadb.PersistentClient(path=str(config.VECTORDB_DIR))
    return client.get_or_create_collection(config.COLLECTION)


def chunk(text: str, size: int = 1200) -> list[str]:
    chunks, buf = [], ""
    for para in (p.strip() for p in text.split("\n")):
        if not para:
            continue
        if len(buf) + len(para) > size and buf:
            chunks.append(buf)
            buf = buf[-200:]  # small overlap for context
        buf += para + "\n"
    if buf.strip():
        chunks.append(buf)
    return chunks


def fetch(url: str) -> str:
    html = requests.get(url, timeout=30, headers={"User-Agent": "app-factory/1.0"}).text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body
    return main.get_text("\n") if main else ""


def add(col, source: str, text: str) -> int:
    parts = chunk(text)
    if not parts:
        return 0
    ids = [hashlib.md5(f"{source}-{i}-{p[:50]}".encode()).hexdigest() for i, p in enumerate(parts)]
    col.upsert(ids=ids, documents=parts, metadatas=[{"source": source}] * len(parts))
    return len(parts)


def main():
    col = get_collection()
    total = 0
    for url in config.DOC_URLS:
        try:
            n = add(col, url, fetch(url))
            print(f"OK   {n:3d} chunks  {url}")
            total += n
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {url}: {e}")
    for f in config.DOCS_DIR.glob("*"):          # your own .md/.txt docs
        if f.suffix in {".md", ".txt"}:
            n = add(col, f.name, f.read_text(encoding="utf-8"))
            print(f"OK   {n:3d} chunks  {f.name}")
            total += n
    print(f"Done. {total} chunks, collection size: {col.count()}")


if __name__ == "__main__":
    main()
