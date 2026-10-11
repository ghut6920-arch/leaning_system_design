"""AI-authored review artifact builder, revision 1, 2026-10-11.

Only reads the newly created preparation package, selected framework resources,
and this package's teacher verification. No old same-unit preparation is read.
Pillow draws a static diagram; it is not a model or performance simulation.
All executable preparation code remains in code/. No learner state is modified.
"""
from pathlib import Path
import hashlib
import json
import math
import re
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "artifacts/preparation-tests/20261011-attention-kv-independent-v1"
FRAMEWORK = ROOT.parent.parent / "personal-learning-suite"
FONT_PATH = Path("C:/Windows/Fonts/msyh.ttc")


def draw_diagram():
    im = Image.new("RGB", (1480, 1000), "#f5f7fa")
    d = ImageDraw.Draw(im)
    fonts = {s: ImageFont.truetype(str(FONT_PATH), s) for s in (20, 23, 26, 30, 38)}
    ink, blue, green = "#192b40", "#2864b7", "#197d69"

    def text(x, y, value, size=23, color=ink):
        d.text((x, y), value, font=fonts[size], fill=color)

    def box(rect, fill="white", outline="#ced7e2"):
        d.rounded_rectangle(rect, radius=14, fill=fill, outline=outline, width=2)

    def arrow(x1, y1, x2, y2, color=blue):
        d.line((x1, y1, x2, y2), fill=color, width=4)
        angle = math.atan2(y2-y1, x2-x1)
        points = [(x2,y2), (x2-14*math.cos(angle-.5),y2-14*math.sin(angle-.5)),
                  (x2-14*math.cos(angle+.5),y2-14*math.sin(angle+.5))]
        d.polygon(points, fill=color)

    text(45, 30, "KV Cache：保留旧 K/V，重算当前 query 的读取", 38)
    text(45, 91, "因果前缀、位置、权重与可见规则保持不变时；每一层独立保存状态", 23)
    box((35, 143, 715, 561))
    box((745, 143, 1445, 561))
    text(60, 165, "逻辑可见性：当前 q4 仍读取 K1…K4", 26)
    x0, y0, cw, ch = 160, 237, 91, 56
    for col, label in enumerate(["K1", "K2", "K3", "K4", "未来"]):
        text(x0+col*cw+15, 205, label, 20)
    for row in range(4):
        text(73, y0+row*ch+13, f"q{row+1}", 23, blue if row == 3 else "#7b8794")
        for col in range(5):
            allowed = col <= row
            fill = "#347bc9" if row == 3 and allowed else ("#d7e7f7" if allowed else "#edf0f4")
            rect = (x0+col*cw,y0+row*ch,x0+(col+1)*cw-6,y0+(row+1)*ch-6)
            d.rectangle(rect, fill=fill)
            if not allowed:
                text(rect[0]+28, rect[1]+11, "×", 23, "#8e99a6")
    text(61, 488, "浅色旧行仅示意可见性，KV 中不存这些权重。", 20)
    text(61, 520, "深色当前行需重新匹配、softmax 和加权。", 20)
    text(771, 165, "一次 decode 的本层读写", 26)
    box((780, 216, 1080, 273), "#e3f1ec")
    text(800, 230, "旧 K/V 1…3：保持", 23, green)
    box((1110, 216, 1410, 273), "#e8f0fc")
    text(1130, 230, "新 k4/v4：追加", 23, blue)
    box((950, 322, 1395, 383), "#e8f0fc")
    text(972, 339, "逻辑 K/V 1…4 供当前读取", 23)
    box((780, 322, 916, 383), "#d5e6fa")
    text(818, 339, "q4", 26, blue)
    arrow(930, 273, 1080, 322, green)
    arrow(1240, 273, 1250, 322)
    box((780, 423, 1060, 483), "#edf3fa")
    text(796, 441, "Q/K 匹配 → 权重", 23)
    box((1100, 423, 1410, 483), "#edf3fa")
    text(1116, 441, "权重/V → 加权读出", 23)
    arrow(849, 383, 849, 423)
    arrow(1100, 383, 1028, 423)
    arrow(1295, 383, 1295, 423, green)
    text(1047, 396, "K", 20)
    text(1310, 396, "V", 20, green)
    arrow(1060, 453, 1100, 453)
    text(907, 508, "输出投影与本层输出 → 下一层输入", 23)
    box((35, 590, 1445, 948))
    text(61, 611, "同一服务 D：容量不等于速度或长文质量", 30)
    text(61, 658, "32 层 · 8 KV 头 · 128 维 · BF16；KV 额度 14 GiB；图中仅画 payload", 23)
    rows = [("原规格：4 × 20480 token", 10, blue),
            ("扩长：4 × 36864 token", 18, "#bd504f"),
            ("扩长：理想 INT8", 9, green)]
    left, scale, limit = 505, 38, 14
    for i, (label, value, color) in enumerate(rows):
        y = 721+i*65
        text(61, y+5, label, 23)
        d.rounded_rectangle((left,y,left+value*scale,y+40),radius=5,fill=color)
        text(left+value*scale+13, y+3, f"{value} GiB", 23, color)
    lx = left+limit*scale
    for yy in range(711, 895, 15):
        d.line((lx,yy,lx,yy+7),fill="#394b5f",width=2)
    text(lx-18, 896, "14 GiB 额度", 20)
    text(61, 908, "INT8 另加元数据与残留；所有配置仍需核分配开销、实现、性能和任务质量。", 20)
    text(45, 966, "AI 教师准备图 v1 · 假设规格与公式对应 · 无真实模型基准或学习者表现", 20, "#66778c")
    target = PACKAGE / "cache-state-and-cost.png"
    im.save(target)
    return target


