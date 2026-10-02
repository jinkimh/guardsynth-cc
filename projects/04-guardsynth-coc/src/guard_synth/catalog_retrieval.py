"""Deterministic retrieval interfaces for M14 source-catalog candidates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log, sqrt
import re
from typing import Callable, Protocol

from .source_catalog import SourceCatalog


_TOKEN = re.compile(r"[A-Za-z0-9_가-힣]+")


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    slice_hint: str
    scene_predicates: tuple[str, ...]
    scene_tags: tuple[str, ...]
    coc_concepts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievedRule:
    rule_id: str
    score: float
    backend: str


class CatalogRetriever(Protocol):
    backend_id: str

    def retrieve(
        self,
        catalog: SourceCatalog,
        query: RetrievalQuery,
    ) -> tuple[RetrievedRule, ...]: ...


def _rules(catalog: SourceCatalog, slice_hint: str) -> list[dict]:
    return [
        rule for rule in catalog.raw["rule_templates"]
        if rule["slice"] == slice_hint
    ]


class GraphPredicateRetriever:
    backend_id = "GRAPH_PREDICATE_V0.1"

    def retrieve(self, catalog: SourceCatalog, query: RetrievalQuery) -> tuple[RetrievedRule, ...]:
        predicates = set(query.scene_predicates)
        records = [
            RetrievedRule(
                rule["rule_id"],
                float(sum(item in predicates for item in rule["required_predicate_refs"])),
                self.backend_id,
            )
            for rule in _rules(catalog, query.slice_hint)
        ]
        return tuple(sorted(records, key=lambda item: (-item.score, item.rule_id)))


def _tokens(value: str) -> list[str]:
    return [token.casefold() for token in _TOKEN.findall(value)]


def _rule_text(rule: dict) -> str:
    return " ".join([
        rule["rule_id"],
        rule["slice"],
        rule["family"],
        rule["scope"],
        *rule["preconditions"],
        *rule["exceptions"],
        *rule["roles"],
        *rule["required_predicate_refs"],
    ])


class BM25CatalogRetriever:
    backend_id = "BM25_CATALOG_V0.1"

    def __init__(self, *, k1: float = 1.2, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def retrieve(self, catalog: SourceCatalog, query: RetrievalQuery) -> tuple[RetrievedRule, ...]:
        rules = _rules(catalog, query.slice_hint)
        documents = [Counter(_tokens(_rule_text(rule))) for rule in rules]
        lengths = [sum(document.values()) for document in documents]
        average = sum(lengths) / len(lengths) if lengths else 1.0
        terms = set(
            token
            for value in (
                *query.scene_predicates,
                *query.scene_tags,
                *query.coc_concepts,
            )
            for token in _tokens(value)
        )
        document_frequency = {
            term: sum(term in document for document in documents) for term in terms
        }
        records = []
        for rule, document, length in zip(rules, documents, lengths):
            score = 0.0
            for term in terms:
                frequency = document[term]
                if not frequency:
                    continue
                frequency_in_documents = document_frequency[term]
                inverse = log(1.0 + (len(documents) - frequency_in_documents + 0.5) / (frequency_in_documents + 0.5))
                denominator = frequency + self.k1 * (1.0 - self.b + self.b * length / average)
                score += inverse * frequency * (self.k1 + 1.0) / denominator
            records.append(RetrievedRule(rule["rule_id"], score, self.backend_id))
        return tuple(sorted(records, key=lambda item: (-item.score, item.rule_id)))


class DenseCatalogRetriever:
    """Adapter for a caller-supplied deterministic embedding function."""

    backend_id = "DENSE_ADAPTER_V0.1"

    def __init__(self, embed: Callable[[str], tuple[float, ...]]) -> None:
        self.embed = embed

    @staticmethod
    def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if len(left) != len(right) or not left:
            raise ValueError("DENSE_EMBEDDING_DIMENSION_MISMATCH")
        denominator = sqrt(sum(x * x for x in left) * sum(x * x for x in right))
        return sum(x * y for x, y in zip(left, right)) / denominator if denominator else 0.0

    def retrieve(self, catalog: SourceCatalog, query: RetrievalQuery) -> tuple[RetrievedRule, ...]:
        query_text = " ".join((
            *query.scene_predicates,
            *query.scene_tags,
            *query.coc_concepts,
        ))
        query_vector = self.embed(query_text)
        records = [
            RetrievedRule(
                rule["rule_id"],
                self._cosine(query_vector, self.embed(_rule_text(rule))),
                self.backend_id,
            )
            for rule in _rules(catalog, query.slice_hint)
        ]
        return tuple(sorted(records, key=lambda item: (-item.score, item.rule_id)))
