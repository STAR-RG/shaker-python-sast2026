#!/usr/bin/env python3
"""Small statistics helpers shared across the RQ scripts."""
from __future__ import annotations

import math
from dataclasses import dataclass

from scipy import stats


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact (binomial) two-sided McNemar p-value on discordant counts b, c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = stats.binom.cdf(k, n, 0.5) * 2
    return min(1.0, p)


def mcnemar_cc(b: int, c: int) -> tuple[float, float]:
    """Continuity-corrected McNemar chi-square statistic and p-value."""
    n = b + c
    if n == 0:
        return (0.0, 1.0)
    chi2 = (abs(b - c) - 1) ** 2 / n
    p = stats.chi2.sf(chi2, df=1)
    return (chi2, p)


def cliffs_delta(a, b) -> tuple[float, str]:
    """Cliff's delta effect size for two samples, with magnitude label."""
    a, b = list(a), list(b)
    if not a or not b:
        return (float("nan"), "n/a")
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    d = (gt - lt) / (len(a) * len(b))
    ad = abs(d)
    mag = ("negligible" if ad < 0.147 else
           "small" if ad < 0.33 else
           "medium" if ad < 0.474 else "large")
    return (d, mag)


@dataclass
class Prop:
    k: int
    n: int

    @property
    def rate(self) -> float:
        return self.k / self.n if self.n else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson_ci(self.k, self.n)

    def pct(self) -> str:
        lo, hi = self.ci
        return f"{self.rate*100:.1f}\\% (95\\% CI {lo*100:.1f}--{hi*100:.1f})"
