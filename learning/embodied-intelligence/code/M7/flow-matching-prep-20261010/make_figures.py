"""AI-authored r1 teaching figures from saved real fit and analytic references.

All scientific plotting code lives under code/. English figure labels avoid
font portability problems; Chinese reading guide/captions are in 07 report.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from teacher_cfm import PREP_DIR, oracle_exact


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=10)


def save(fig, output_base):
    fig.savefig(output_base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def create_figures(run_dir, figure_dir):
    run_dir, figure_dir = Path(run_dir), Path(figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)
    summary = json.loads((run_dir / "summary-r1.json").read_text(encoding="utf-8"))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.titlesize": 12, "axes.labelsize": 11, "legend.fontsize": 10,
                         "svg.fonttype": "none", "axes.axisbelow": True})
    blue, orange, gray = "#0072B2", "#D55E00", "#555555"

    t = np.linspace(0, 1, 301)
    z = np.tile([-1.0, 1.0], (len(t), 1))
    c = np.ones(len(t), dtype=np.int64)
    trajectory = oracle_exact(z, t, c)
    straight = (1 - t[:, None]) * z + t[:, None] * trajectory[-1]
    fig, ax = plt.subplots(figsize=(8.1, 4.8), constrained_layout=True)
    ax.plot(trajectory[:, 0], trajectory[:, 1], color=blue, linewidth=2.5,
            label="Oracle marginal ODE (analytic)")
    ax.plot(straight[:, 0], straight[:, 1], color=gray, linestyle="--", linewidth=2,
            label="Straight interpolation: same endpoints")
    selected_t = np.array([0, 0.25, 0.5, 0.75, 1])
    positions = oracle_exact(np.tile([-1.0, 1.0], (5, 1)), selected_t, np.ones(5, dtype=int))
    ax.scatter(positions[:, 0], positions[:, 1], color=blue, edgecolors="white", s=50, zorder=5)
    for ti, xy in zip(selected_t, positions):
        dy = 14 if ti in (0, 0.5) else -20
        ax.annotate(f"t={ti:g}", xy=xy, xytext=(3, dy), textcoords="offset points", color=blue, fontsize=10)
    ax.scatter([0.25], [0.75], marker="s", color=gray, s=38, zorder=5)
    ax.annotate("line midpoint (0.25, 0.75)", (0.25, 0.75), xytext=(12, 20),
                textcoords="offset points", fontsize=10, color=gray,
                arrowprops={"arrowstyle": "-", "color": gray})
    ax.annotate("", xy=trajectory[176], xytext=trajectory[158],
                arrowprops={"arrowstyle": "->", "color": blue, "lw": 2})
    ax.set(xlabel="State coordinate x[0] (toy units)", ylabel="State coordinate x[1] (toy units)",
           title="Same endpoints, different paths | c=1, z=(-1,1)", xlim=(-1.3, 1.8), ylim=(0.30, 1.25))
    ax.text(0.02, 0.03, "t: generation time, 0=noise, 1=data\nAxes: two state coordinates, not time", transform=ax.transAxes,
            fontsize=10, color="#333333", va="bottom")
    ax.legend(loc="upper right", frameon=False)
    style_axes(ax)
    save(fig, figure_dir / "01-trajectories")

    rows = summary["samples"]
    n = np.array([r["n_steps"] for r in rows])
    variances = np.array([r["oracle_theory_coordinate_variance"] for r in rows])
    oracle_errors = [r["oracle_euler_vs_exact"]["coordinate_rmse"] for r in rows]
    learned_exact_errors = [r["learned_vs_oracle_exact"]["coordinate_rmse"] for r in rows]
    learned_ref_errors = [r["learned_vs_double_reference"]["coordinate_rmse"] for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), constrained_layout=True)
    ax = axes[0]
    ax.plot(n, variances, "o-", color=blue, label="Oracle Euler: theoretical variance", linewidth=2)
    ax.axhline(0.25, color=gray, linestyle="--", label="Target variance = 0.25")
    ax.annotate("N=1: variance=0", (1, 0), xytext=(3.8, 0.06),
                arrowprops={"arrowstyle": "->", "color": gray}, fontsize=10)
    ax.set(xlabel="Euler steps N = NFE per sample", ylabel="Endpoint coordinate variance", title="A  Pure integration distortion")
    ax.set_xscale("log", base=2)
    ax.set_xticks(n, [str(i) for i in n])
    ax.set_ylim(-0.01, 0.29)
    ax.legend(frameon=False, loc="upper left", fontsize=9)

    ax = axes[1]
    with np.load(run_dir / "paired-generation-r1.npz") as archive:
        labels = archive["c"]
        sample = archive["learned_n128"]
        # Deterministic first 180 per condition; not another generated batch.
        for label, color, marker in ((0, blue, "o"), (1, orange, "^")):
            subset = sample[labels == label][:180]
            ax.scatter(subset[:, 0], subset[:, 1], s=12, alpha=0.5, color=color, marker=marker,
                       label=f"Learned fit, c={label} (180 shown)")
            center = summary["target_class_statistics"][str(label)]["mean"]
            circle = plt.Circle(center, 0.5, fill=False, linestyle="--", edgecolor=color, linewidth=1.7)
            ax.add_patch(circle)
            ax.scatter(*center, marker="x", color=color, s=65, linewidth=2)
    ax.set(xlabel="State coordinate x[0] (toy units)", ylabel="State coordinate x[1] (toy units)",
           title="B  Actual CFM fit: N=128 samples", xlim=(-3.8, 3.8), ylim=(-1.9, 1.9))
    ax.set_aspect("equal", adjustable="box")
    ax.legend(frameon=False, loc="upper center", fontsize=9)
    ax.text(0.01, 0.02, "Each c evaluated separately: n=4096\nDashed radius=0.5: target SD, not a confidence region",
            transform=ax.transAxes, fontsize=8.5, color=gray)

    ax = axes[2]
    ax.plot(n, oracle_errors, "o-", color=blue, linewidth=2, label="Oracle Euler vs analytic exact")
    ax.plot(n, learned_ref_errors, "s--", color=orange, linewidth=2, label="Learned Euler vs learned N=4096")
    ax.plot(n, learned_exact_errors, "^:", color="#009E73", linewidth=2, label="Learned Euler vs oracle exact")
    ax.set(xlabel="Euler steps N = NFE per sample", ylabel="Paired endpoint coordinate RMSE",
           title="C  Keep field and z/c fixed")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(n, [str(i) for i in n])
    ax.legend(frameon=False, loc="upper right", fontsize=8.7)
    ax.text(0.02, 0.03, "Same paired noise: n=8192\n2D norm-RMS = sqrt(2) x coordinate RMSE",
            transform=ax.transAxes, fontsize=8.5, color=gray)
    for ax in axes:
        style_axes(ax)
    save(fig, figure_dir / "02-sampling-comparison")
    print(json.dumps({"figures": [str(p) for p in sorted(figure_dir.glob("*.png"))],
                      "source": str(run_dir / "summary-r1.json"), "revision": summary["revision"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=PREP_DIR / "teacher-run")
    parser.add_argument("--figure-dir", type=Path, default=PREP_DIR / "figures")
    args = parser.parse_args()
    create_figures(args.run_dir, args.figure_dir)
