"""Additional audit of lesson 2026-10-06-02's mathematical interface claims.

Unique coordinate labels are constructed for checking; these are not camera
samples, learner code, teacher pre-class execution or a PyTorch runtime test.
"""
from pathlib import Path
import json


def main():
    batch, time, height, width, channel = 2, 4, 2, 2, 3
    raw = {(b, t, h, w, c): (b, t, c, h, w)
           for b in range(batch) for t in range(time) for h in range(height)
           for w in range(width) for c in range(channel)}
    video = {(b, c, t, h, w): label for (b, t, h, w, c), label in raw.items()}
    frames = {(b * time + t, c, h, w): label for (b, t, h, w, c), label in raw.items()}
    merge_first = {(b * time + t, h, w, c): label for (b, t, h, w, c), label in raw.items()}
    alternate = {(k, c, h, w): label for (k, h, w, c), label in merge_first.items()}
    checks = []
    def check(name, value):
        if not value:
            raise AssertionError(name)
        checks.append({"case": name, "pass": True})
    check("input_elements_96", len(raw) == 96)
    check("video_output_shape", len(video) == batch * channel * time * height * width)
    check("frame_output_shape", len(frames) == batch * time * channel * height * width)
    check("alternate_valid_route", alternate == frames)
    coordinate_checks = 0
    for (b, t, h, w, c), label in raw.items():
        assert video[b, c, t, h, w] == label
        assert frames[b * time + t, c, h, w] == label
        k = b * time + t
        assert (k // time, k % time) == (b, t)
        coordinate_checks += 3
    check("all_coordinate_identities_and_inverse", coordinate_checks == 288)
    flattened = [11, 12, 13, 21, 22, 23]
    reshape = [flattened[i:i+2] for i in range(0, 6, 2)]
    transpose = [[11, 21], [12, 22], [13, 23]]
    check("given_green_values", transpose[1] == [12, 22])
    check("given_bad_result_is_compatible_with_direct_reshape", reshape[1] == [13, 21])
    check("equal_elements_and_dimensions_do_not_prove_identity", len(flattened) == 6 and reshape != transpose)
    check("swapping_second_third_axes_of_BTHWC_is_not_BCTHW", [batch, height, time, width, channel] != [batch, channel, time, height, width])
    check("merging_BT_only_does_not_move_channel", [batch*time, height, width, channel] != [batch*time, channel, height, width])
    check("image_6_recovers_video_1_frame_2", divmod(6, time) == (1, 2))
    check("N_alone_does_not_determine_original_BT", 2*4 == 4*2 == 8 and divmod(3, 4) != divmod(3, 2))
    result = {"lesson": "2026-10-06-02", "status": "pass", "cases": checks,
              "checks_passed": len(checks), "coordinate_checks": coordinate_checks,
              "pytorch_executed": False, "learner_performance_generated": False,
              "limits": ["Additional audit constructed from the lesson's stated specifications",
                         "Finite coordinate checking does not prove general software correctness or learning effects",
                         "Given green samples alone cannot prove whole-data correctness or uniquely identify an operation"]}
    out = Path(__file__).resolve().parents[2] / "reviews/2026-10-06-02-content-checks.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:result[k] for k in ["status", "checks_passed", "coordinate_checks", "pytorch_executed"]}))


if __name__ == "__main__":
    main()
