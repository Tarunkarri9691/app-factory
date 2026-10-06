"""query(text) -> top-k doc chunks as one string. Returns '' if RAG isn't set up or fails."""


def query(text: str, k: int = 4) -> str:
    if not text.strip():
        return ""
    try:
        from rag.ingest import get_collection   # imported lazily: RAG problems never crash the pipeline
        col = get_collection()
        n = col.count()
        if n == 0:
            return ""
        res = col.query(query_texts=[text], n_results=min(k, n))
        return "\n\n---\n".join(
            f"[{m['source']}]\n{d}" for d, m in zip(res["documents"][0], res["metadatas"][0])
        )
    except Exception:  # noqa: BLE001
        return ""
