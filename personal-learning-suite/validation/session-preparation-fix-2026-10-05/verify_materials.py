"""Check the fictional model materials and render the actual static inputs.

Finite checks support the examples/plots, not the general proof or learning gains.
"""
from pathlib import Path
from fractions import Fraction
import cmath
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent
UNIT = OUT / "first-unit"
FONT = Path("C:/Windows/Fonts/msyh.ttc")
if FONT.is_file():
    font_manager.fontManager.addfont(str(FONT))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(FONT)).get_name()
plt.rcParams["axes.unicode_minus"] = False


def original_steps(a, k, r, x0, steps):
    x = x0
    values = [x - r]
    for _ in range(steps):
        u = k * (r - x)
        x = x + a * u
        values.append(x - r)
    return values


def main():
    UNIT.mkdir(parents=True, exist_ok=True)
    checks = []
    F = Fraction
    sample_q = [F(0), F(1, 2), F(1), F(6, 5), F(2), F(11, 5)]
    for q in sample_q:
        for e0 in [F(1), F(-3), F(0)]:
            a = F(2)
            k = q / a
            r = F(10)
            actual = original_steps(a, k, r, r + e0, 24)
            expected = [(1 - q) ** t * e0 for t in range(25)]
            assert actual == expected, (q, e0)
            checks.append({"case": f"original-model/q={q}/e0={e0}", "pass": True})
    worked = original_steps(F(1), F(1, 2), F(10), F(0), 2)
    assert worked == [F(-10), F(-5), F(-5, 2)]
    checks.append({"case": "worked-example/0-to-5-to-7.5", "pass": True})
    assert original_steps(F(1), F(11, 5), F(0), F(1), 2) == [F(1), F(-6, 5), F(36, 25)]
    checks.append({"case": "local-direction-does-not-imply-contraction", "pass": True})

    q = F(6, 5)
    previous, current = F(1), F(1)
    delayed = [current]
    for _ in range(80):
        previous, current = current, current - q * previous
        delayed.append(current)
    assert delayed[1:3] == [F(-1, 5), F(-7, 5)]
    roots = [(1 + cmath.sqrt(1 - 4 * float(q))) / 2,
             (1 - cmath.sqrt(1 - 4 * float(q))) / 2]
    assert all(abs(z * z - z + float(q)) < 1e-12 for z in roots)
    assert all(abs(abs(z) - float(q) ** 0.5) < 1e-12 and abs(z) > 1 for z in roots)
    checks.append({"case": "delay-counterexample/initial-values-and-characteristic-roots", "pass": True})

    fig, ax = plt.subplots(figsize=(11, 3.8), dpi=150)
    fig.patch.set_facecolor("#f6f8fb")
    ax.set_facecolor("#f6f8fb")
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 3.6)
    ax.axis("off")
    boxes = [(0.3, "目标与当前状态\nr, x[t]"), (3.0, "比较偏差\nr − x[t]"),
             (5.7, "生成命令\nu[t] = k(r − x[t])"),
             (8.4, "执行与下一状态\nx[t+1] = x[t] + a u[t]")]
    for x, label in boxes:
        ax.add_patch(FancyBboxPatch((x, 1.9), 2.25, 0.95,
                                  boxstyle="round,pad=0.09", facecolor="white", edgecolor="#23486b"))
        ax.text(x + 1.125, 2.375, label, ha="center", va="center", fontsize=10)
    for x in [2.55, 5.25, 7.95]:
        ax.annotate("", xy=(x + 0.4, 2.375), xytext=(x + 0.07, 2.375),
                    arrowprops={"arrowstyle": "->", "color": "#23486b", "lw": 1.7})
    ax.plot([9.525, 9.525, 1.425, 1.425], [1.82, 1.0, 1.0, 1.72], color="#23486b", lw=1.6)
    ax.annotate("", xy=(1.425, 1.82), xytext=(1.425, 1.65),
                arrowprops={"arrowstyle": "->", "color": "#23486b", "lw": 1.6})
    ax.text(5.5, 0.7, "进入下一步：把 x[t+1] 用作新的当前状态，r 保持固定", ha="center", fontsize=10)
    ax.text(5.5, 3.28, "离散教学模型：偏差 → 命令 → 状态更新 → 再比较", ha="center", fontsize=13)
    fig.tight_layout()
    fig.savefig(UNIT / "feedback-loop.png")
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(9, 6), dpi=150, sharex=True)
    colors = ["#236aab", "#218879", "#b77b16", "#bb3e52"]
    rows = []
    for ax, q, color in zip(axes.flat, [F(1, 2), F(6, 5), F(2), F(11, 5)], colors):
        values = original_steps(F(1), q, F(0), F(1), 12)
        for t, e in enumerate(values):
            rows.append({"q": str(q), "t": t, "error_exact": str(e), "error": float(e)})
        ax.plot(range(13), [float(v) for v in values], "o-", color=color, markersize=4)
        ax.axhline(0, color="#687580", lw=0.7)
        ax.set_title(f"q = {float(q):g}")
        ax.set_xlabel("离散步 t")
        ax.set_ylabel("误差 e[t]")
        ax.grid(alpha=0.2)
        if q < 2:
            ax.set_ylim(-1.25, 1.25)
    fig.suptitle("同一无延迟模型，e[0]=1：有限轨迹用于核对，不替代一般证明", fontsize=11)
    fig.tight_layout()
    fig.savefig(UNIT / "error-trajectories.png")
    plt.close(fig)
    with (UNIT / "trajectory-data.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["q", "t", "error_exact", "error"])
        writer.writeheader()
        writer.writerows(rows)
    result = {"status": "pass", "checks": checks, "checks_passed": len(checks),
              "plot_data_rows": len(rows), "static_images_generated": 2,
              "limitations": ["General proof checked in teacher-reference; finite tests do not prove it",
                              "No real learner or learning-effect validation", "No runtime/API changes"]}
    (OUT / "material-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["status", "checks_passed", "plot_data_rows", "static_images_generated"]}))


if __name__ == "__main__":
    main()
