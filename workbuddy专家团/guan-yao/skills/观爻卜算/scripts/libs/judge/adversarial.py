# -*- coding: utf-8 -*-
"""对抗判别器（GAN 式独立复核）

借鉴 mingli-skills「独立评估者」：不是 self-eval，而是用**独立规则链**从原始数据重推核心判断，
专门找主判的矛盾（判别器尝试反驳主判）。与「回归自检」（排盘正确性 parity）互补——
回归只查「盘排得对不对」，本模块查「断语下得自不自洽、有无与独立口径分歧」。

用法:
  python libs/adversarial.py 2001 9 22 4 0 0 1     # 八字·对抗复核
  import adversarial; adversarial.bazi(2001, 9, 22, 4, 0, 0, 1)
"""
import sys
import io
import contextlib


def bazi(y, mo, d, hh=12, mi=0, ss=0, gender=1):
    """八字对抗复核：独立「旺相休囚死+得地得生得势」重推 vs 主路径「四指标加权」。

    返回 {矛盾[], verdict, 主判{}, 独立判{}}。有矛盾 → verdict 存疑，断卦须降级并标「信号冲突，仅供参考」。
    """
    from pan import bazi_liunian
    from judge import bazi_evaluator
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main = bazi_liunian.mingli_analysis(y, mo, d, hh, mi, ss, gender)
    indep = bazi_evaluator.derive_from_solar(y, mo, d, hh, mi, ss, gender)

    ws_m, ws_i = main["旺衰"]["档次"], indep["旺衰"]
    gj_m = main["格局"]["格局"]
    gj_i = indep["格局"].replace("格", "")
    xi_m, xi_i = set(main["喜"]), set(indep["喜"])

    findings = []
    # 旺衰：方向必须一致（弱 vs 强 = 硬矛盾；弱 vs 中和偏弱 = 边界差异）
    same_dir = ("弱" in ws_m and "弱" in ws_i) or ("强" in ws_m and "强" in ws_i)
    if not same_dir:
        findings.append(f"旺衰分歧：主判「{ws_m}」vs 独立判「{ws_i}」（旺相休囚死口径）")
    # 格局
    if gj_m != gj_i:
        findings.append(f"格局分歧：主判「{gj_m}」vs 独立判「{gj_i}」")
    # 喜忌（喜印比 vs 喜财官食伤 自洽性，独立口径独立判定）
    if xi_m != xi_i:
        findings.append(f"喜忌分歧：主判喜{''.join(sorted(xi_m))} vs 独立喜{''.join(sorted(xi_i))}")

    verdict = "存疑（判别器反驳成功，须降级/复核）" if findings else "通过（主判与独立重推一致）"
    return {"矛盾": findings, "verdict": verdict,
            "主判": {"旺衰": ws_m, "格局": gj_m, "喜": sorted(xi_m)},
            "独立判": {"旺衰": ws_i, "格局": gj_i, "喜": sorted(xi_i)}}


def format_review(r):
    lines = [f"【对抗判别器·八字】{r['verdict']}"]
    lines.append(f"  主判：旺衰「{r['主判']['旺衰']}」 格局「{r['主判']['格局']}」 喜{'、'.join(r['主判']['喜'])}")
    lines.append(f"  独立：旺衰「{r['独立判']['旺衰']}」 格局「{r['独立判']['格局']}」 喜{'、'.join(r['独立判']['喜'])}")
    if r["矛盾"]:
        for f in r["矛盾"]:
            lines.append(f"  ⚠ {f}")
    else:
        lines.append("  · 无矛盾，主判稳健")
    return "\n".join(lines)


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    a = [int(x) for x in sys.argv[1:] if not x.startswith("-")]
    if len(a) >= 7:
        print(format_review(bazi(*a[:7])))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()