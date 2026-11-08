"""文件型审批门禁与 checkpoint（标准库）。"""
from __future__ import annotations
import json, os, tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _atomic(path: str, obj: Any) -> None:
    parent = os.path.dirname(os.path.abspath(path)); os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.approval-', dir=parent, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def risk(action: str = '', *, data: Optional[Dict[str, Any]] = None) -> str:
    """Return low/medium/high using conservative, inspectable keyword rules."""
    text = (action + ' ' + json.dumps(data or {}, ensure_ascii=False)).lower()
    if any(k in text for k in ('delete', 'drop', 'publish', 'payment', 'external', 'send', 'refund', 'charge', 'transfer', '扣款', '退款', '付款', '转账', '发送', '发布', '签约', '采购')): return 'high'
    if any(k in text for k in ('write', 'modify', 'credential', 'deploy', '写入', '修改', '部署', '密钥')): return 'medium'
    return 'low'


def needs_approval(action: str = '', *, level: Optional[str] = None,
                   data: Optional[Dict[str, Any]] = None) -> bool:
    detected = risk(action, data=data)
    requested = level or detected
    order = {'low': 0, 'medium': 1, 'high': 2}
    if requested not in order:
        raise ValueError(f'Unknown risk level: {requested}')
    # Caller-provided labels may escalate risk, never suppress it.
    return order[requested] >= order[detected] and requested in ('medium', 'high') or detected in ('medium', 'high')


class _FileLock:
    def __init__(self, path: str, timeout: float = 5.0):
        self.path, self.timeout = path, timeout

    def __enter__(self):
        import time
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode('ascii'))
                os.close(fd)
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'Approval store lock timed out: {self.path}')
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass


class ApprovalStore:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.path = os.path.join(self.root, 'approvals.json')
        self.lock_path = os.path.join(self.root, '.approvals.lock')
        os.makedirs(self.root, exist_ok=True)
    def _all(self):
        if not os.path.exists(self.path): return {}
        with open(self.path, encoding='utf-8') as f: return json.load(f)
    def _save(self, x): _atomic(self.path, x)
    def create(self, action: str, *, details: Optional[Dict[str, Any]] = None, level: Optional[str] = None, checkpoint: str = '') -> Dict[str, Any]:
        import uuid
        aid = uuid.uuid4().hex[:12]; now = datetime.now(timezone.utc).isoformat()
        detected = risk(action, data=details)
        severity = level or detected
        if needs_approval(action, level=severity, data=details):
            status = 'pending'
        else:
            status = 'not_required'
        card = {'id': aid, 'action': action, 'details': details or {}, 'risk': severity, 'status': status, 'checkpoint': checkpoint, 'created_at': now, 'updated_at': now}
        with _FileLock(self.lock_path):
            all_ = self._all(); all_[aid] = card; self._save(all_)
        return card
    def get(self, approval_id: str): return self._all().get(approval_id)
    def decide(self, approval_id: str, decision: str, *, actor: str = '') -> Dict[str, Any]:
        if decision not in ('approve', 'reject'): raise ValueError(decision)
        with _FileLock(self.lock_path):
            all_ = self._all(); card = all_.get(approval_id)
            if not card: raise KeyError(approval_id)
            if card['status'] != 'pending': raise RuntimeError(f"approval is not pending: {card['status']}")
            card.update(status='approved' if decision == 'approve' else 'rejected', decision=decision, actor=actor, updated_at=datetime.now(timezone.utc).isoformat()); self._save(all_)
            return card
    def approve(self, approval_id: str, **kw): return self.decide(approval_id, 'approve', **kw)
    def reject(self, approval_id: str, **kw): return self.decide(approval_id, 'reject', **kw)
    def resume(self, approval_id: str) -> str:
        card = self.get(approval_id)
        if not card: raise KeyError(approval_id)
        if card['status'] != 'approved': raise RuntimeError('approval is not approved')
        return card.get('checkpoint', '')

def approval_card(root: str, action: str, **kwargs): return ApprovalStore(root).create(action, **kwargs)
