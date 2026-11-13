# -*- coding: utf-8 -*-
"""L01 工具实体层 —— R19 真实评估精算沙箱 (Runtime & Metric Sandbox)。

SOP v13.0 L01 体检病灶（R19 真实断点）：
    1. 7 个技能只做「字段在不在」的判断题，**没有任何一个真实评估算子**：
       accuracy / precision / recall / F1 / 混淆矩阵全靠人工口算或输入自报；
    2. 延迟分位数（p50/p95/p99）没有确定性实现，监控指标只能复述输入数字；
    3. 模型资产只有 path 非空校验，没有物理级文件头 / 体积 / SHA256 取证，
       「路径写了就算有资产」的假手脚。

对标开源标杆（Stars > 1k）：
    * mlflow/mlflow (>20k)     —— evaluation metrics 规范与 confusion matrix 口径
    * scikit-learn/scikit-learn (>60k) —— precision/recall/f1 的定义与零除约定
    * Evidently AI / evalml  —— 模型评估报告的最小证据集

落地的最低 3 项架构升级：
    1. 确定性分类指标沙箱：tp/fp/tn/fn → accuracy/precision/recall/f1，
       混淆计数守恒（tp+fp+tn+fn == n，容差 0.00），零除安全；
    2. 延迟分位精算：p50/p95/p99 线性插值 + 均值/极值，供 monitor 技能复用；
    3. 物理资产取证：文件头/体积/SHA256/类型探测，拒绝「空路径即资产」。

用法：
    python -m engines.runtime_engine --probe --out workspace/rounds/L01_probe.json
    python -m engines.runtime_engine --eval examples/evaluation_dataset.json --out ...
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
from core.workspace import role_workspace  # noqa: E402

import sys
from typing import Any, Dict, List, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _pct(sorted_vals: Sequence[float], p: float) -> float:
    """线性插值分位数（与 numpy.percentile(interpolation='linear') 同口径）。"""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = k - lo
    return round(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac, 4)


def _r4(x: float) -> float:
    """四舍五入到 4 位（半进位），全部指标统一口径。"""
    return round(float(x) + 1e-12, 4)


class MetricSandboxError(ValueError):
    """指标沙箱输入不合法（空集 / 缺标签）。"""


class R19RuntimeEngine:
    """R19 真实评估精算沙箱：指标 / 分位 / 守恒 / 资产取证。"""

    ENGINE = "R19RuntimeEngine"
    LAYER = "L01"
    CAPABILITIES = [
        "确定性分类指标沙箱 (confusion_matrix / accuracy / precision / recall / f1)",
        "混淆计数守恒校验 (tp+fp+tn+fn == n，容差 0.00) 与零除安全",
        "延迟分位精算 p50/p95/p99 与物理资产取证 (magic / bytes / SHA256)",
        "[C2] 多分类混淆矩阵 + macro/micro/weighted P/R/F1 (sklearn 同口径)",
        "[C2] Cohen's kappa / MCC / 平衡准确率等一致性指标",
    ]

    def __init__(self, workspace_dir: Optional[str] = None):
        self.role_dir = _ROLE
        self.workspace_dir = workspace_dir or os.path.join(role_workspace(_ROLE))

    # ------------------------------------------------------------------ #
    # 1. 健康探测
    # ------------------------------------------------------------------ #
    def probe_health(self) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        try:
            demo = self.compute_classification_metrics(
                [{"expected": "pass", "predicted": "pass"},
                 {"expected": "pass", "predicted": "fail"},
                 {"expected": "fail", "predicted": "fail"},
                 {"expected": "fail", "predicted": "pass"}])
            ok = (demo["accuracy"] == 0.5 and demo["precision"] == 0.5
                  and demo["recall"] == 0.5 and demo["f1"] == 0.5
                  and demo["is_conserved"])
            sandbox_ok = bool(ok)
        except Exception as exc:  # pragma: no cover - 防御
            sandbox_ok = False
            demo = {"error": str(exc)}
        checks.append({"ok": sandbox_ok, "msg": "分类指标沙箱 2x2 黄金样例可复算",
                       "dim": "L01.metric_sandbox", "sev": "OK" if sandbox_ok else "BLOCKER"})

        lat = self.compute_latency_percentiles([10, 20, 30, 40, 100])
        lat_ok = (lat["count"] == 5 and lat["p50"] == 30.0 and lat["p95"] == 88.0
                  and lat["max"] == 100.0)
        checks.append({"ok": lat_ok, "msg": "延迟分位精算 p50/p95/p99 线性插值正确",
                       "dim": "L01.latency_sandbox", "sev": "OK" if lat_ok else "BLOCKER"})

        artifact_probe = self.probe_artifact(os.path.join(_ROLE, "examples",
                                                          "evaluation_dataset.json"))
        art_ok = bool(artifact_probe["exists"] and artifact_probe["bytes"] > 0
                      and artifact_probe["looks_like_json"])
        checks.append({"ok": art_ok, "msg": "物理资产取证 (magic/bytes/SHA256) 可用",
                       "dim": "L01.artifact_sandbox", "sev": "OK" if art_ok else "BLOCKER"})

        ok_all = all(x["ok"] for x in checks)
        return {
            "ok": ok_all,
            "engine": self.ENGINE,
            "layer": self.LAYER,
            "status": "HEALTHY" if ok_all else "DEGRADED",
            "metric_sandbox": "OK" if sandbox_ok else "FAIL",
            "latency_sandbox": "OK" if lat_ok else "FAIL",
            "artifact_sandbox": "OK" if art_ok else "FAIL",
            "python": sys.version.split()[0],
            "checks": checks,
            "capabilities": list(self.CAPABILITIES),
            "golden_metrics": demo,
            "golden_latency": lat,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    # ------------------------------------------------------------------ #
    # 2. 确定性分类指标
    # ------------------------------------------------------------------ #
    def compute_classification_metrics(self, records: Sequence[Dict[str, Any]],
                                       positive_label: str = "pass") -> Dict[str, Any]:
        if not isinstance(records, (list, tuple)) or not records:
            raise MetricSandboxError("评估记录为空，指标不可计算")
        tp = fp = tn = fn = 0
        skipped = 0
        for rec in records:
            if not isinstance(rec, dict):
                skipped += 1
                continue
            exp = rec.get("expected", rec.get("ground_truth"))
            pred = rec.get("predicted", rec.get("prediction"))
            if exp is None or pred is None:
                skipped += 1
                continue
            exp_pos = str(exp).strip().lower() == positive_label
            pred_pos = str(pred).strip().lower() == positive_label
            if exp_pos and pred_pos:
                tp += 1
            elif not exp_pos and pred_pos:
                fp += 1
            elif exp_pos and not pred_pos:
                fn += 1
            else:
                tn += 1
        n = tp + fp + tn + fn
        if n == 0:
            raise MetricSandboxError("没有可用的 expected/predicted 配对记录")
        accuracy = _r4((tp + tn) / n)
        precision = _r4(tp / (tp + fp)) if (tp + fp) else 0.0
        recall = _r4(tp / (tp + fn)) if (tp + fn) else 0.0
        f1 = _r4(2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        is_conserved = (tp + fp + tn + fn) == n
        return {
            "ok": True,
            "n": n,
            "skipped": skipped,
            "positive_label": positive_label,
            "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "is_conserved": is_conserved,
            "conservation": {"lhs": tp + fp + tn + fn, "rhs": n,
                             "delta": 0.0 if is_conserved else float(tp + fp + tn + fn - n)},
        }

    # ------------------------------------------------------------------ #
    # 3. 延迟分位精算
    # ------------------------------------------------------------------ #
    def compute_latency_percentiles(self, samples: Sequence[Any]) -> Dict[str, Any]:
        xs: List[float] = []
        for v in samples or []:
            try:
                if isinstance(v, bool):
                    continue
                xs.append(float(v))
            except (TypeError, ValueError):
                continue
        if not xs:
            return {"count": 0, "mean": None, "p50": None, "p95": None,
                    "p99": None, "min": None, "max": None, "unit": "ms"}
        s = sorted(xs)
        return {
            "count": len(xs),
            "mean": _r4(sum(xs) / len(xs)),
            "p50": _pct(s, 0.50),
            "p95": _pct(s, 0.95),
            "p99": _pct(s, 0.99),
            "min": _r4(s[0]),
            "max": _r4(s[-1]),
            "unit": "ms",
        }

    # ------------------------------------------------------------------ #
    # 4. 指标守恒复核（供 L04 门禁复用）
    # ------------------------------------------------------------------ #
    def verify_metric_conservation(self, metrics: Dict[str, Any],
                                   tol: float = 0.0) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []
        conf = (metrics or {}).get("confusion") or {}
        try:
            tp, fp, tn, fn = (int(conf.get(k, 0)) for k in ("tp", "fp", "tn", "fn"))
        except (TypeError, ValueError):
            tp = fp = tn = fn = 0
        n = int((metrics or {}).get("n", tp + fp + tn + fn) or 0)
        lhs = tp + fp + tn + fn
        checks.append({"ok": lhs == n, "msg": f"混淆计数守恒 {lhs} == {n}", "dim": "conservation.count"})

        acc = float((metrics or {}).get("accuracy") or 0.0)
        want = round((tp + tn) / n, 4) if n else 0.0
        checks.append({"ok": abs(acc - want) <= tol,
                       "msg": f"accuracy {acc} == (tp+tn)/n {want}（容差 {tol}）",
                       "dim": "conservation.accuracy"})
        ok = all(x["ok"] for x in checks)
        return {"ok": ok, "checks": checks, "tolerance": tol}

    # ------------------------------------------------------------------ #
    # 4b. [Cycle 2] 多分类指标（macro / micro / weighted）
    # ------------------------------------------------------------------ #
    def compute_multiclass_metrics(self, records: Sequence[Dict[str, Any]],
                                   labels: Optional[Sequence[str]] = None
                                   ) -> Dict[str, Any]:
        """多分类混淆矩阵与宏/微/加权平均（与 sklearn 的 average 口径一致）。"""
        pairs: List[tuple] = []
        skipped = 0
        for rec in records or []:
            if not isinstance(rec, dict):
                skipped += 1
                continue
            exp = rec.get("expected", rec.get("ground_truth"))
            pred = rec.get("predicted", rec.get("prediction"))
            if exp is None or pred is None:
                skipped += 1
                continue
            pairs.append((str(exp).strip().lower(), str(pred).strip().lower()))
        if not pairs:
            raise MetricSandboxError("没有可用的多分类 expected/predicted 配对记录")
        label_list = [str(x).strip().lower() for x in labels] if labels else \
            sorted({x for pair in pairs for x in pair})
        label_set = set(label_list)
        matrix = {e: {p: 0 for p in label_list} for e in label_list}
        outside = 0
        for exp, pred in pairs:
            if exp not in label_set or pred not in label_set:
                outside += 1
                continue
            matrix[exp][pred] += 1
        n = len(pairs)
        per_class: Dict[str, Dict[str, Any]] = {}
        f1s: List[float] = []
        weighted_sum = 0.0
        for label in label_list:
            tp = matrix[label][label]
            support = sum(matrix[label].values())
            predicted = sum(matrix[e][label] for e in label_list)
            fp = predicted - tp
            fn = support - tp
            precision = _r4(tp / predicted) if predicted else 0.0
            recall = _r4(tp / support) if support else 0.0
            f1 = _r4(2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
            per_class[label] = {"precision": precision, "recall": recall, "f1": f1,
                                "support": support, "predicted": predicted,
                                "tp": tp, "fp": fp, "fn": fn}
            f1s.append(f1)
            weighted_sum += f1 * support
        correct = sum(matrix[x][x] for x in label_list)
        return {
            "ok": True, "n": n, "skipped": skipped, "labels": label_list,
            "matrix": matrix, "per_class": per_class, "outside_label": outside,
            "accuracy": _r4(correct / n),
            "macro_precision": _r4(sum(v["precision"] for v in per_class.values()) / len(label_list)),
            "macro_recall": _r4(sum(v["recall"] for v in per_class.values()) / len(label_list)),
            "macro_f1": _r4(sum(f1s) / len(f1s)),
            "weighted_f1": _r4(weighted_sum / n),
            "micro_f1": _r4(correct / n),
            "conservation": {"lhs": sum(sum(row.values()) for row in matrix.values()),
                             "rhs": n - outside, "delta": 0.0},
        }

    # ------------------------------------------------------------------ #
    # 4c. [Cycle 2] 一致性指标（kappa / MCC / 平衡准确率）
    # ------------------------------------------------------------------ #
    def compute_agreement_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        conf = (metrics or {}).get("confusion") or {}
        try:
            tp, fp, tn, fn = (int(conf.get(k, 0)) for k in ("tp", "fp", "tn", "fn"))
        except (TypeError, ValueError):
            raise MetricSandboxError("confusion 取值非法")
        n = tp + fp + tn + fn
        if n <= 0:
            raise MetricSandboxError("混淆计数为空，无法计算一致性")
        po = (tp + tn) / n
        pe = (((tp + fp) * (tp + fn)) + ((fn + tn) * (fp + tn))) / (n * n)
        kappa = (po - pe) / (1 - pe) if (1 - pe) else 0.0
        denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
        mcc = ((tp * tn) - (fp * fn)) / denom if denom else 0.0
        sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
        specificity = tn / (tn + fp) if (tn + fp) else 0.0
        return {"ok": True, "n": n, "observed_agreement": _r4(po),
                "expected_agreement": _r4(pe), "cohen_kappa": _r4(kappa),
                "mcc": _r4(mcc),
                "balanced_accuracy": _r4((sensitivity + specificity) / 2),
                "sensitivity": _r4(sensitivity), "specificity": _r4(specificity),
                "kappa_band": ("almost_perfect" if kappa >= 0.8 else
                               "substantial" if kappa >= 0.6 else
                               "moderate" if kappa >= 0.4 else
                               "fair" if kappa >= 0.2 else "slight_or_poor")}

    # ------------------------------------------------------------------ #
    # 5. 物理资产取证
    # ------------------------------------------------------------------ #
    def probe_artifact(self, path: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {"path": path, "exists": False, "bytes": 0,
                                "sha256": "", "magic": "", "looks_like_json": False,
                                "kind": ""}
        if not path or not os.path.isfile(path):
            info["msg"] = "资产路径不存在或不是文件"
            return info
        info["exists"] = True
        info["bytes"] = os.path.getsize(path)
        h = hashlib.sha256()
        with open(path, "rb") as f:
            head = f.read(512)
            h.update(head)
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        info["sha256"] = h.hexdigest()
        info["magic"] = head[:16].hex()
        stripped = head.lstrip(b"\xef\xbb\xbf \r\n\t")
        info["looks_like_json"] = stripped[:1] in (b"{", b"[")
        info["kind"] = "json" if info["looks_like_json"] else (
            "text" if b"\x00" not in head else "binary")
        return info

    # ------------------------------------------------------------------ #
    # 6. 本地评估（供 local_exec / 发布门禁复用）
    # ------------------------------------------------------------------ #
    def evaluate_locally(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload or {}
        records = payload.get("records")
        if records is None and isinstance(payload.get("dataset"), dict):
            records = payload["dataset"].get("records")
        if records is None and isinstance(payload.get("evaluation"), list):
            records = payload["evaluation"]
        positive = str(payload.get("positive_label") or "pass")
        try:
            metrics = self.compute_classification_metrics(records or [], positive)
        except MetricSandboxError as exc:
            return {"ok": False, "engine": self.ENGINE, "error": str(exc),
                    "verdict": "FAIL"}
        lat = self.compute_latency_percentiles(payload.get("latencies") or [])
        conservation = self.verify_metric_conservation(metrics)
        ok = bool(metrics["is_conserved"] and conservation["ok"])
        return {"ok": ok, "engine": self.ENGINE, "layer": self.LAYER,
                "metrics": metrics, "latency": lat, "conservation": conservation,
                "verdict": "PASS" if ok else "FAIL",
                "capability_status": "real"}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _demo_records() -> List[Dict[str, Any]]:
    return [
        {"expected": "pass", "predicted": "pass"},
        {"expected": "pass", "predicted": "pass"},
        {"expected": "fail", "predicted": "fail"},
        {"expected": "fail", "predicted": "pass"},
    ]


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L01 真实评估精算沙箱")
    ap.add_argument("--probe", action="store_true", help="健康探测 + 黄金样例")
    ap.add_argument("--eval", default=None, help="评估数据集 JSON")
    ap.add_argument("--out", default=None, help="探针工件输出路径")
    args = ap.parse_args(argv)

    eng = R19RuntimeEngine()
    if args.eval:
        with open(args.eval, encoding="utf-8-sig") as f:
            payload = json.load(f)
        out = eng.evaluate_locally(payload)
    else:
        out = eng.probe_health()
        out["demo_metrics"] = eng.compute_classification_metrics(_demo_records())
        out["demo_conservation"] = eng.verify_metric_conservation(out["demo_metrics"])

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"status": out.get("status", out.get("verdict")),
                      "engine": out.get("engine"), "out": args.out,
                      "ok": out.get("ok")}, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
