"""AI-authored static deployment diagram, revision1, 2026-10-09.

Definitions: preparation 01/02; scope: online information interfaces only.
No simulated learner responses or training/control results.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.font_manager import FontProperties


BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "artifacts/preparation-tests/2026-10-09-rssm-01a11f30/11-online-dataflow.png"
FONT = FontProperties(fname="C:/Windows/Fonts/msyh.ttc")
fig, ax = plt.subplots(figsize=(16, 10), dpi=130)
fig.patch.set_facecolor("#f6f8fc")
ax.set_facecolor("#f6f8fc")
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis("off")


def text(x, y, value, size=13, color="#203149", weight="normal", ha="center"):
    ax.text(x, y, value, fontproperties=FONT, fontsize=size, color=color,
            weight=weight, ha=ha, va="center", linespacing=1.6)


def box(x, y, w, h, label, color="#e6edf7", size=13):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                              edgecolor="#b0bdce", facecolor=color, linewidth=1.3))
    text(x + w / 2, y + h / 2, label, size=size)


def arrow(start, end, color="#526e97", dashed=False, arc=0):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=18,
                                linewidth=1.7, color=color,
                                linestyle="--" if dashed else "-",
                                connectionstyle=f"arc3,rad={arc}"))


text(8, 9.45, "RSSM 在线数据流：估计 → 想象 → 执行 → 重新估计", size=22, weight="bold")
text(8, 8.93, "本图只画在线接口；训练联合分布、ELBO 与参数更新另见材料", size=12, color="#5e7189")

box(.7, 6.9, 3.7, 1.2, "真实时刻 t\n历史动作 / 已取得观测 o_t", "#e0f0ee")
box(5.05, 6.9, 4.05, 1.2, "当前估计\nq(z_t | h_t, o_t) 与历史 h_t", "#e0f0ee")
arrow((4.45, 7.5), (4.99, 7.5))

box(10.3, 6.9, 4.8, 1.2, "复制当前模型状态\n候选动作 a_t … a_(t+H-1)", "#e8e7f8")
arrow((9.15, 7.5), (10.24, 7.5), dashed=True)
box(10.3, 4.55, 4.8, 1.4, "想象分支：反复调用 f 与 prior p\n(h_future, z_future) → 奖励头 → 评分", "#e8e7f8", size=12)
arrow((14.7, 6.85), (14.7, 6.02), dashed=True)
text(12.3, 6.42, "不读取真实未来观测", size=12, color="#704fa5")
box(10.3, 2.45, 4.8, 1.15, "搜索后只执行首动作 a_t*\n其余想象状态不替代真实记忆", "#e8e7f8", size=12)
arrow((14.7, 4.49), (14.7, 3.67), dashed=True)
text(12.2, 4.04, "CEM：动作搜索\nq：潜状态推断", size=11, color="#704fa5")

box(.7, 2.45, 3.7, 1.15, "真实环境执行 a_t*\n返回 o_(t+1)、r_(t+1)", "#f8ebd9", size=12)
arrow((10.24, 3.025), (4.47, 3.025), color="#aa793c")
text(7.25, 3.4, "执行的动作进入真实回路", size=12, color="#946330")
box(.7, 4.55, 8.4, 1.4, "用实际 a_t* 与保存的 (h_t, z_t) 推进 h_(t+1)\n新 o_(t+1) → q(z_(t+1) | h_(t+1), o_(t+1)) → 再规划", "#e0f0ee", size=12)
arrow((2.55, 3.66), (2.55, 4.49), color="#aa793c")
arrow((7.05, 6.84), (7.05, 6.02), color="#397e79")
arrow((4.4, 5.98), (4.98, 7.0), color="#397e79", arc=-.33)

text(8, 1.62, "虚线：候选想象 / 搜索　　实线：已发生的观测与执行 / 状态估计", size=13, color="#526582")
text(8, .94, "同一时间约定：a_t 影响 t+1；r_(t+1) 记在到达时刻。h 的递归必须保留正确的历史来源。", size=12, color="#526582")
text(8, .4, "确定性递归 h + 随机潜变量 z 是学习表示；不等同于真实物理隐态 x。", size=12, color="#526582")

fig.tight_layout(pad=1)
fig.savefig(OUT, facecolor=fig.get_facecolor(), bbox_inches="tight")
plt.close(fig)
print(OUT)
