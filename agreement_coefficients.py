from collections import Counter
from fractions import Fraction
from itertools import combinations


def coefficients(votes, categories):
    if not votes or len(votes[0]) < 2 or any(len(v) != len(votes[0]) for v in votes):
        raise ValueError("A complete panel with at least two raters is required")
    if len(categories) < 2 or len(set(categories)) != len(categories):
        raise ValueError("At least two distinct nominal categories are required")
    counts = Counter(v for row in votes for v in row)
    if not set(counts) <= set(categories) or any(not v for row in votes for v in row):
        raise ValueError("Unknown or missing category")
    n, r, q = len(votes), len(votes[0]), len(categories)
    pa = sum(sum(c * (c - 1) for c in Counter(row).values()) / (r * (r - 1)) for row in votes) / n
    proportions = {c: counts[c] / (n * r) for c in categories}
    kappa_pe = sum(p * p for p in proportions.values())
    ac1_pe = sum(p * (1 - p) for p in proportions.values()) / (q - 1)
    return {"subjects": n, "raters": r, "ratings": n * r, "category_count": q,
            "category_counts": {c: counts[c] for c in categories}, "category_proportions": proportions,
            "raw_agreement": pa, "fleiss_chance_agreement": kappa_pe,
            "fleiss_kappa": (pa - kappa_pe) / (1 - kappa_pe) if kappa_pe < 1 else None,
            "ac1_chance_agreement": ac1_pe, "gwet_ac1": (pa - ac1_pe) / (1 - ac1_pe),
            "disputed_subjects": sum(len(set(row)) > 1 for row in votes)}


def pairwise_exact_check(votes, categories):
    """Direct rater-pair enumeration and exact rational arithmetic."""
    pairs = [a == b for row in votes for a, b in combinations(row, 2)]
    pa = Fraction(sum(pairs), len(pairs))
    flat = [v for row in votes for v in row]
    probabilities = [Fraction(flat.count(c), len(flat)) for c in categories]
    pe_k = sum(p * p for p in probabilities)
    pe_a = (1 - pe_k) / (len(categories) - 1)
    return {"raw_agreement": float(pa),
            "fleiss_kappa": float((pa - pe_k) / (1 - pe_k)) if pe_k != 1 else None,
            "gwet_ac1": float((pa - pe_a) / (1 - pe_a))}
