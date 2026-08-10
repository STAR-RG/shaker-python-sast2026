#!/usr/bin/env python3
"""
Figures for the paper, regenerated from results/ CSVs (+ fetched metadata).

Outputs to paper/img/:
    fig_detection_rate.png  : detection rate by technique with 95% Wilson CIs
    fig_overlap.png         : Shaker vs ReRun detection overlap (paired counts)
    fig_categories.png      : flakiness-category distribution + reproduction
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analysis.load import load_paired
from analysis.stats_util import Prop

IMG = Path(__file__).resolve().parent.parent / "paper" / "img"


def fig_detection_rate(df):
    n = len(df)
    props = {
        "ReRun\n": Prop(int(df.rerun_flaky.sum()), n),
        "Shaker\n": Prop(int(df.shaker_flaky.sum()), n),
        "Either": Prop(int(df.either_flaky.sum()), n),
    }
    labels = list(props)
    rates = [p.rate * 100 for p in props.values()]
    errs = [[(p.rate - p.ci[0]) * 100 for p in props.values()],
            [(p.ci[1] - p.rate) * 100 for p in props.values()]]
    fig, ax = plt.subplots(figsize=(5, 3.2))
    bars = ax.bar(labels, rates, yerr=errs, capsize=4,
                  color=["#7fa6c9", "#c98b7f", "#9ec97f"], edgecolor="black", linewidth=0.6)
    for bar, p in zip(bars, props.values()):
        ax.text(bar.get_x() + bar.get_width() / 2, p.rate * 100 + 3,
                f"      {p.k}", ha="center", fontsize=9)
    ax.set_ylabel("Detection rate (recall) %")
    ax.set_ylim(0, 70)
    ax.set_title(f"Detection on {n} ground-truth flaky tests")
    fig.tight_layout()
    fig.savefig(IMG / "fig_detection_rate.png", dpi=200)
    plt.close(fig)


def fig_overlap(df):
    both = int((df.shaker_flaky & df.rerun_flaky).sum())
    s_only = int((df.shaker_flaky & ~df.rerun_flaky).sum())
    r_only = int((~df.shaker_flaky & df.rerun_flaky).sum())
    neither = int((~df.shaker_flaky & ~df.rerun_flaky).sum())
    fig, ax = plt.subplots(figsize=(5, 3.2))
    cats = ["Both", "Shaker only", "ReRun only", "Neither"]
    vals = [both, s_only, r_only, neither]
    ax.bar(cats, vals, color=["#9ec97f", "#c98b7f", "#7fa6c9", "#cccccc"],
           edgecolor="black", linewidth=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 1, str(v), ha="center", fontsize=9)
    ax.set_ylabel("Tests")
    ax.set_title("Paired detection overlap (Shaker vs. ReRun)")
    fig.tight_layout()
    fig.savefig(IMG / "fig_overlap.png", dpi=200)
    plt.close(fig)


def fig_categories(df):
    sub = df[df.category.notna()]
    if sub.empty:
        return
    agg = sub.groupby("category").agg(total=("category", "size"),
                                      repro=("either_flaky", "sum"))
    agg = agg.sort_values("total", ascending=True)
    fig, ax = plt.subplots(figsize=(5, 3.4))
    y = range(len(agg))
    ax.barh(list(y), agg["total"], color="#cccccc", edgecolor="black",
            linewidth=0.6, label="labelled")
    ax.barh(list(y), agg["repro"], color="#c98b7f", edgecolor="black",
            linewidth=0.6, label="reproduced")
    ax.set_yticks(list(y))
    ax.set_yticklabels(agg.index)
    ax.set_xlabel("Tests")
    ax.set_title("Flakiness category vs. reproduction")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(IMG / "fig_categories.png", dpi=200)
    plt.close(fig)


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    df = load_paired()
    fig_detection_rate(df)
    fig_overlap(df)
    fig_categories(df)
    print(f"wrote figures to {IMG}")


if __name__ == "__main__":
    main()
