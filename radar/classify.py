"""Deterministic keyword topic labelling. Bump RULES_VERSION when rules change."""
from __future__ import annotations

RULES_VERSION = "1"

DEFAULT_TOPICS: dict[str, list[str]] = {
    "fashion": ["fashion", "runway", "couture", "collection", "designer", "lookbook",
                "garment", "apparel", "textile", "luxury"],
    "retail": ["retailer", "retail", "store", "sales", "revenue", "e-commerce",
               "ecommerce", "shopper", "supply chain", "inventory"],
    "beauty": ["beauty", "makeup", "cosmetic", "skincare", "fragrance"],
    "ai-video": ["video generation", "text-to-video", "image-to-video", "generative video",
                 "diffusion", "cinematic", "shot synthesis"],
    "research": ["benchmark", "dataset", "pretraining", "fine-tuning", "arxiv"],
    "tooling": ["library", "sdk", "framework", "command-line", "cli"],
    "sustainability": ["sustainable", "recycled", "circular", "carbon", "esg"],
}
KIND_BASELINE = {"paper": ("research", 0.5), "repo": ("tooling", 0.4)}
MIN_SCORE = 0.2


def _hits(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term in lowered)


def classify(title: str, summary: str = "", topics: dict[str, list[str]] | None = None,
             kind: str = "news") -> list[dict]:
    """Score topics by weighted keyword hits; return the strongest few."""
    rules = topics or DEFAULT_TOPICS
    scores: dict[str, float] = {}
    for name, terms in rules.items():
        weight = 3 * _hits(title, terms) + _hits(summary, terms)
        if weight:
            scores[name] = min(1.0, weight / 6)
    baseline = KIND_BASELINE.get(kind)
    if baseline:
        name, score = baseline
        scores[name] = max(scores.get(name, 0.0), score)
    ordered = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    return [{"name": name, "score": round(score, 2)}
            for name, score in ordered if score >= MIN_SCORE][:3]
