"""Workers for the Day 8 Supervisor-Workers RAG pipeline."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import TypedDict


DATA_PATH = Path(__file__).parent / "data" / "corpus.json"
TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


class Evidence(TypedDict):
    content: str
    score: float
    metadata: dict


def load_corpus() -> list[dict]:
    """Load the self-contained Day 8 sample corpus."""
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


def semantic_worker(query: str, top_k: int = 5) -> list[Evidence]:
    """Retrieve by cosine similarity over token-frequency vectors."""
    query_vector = Counter(tokenize(query))
    if not query_vector:
        return []

    results: list[Evidence] = []
    for document in load_corpus():
        document_vector = Counter(tokenize(document["content"]))
        score = _cosine_similarity(query_vector, document_vector)
        if score <= 0:
            continue
        results.append(_evidence(document, score, "semantic"))
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


def lexical_worker(query: str, top_k: int = 5) -> list[Evidence]:
    """Retrieve with a compact BM25 implementation."""
    corpus = load_corpus()
    tokenized_docs = [tokenize(item["content"]) for item in corpus]
    query_terms = tokenize(query)
    if not query_terms:
        return []

    average_length = sum(map(len, tokenized_docs)) / max(len(tokenized_docs), 1)
    document_frequency = Counter(
        term for tokens in tokenized_docs for term in set(tokens)
    )
    results: list[Evidence] = []
    for document, tokens in zip(corpus, tokenized_docs):
        frequencies = Counter(tokens)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse_document_frequency = math.log(
                1 + (len(corpus) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            denominator = frequency + 1.5 * (
                1 - 0.75 + 0.75 * len(tokens) / max(average_length, 1)
            )
            score += inverse_document_frequency * frequency * 2.5 / denominator
        if score > 0:
            results.append(_evidence(document, score, "lexical"))
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


def reciprocal_rank_fusion(result_lists: list[list[Evidence]]) -> list[Evidence]:
    """Fuse worker rankings while preserving source metadata."""
    scores: dict[str, float] = defaultdict(float)
    documents: dict[str, Evidence] = {}
    retrievers: dict[str, set[str]] = defaultdict(set)

    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            document_id = str(item["metadata"]["id"])
            scores[document_id] += 1.0 / (60 + rank)
            documents[document_id] = item
            retrievers[document_id].add(str(item["metadata"]["retriever"]))

    fused: list[Evidence] = []
    for document_id, item in documents.items():
        metadata = dict(item["metadata"])
        metadata["retrievers"] = sorted(retrievers[document_id])
        metadata["fusion"] = "rrf"
        fused.append(
            {
                "content": item["content"],
                "score": scores[document_id],
                "metadata": metadata,
            }
        )
    return sorted(fused, key=lambda item: item["score"], reverse=True)


def citation_worker(query: str, evidence: list[Evidence], top_k: int = 3) -> str:
    """Produce a grounded extractive answer with citations."""
    ranked = _rerank_by_query_overlap(query, evidence)[:top_k]
    if not ranked or ranked[0]["score"] <= 0:
        return (
            "I cannot verify this information.\n\n"
            "Giới hạn: Không tìm thấy bằng chứng phù hợp trong corpus Day 8."
        )

    query_terms = set(tokenize(query))
    claims: list[str] = []
    sources: list[str] = []
    for item in ranked:
        metadata = item["metadata"]
        sentence = _best_sentence(item["content"], query_terms)
        citation = f"[{metadata['title']}, {metadata['year']}]"
        if sentence:
            claims.append(f"{sentence} {citation}")
        sources.append(f"- {citation} {metadata['source']}")

    return (
        "Trả lời:\n"
        + " ".join(claims)
        + "\n\nNguồn:\n"
        + "\n".join(sources)
        + "\n\nGiới hạn: Chỉ sử dụng corpus mẫu được đóng gói trong assignment."
    )


def _cosine_similarity(left: Counter, right: Counter) -> float:
    dot_product = sum(value * right[term] for term, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _evidence(document: dict, score: float, retriever: str) -> Evidence:
    return {
        "content": document["content"],
        "score": float(score),
        "metadata": {
            "id": document["id"],
            "title": document["title"],
            "year": document["year"],
            "source": document["source"],
            "retriever": retriever,
        },
    }


def _rerank_by_query_overlap(
    query: str,
    evidence: list[Evidence],
) -> list[Evidence]:
    query_terms = set(tokenize(query))
    reranked: list[Evidence] = []
    for item in evidence:
        overlap = len(query_terms & set(tokenize(item["content"])))
        score = float(item["score"]) + 0.05 * overlap
        reranked.append({**item, "score": score})
    return sorted(reranked, key=lambda item: item["score"], reverse=True)


def _best_sentence(content: str, query_terms: set[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", content)
    return max(
        sentences,
        key=lambda sentence: len(query_terms & set(tokenize(sentence))),
        default="",
    ).strip()
