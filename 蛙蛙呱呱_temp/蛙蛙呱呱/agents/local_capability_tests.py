import csv, json
from pathlib import Path
import tempfile
import importlib.util

ROOT = Path(__file__).resolve().parent


def load(role, folder):
    spec = importlib.util.spec_from_file_location(role + "_local_exec", ROOT / folder / "local_exec.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run():
    with tempfile.TemporaryDirectory() as temp:
        d = Path(temp)
        ledger = d / "ledger.json"
        ledger.write_text(json.dumps({"entries": [{"sku": "A", "qty": 3}, {"sku": "A", "qty": -1}]}), encoding="utf-8")
        backup = d / "backup"
        backup.mkdir()
        (backup / "sample.txt").write_text("fixture", encoding="utf-8")
        cases = [
            ("r14", load("r14", "r14-wajiaoyi-commerce"), {"items": [{"unit_price": "2.50", "quantity": 2}], "total": "5.00", "events": [{"idempotency_key": "once"}]}, {"items": [{"unit_price": "2.50", "quantity": 2}], "total": "4.00"}, False),
            ("r15", load("r15", "r15-wagongying-erp"), str(ledger), str(d / "missing.csv"), False),
            ("r16", load("r16", "r16-warenshi-hr"), {"email": "a@b.com", "payroll": {"gross": 100, "source": "input"}}, {"payroll": {"gross": -1}}, False),
            ("r17", load("r17", "r17-wazhiwang-automation"), {"nodes": [{"name": "start"}], "fields": {"a": "b"}, "max_retries": 2}, {"execute_external": True}, True),
            ("r18", load("r18", "r18-washucang-dataeng"), [{"a": " x ", "b": 1}, {"a": "y", "b": 2}], [], False),
            ("r19", load("r19", "r19-wazhimo-ml"), [{"expected": "yes", "predicted": "yes"}, {"expected": "no", "predicted": "yes"}], [], False),
            ("r20", load("r20", "r20-washouzhi-sre"), str(backup), str(d / "absent"), False),
        ]
        for role, module, good, bad, simulated in cases:
            real = module.execute(good) if role != "r15" else module.execute(str(good))
            blocked = module.execute(bad) if role != "r15" else module.execute(str(bad))
            want = "simulated" if simulated else "real"
            assert real.get("ok") and real.get("capability_status") == want, (role, real)
            assert not blocked.get("ok") and blocked.get("capability_status") == "blocked", (role, blocked)
            print(f"{role}: local={want}; blocked=blocked")

if __name__ == "__main__":
    run()