def assemble_complete():
    parts = ["01-materials-and-demonstration.md", "02-workbook.md",
             "03-teacher-reference.md", "04-dynamic-support.md",
             "05-basis-and-methods.md", "06-review.md", "07-verification.md"]
    intro = """# Transformer Attention：KV Cache 与长上下文推理——备课成品 v1

2026-10-11 · prepared_for_review · 仅供用户审查，未开展正式教学。

本次根据当前学习系统入口、原始学科资料和完整所选策略独立制作；未读取同单元既有备课／测试记录，未修改真实学习进度。教师示范、服务规格和新证据票据均已注明来源或教学假设。

连续作品是《长文档问答服务推理方案》。四层主线贯穿同一工作：识别可改变选择 → 说明条件和后果 → 审计联动及失效 → 在未知约束下构造、验证、调整方案。

Encoding从实际读取、状态与因果关系推进到分账和选择；Post在同作品中整合关系、选用方法、据证据修订。未预期解释先定位对象、区别竞争解释，再改解释／表示／对照并返回原工作。以下包含完整教师材料、连续工作纸、参考与支持，现在不要求用户作答。

审查顺序可沿全文阅读；分文件入口与教师代码见[目录](README.md)。部分教师参考在实际教学时待原答保留后再呈现，本次审查全部开放。

"""
    sections = []
    for name in parts:
        body = (PACKAGE / name).read_text(encoding="utf-8")
        sections.append(re.sub(r"^(#{1,5}) ", r"#\1 ", body, flags=re.M))
    target = PACKAGE / "备课成品.md"
    target.write_text(intro+"\n\n---\n\n".join(sections), encoding="utf-8")
    return target


def validate():
    report = json.loads((ROOT / "code/attention-kv-preptest-20261011/verification.json").read_text(encoding="utf-8"))
    demo = ROOT / "code/attention-kv-preptest-20261011/kv_cache_demo.py"
    assert hashlib.sha256(demo.read_bytes()).hexdigest() == report["code"]["sha256"]
    assert all(item["passed"] for item in report["checks"].values())
    # Fresh arithmetic for the preparation problems; not a re-run of the toy.
    kv = lambda L,H,d,s,B,T: 2*L*H*d*s*B*T/(2**30)
    assert kv(32,8,128,2,4,20480) == 10
    assert kv(32,8,128,2,4,36864) == 18
    assert kv(24,6,128,2,3,32768) == 6.75
    assert kv(24,6,128,2,3,24576) == 5.0625
    assert kv(24,6,128,1,3,32768)+.6 == 3.975
    assert kv(32,8,128,2,4,40960)+.5 == 20.5
    assert kv(32,8,128,2,3,40960)+.5 == 15.5
    assert kv(32,8,128,2,2,40960)+.5 == 10.5
    assert (16384+8*4096)/(8*(16384+4096)) == .3
    keys = ["encoding/S05", "encoding/R06", "encoding/D04", "encoding/R10",
            "post/retrieve-relation", "post/select-method", "post/conditional-update"]
    resources = {key: hashlib.sha256((FRAMEWORK / "resources/strategies" / (key+".json")).read_bytes()).hexdigest()
                 for key in keys}
    state_expected = {"control.md": "d7ba0aa3bf5c84b0a6888bbcccb48da66ddb7c3dbdc623daf31ff99b44692d87",
                      "current.md": "0cdb6c945d41f929f66c9d1752403bb47b516e10ddd6fb763e160f84e3719977"}
    state_actual = {name: hashlib.sha256((ROOT / "state" / name).read_bytes()).hexdigest()
                    for name in state_expected}
    assert state_expected == state_actual
    result = {"artifact_kind": "teacher_preparation_package_verification",
              "date": "2026-10-11", "teacher_report_hash_matches": True,
              "finite_checks": len(report["checks"]), "problem_arithmetic_checked": True,
              "state_hashes_unchanged": state_actual, "resource_file_sha256": resources,
              "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "new preparation artifacts and selected rules only; no real model benchmark or learner performance"}
    output = PACKAGE / "build-verification.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    link_count = 0
    for part in PACKAGE.glob("*.md"):
        for dest in re.findall(r"\]\(([^)]+)\)", part.read_text(encoding="utf-8")):
            if not dest.startswith(("https:", "http:", "#")):
                assert (part.parent / dest).exists(), (part.name, dest)
                link_count += 1
    result["local_links_checked"] = link_count
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    assert json.loads(output.read_text(encoding="utf-8")) == result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    draw_diagram()
    assemble_complete()
    validate()
