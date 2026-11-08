import argparse
import ast
import asyncio
import importlib.util
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

for _parent in Path(__file__).resolve().parents:
    _runtime_scripts = _parent / "skills" / "agent-runtime" / "scripts"
    if _runtime_scripts.exists():
        sys.path.insert(0, str(_runtime_scripts))
        break

try:
    from run_ledger import append_event as _ledger_append_event
    from run_ledger import sync_project as _ledger_sync_project
except Exception:
    _ledger_append_event = None
    _ledger_sync_project = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

VALID_PROVIDER_KEYS = {"openai", "anthropic", "deepseek", "auto", "codex"}
_CODEX_CONFIG_CACHE: dict[str, Any] | None = None

DISABLED_OUTPUT_DIR_NAMES = {
    "_disabled",
    "_disabled-outputs",
    "_archive",
    "_archive-bad-runs",
    "_validation",
    "_rerun-backups",
}

DISABLED_TOPIC_PREFIXES = {
    "echobird-codex-deepseek-tutorial",
    "echobird-codex-deepseek-playbook",
    "strategy-playbook-smoke",
    "tutorial-strategy-smoke",
    "tutorial-strategy-v2-smoke",
    "validation-teaching-playbook",
}

MAX_PARALLEL_SECTIONS = 3
SECTION_SOFT_TOKEN_CAP = 24000
SECTION_HARD_TOKEN_CAP = 40000
AGENT_ID = "content.article_director.v1"


def _safe_json_loads(text: str, default: Any) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _normalize_provider_key(value: str) -> str:
    key = (value or "").strip().lower()
    return key if key in VALID_PROVIDER_KEYS else ""


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _available_provider_keys() -> list[str]:
    keys: list[str] = []
    if os.getenv("OPENAI_API_KEY"):
        keys.append("openai")
    if os.getenv("ANTHROPIC_API_KEY"):
        keys.append("anthropic")
    if os.getenv("DEEPSEEK_API_KEY"):
        keys.append("deepseek")
    return keys


def _load_codex_config() -> dict[str, Any]:
    global _CODEX_CONFIG_CACHE
    if _CODEX_CONFIG_CACHE is not None:
        return _CODEX_CONFIG_CACHE
    path = Path.home() / ".codex" / "config.toml"
    if not path.exists():
        _CODEX_CONFIG_CACHE = {}
        return _CODEX_CONFIG_CACHE
    try:
        _CODEX_CONFIG_CACHE = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _CODEX_CONFIG_CACHE = {}
    return _CODEX_CONFIG_CACHE


def _codex_openai_provider_config() -> dict[str, Any]:
    config = _load_codex_config()
    providers = config.get("model_providers", {})
    provider_name = str(config.get("model_provider", "") or "").strip()
    if provider_name and isinstance(providers, dict):
        selected = providers.get(provider_name, {})
        if isinstance(selected, dict) and str(selected.get("env_key", "")).strip() == "OPENAI_API_KEY":
            return {
                "provider_name": provider_name,
                "base_url": str(selected.get("base_url", "") or "").strip(),
                "model": str(config.get("model", "") or "").strip(),
            }
    if isinstance(providers, dict):
        for name, item in providers.items():
            if not isinstance(item, dict):
                continue
            if str(item.get("env_key", "")).strip() == "OPENAI_API_KEY":
                return {
                    "provider_name": str(name),
                    "base_url": str(item.get("base_url", "") or "").strip(),
                    "model": str(config.get("model", "") or "").strip(),
                }
    return {}


def _resolve_openai_base_url() -> str:
    explicit = (os.getenv("OPENAI_BASE_URL", "") or "").strip()
    if explicit:
        return explicit
    return _codex_openai_provider_config().get("base_url", "") or "https://api.openai.com/v1"


def _resolve_openai_default_model() -> str:
    for name in ("ARTICLE_DIRECTOR_MODEL", "OPENAI_MODEL"):
        explicit = (os.getenv(name, "") or "").strip()
        if explicit:
            return explicit
    configured = _codex_openai_provider_config().get("model", "") or ""
    return configured or "gpt-5.4"


def _default_single_provider_key() -> str:
    explicit = _normalize_provider_key(os.getenv("ARTICLE_DIRECTOR_PROVIDER", ""))
    if explicit:
        return explicit
    # Codex desktop subscription mode is not an API provider. Default to a
    # Codex handoff packet so the runner never silently calls stale API keys.
    if _env_flag("ARTICLE_DIRECTOR_ALLOW_API_PROVIDER", False) is False:
        return "codex"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    available = _available_provider_keys()
    if "anthropic" in available:
        return "anthropic"
    if "deepseek" in available:
        return "deepseek"
    return "auto"


def _truncate_chars(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[...truncated...]"


def _completed_process_payload(result: subprocess.CompletedProcess[str]) -> str:
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    return stdout or stderr


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return _safe_json_loads(path.read_text(encoding="utf-8"), default)


def _safe_relative_path(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path)


def _path_info(path: Path | None, base: Path | None = None) -> dict[str, Any]:
    if path is None:
        return {}
    info: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "exists": path.exists(),
    }
    if base is not None:
        info["relative_path"] = _safe_relative_path(path, base)
    if path.exists() and path.is_file():
        try:
            info["size_bytes"] = path.stat().st_size
        except OSError:
            pass
    return info


def _clone_default(value: Any) -> Any:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    return value


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_heading_key(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _extract_markdown_sections(text: str, headings: list[str]) -> str:
    if not text.strip():
        return ""
    targets = [_normalize_heading_key(item) for item in headings if str(item).strip()]
    if not targets:
        return text
    lines = text.splitlines()
    heading_re = re.compile(r"^(#{1,6})\s+(.*)$")
    matches: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        match = heading_re.match(line)
        if not match:
            continue
        matches.append((idx, len(match.group(1)), match.group(2).strip()))
    selected: list[str] = []
    for index, (start, level, heading_text) in enumerate(matches):
        normalized = _normalize_heading_key(heading_text)
        if not any(normalized == target or normalized in target or target in normalized for target in targets):
            continue
        end = len(lines)
        for next_start, next_level, _ in matches[index + 1 :]:
            if next_level <= level:
                end = next_start
                break
        section_text = "\n".join(lines[start:end]).strip()
        if section_text:
            selected.append(section_text)
    return "\n\n".join(selected) if selected else ""


def _materialize_module_value(value: Any, namespace: dict[str, Any]) -> Any:
    if isinstance(value, list):
        return [_materialize_module_value(item, namespace) for item in value]
    if isinstance(value, dict):
        return {key: _materialize_module_value(item, namespace) for key, item in value.items()}
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    if text.startswith("str("):
        try:
            return eval(text, {"Path": Path}, namespace)
        except Exception:
            return value
    if text[0] in "[{(":
        try:
            return ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return value
    return value


@dataclass
class NodeConfig:
    node_id: str
    role: str
    skill_file: Path
    temperature: float
    output_file: str
    schema_check_id: str
    input_files: list[str] = field(default_factory=list)
    micro_plan: dict[str, Any] = field(default_factory=dict)
    allowed_inputs: list[Any] = field(default_factory=list)
    micro_plan_id: str = ""
    micro_plan_file: str = ""
    micro_plan_version: str = ""
    micro_plan_mode: str = ""
    revision_source: str = ""
    verification_profile: str = ""
    max_input_tokens: int = 2000
    max_output_tokens: int = 4096
    max_retries: int = 2
    memory_write: dict = field(default_factory=dict)
    estimated_tokens: dict = field(default_factory=dict)
    task_prefix: str = ""
    node_type: str = "agent"
    parallel: bool = False
    provider: str = "auto"
    model_override: str = ""
    package_type: str = ""
    package_score: float = 0.0
    package_order: int = 0
    risk_tier: str = "medium"
    section_group: str = ""
    component_parent: str = ""
    command: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class EdgeConfig:
    from_node: str
    to_node: str


class OpenAICompatProvider:
    def __init__(self, api_key: str, base_url: str, default_model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model

    @staticmethod
    def _extract_text(response: Any) -> str:
        if response is None:
            return ""
        if isinstance(response, str):
            return response
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        choices = getattr(response, "choices", None)
        if choices:
            first = choices[0]
            message = getattr(first, "message", None)
            if message is not None:
                content = getattr(message, "content", "")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts: list[str] = []
                    for item in content:
                        text = getattr(item, "text", None)
                        if isinstance(text, str) and text:
                            parts.append(text)
                    if parts:
                        return "\n".join(parts)
            text = getattr(first, "text", None)
            if isinstance(text, str):
                return text
        if isinstance(response, dict):
            if isinstance(response.get("output_text"), str):
                return response["output_text"]
            choices = response.get("choices") or []
            if choices:
                first = choices[0] or {}
                message = first.get("message") or {}
                content = message.get("content", "")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("text")]
                    if parts:
                        return "\n".join(parts)
                text = first.get("text")
                if isinstance(text, str):
                    return text
        return str(response)

    async def create_message(
        self,
        model: str,
        max_tokens: int,
        temperature: float,
        system: str,
        user_content: str,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=model or self.default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        return self._extract_text(response)


class AnthropicProvider:
    def __init__(self) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic()
        self.default_model = "claude-sonnet-4-6"

    async def create_message(
        self,
        model: str,
        max_tokens: int,
        temperature: float,
        system: str,
        user_content: str,
    ) -> str:
        response = await self._client.messages.create(
            model=model or self.default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text


def create_default_provider() -> Any | None:
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return AnthropicProvider()
        except Exception:
            pass
    if os.getenv("DEEPSEEK_API_KEY"):
        try:
            return OpenAICompatProvider(
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                default_model="deepseek-chat",
            )
        except Exception:
            pass
    if os.getenv("OPENAI_API_KEY"):
        try:
            return OpenAICompatProvider(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=_resolve_openai_base_url(),
                default_model=_resolve_openai_default_model(),
            )
        except Exception:
            pass
    return None


def create_provider(provider_name: str) -> Any | None:
    key = (provider_name or "auto").lower()
    if key == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            return None
        try:
            return AnthropicProvider()
        except Exception:
            return None
    if key == "deepseek":
        if not os.getenv("DEEPSEEK_API_KEY"):
            return None
        try:
            return OpenAICompatProvider(
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                default_model="deepseek-chat",
            )
        except Exception:
            return None
    if key == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            return None
        try:
            return OpenAICompatProvider(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=_resolve_openai_base_url(),
                default_model=_resolve_openai_default_model(),
            )
        except Exception:
            return None
    return create_default_provider()


class WorkflowRunner:
    def __init__(
        self,
        project_id: str,
        topic_id: str,
        title: str,
        brief: str,
        strategy: str,
        skill_root: Path,
        project_root: Path,
        nodes: list[NodeConfig],
        edges: list[EdgeConfig],
    ) -> None:
        self.project_id = project_id
        self.topic_id = topic_id
        self.title = title
        self.brief = brief
        self.strategy = strategy
        self.skill_root = Path(skill_root)
        self.project_root = Path(project_root)
        self.nodes = nodes
        self.edges = edges
        self.project_dir = self.skill_root / "outputs" / project_id
        self.project_dir.mkdir(parents=True, exist_ok=True)
        (self.project_dir / "memory").mkdir(parents=True, exist_ok=True)
        self.state_path = self.project_dir / "workflow-state.json"
        self.index_path = self.project_dir / "workflow-index.json"
        self._provider_cache: dict[str, Any | None] = {}
        self.provider_status_path = self.project_dir / "provider-status.json"
        self.execution_log_path = self.project_dir / "micro-plan" / "execution-log.json"

    def _provider_mode(self) -> str:
        return "single"

    def _single_provider_key(self) -> str:
        return _default_single_provider_key()

    def _single_provider_model(self, provider: Any | None) -> str:
        explicit = (os.getenv("ARTICLE_DIRECTOR_MODEL", "") or "").strip()
        if explicit:
            return explicit
        if provider is not None:
            resolved = getattr(provider, "default_model", "") or ""
            if resolved:
                return resolved
        single_key = self._single_provider_key()
        if single_key == "openai":
            return _resolve_openai_default_model()
        if single_key == "anthropic":
            return "claude-sonnet-4-6"
        if single_key == "deepseek":
            return "deepseek-chat"
        if single_key == "codex":
            return "codex-desktop-subscription"
        fallback_provider = self._provider_for_key(single_key)
        return getattr(fallback_provider, "default_model", "") or ""

    def _default_state(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "topic_id": self.topic_id,
            "title": self.title,
            "status": "running",
            "approved": False,
            "approval": {},
            "approvals": {},
            "completed_nodes": [],
            "failed_nodes": [],
            "retry_counts": {},
            "history": [],
            "ingested_formal_id": "",
            "current_micro_plan_id": "",
            "last_completed_micro_plan_id": "",
            "micro_plan_status": "",
            "current_micro_plan": {},
            "recent_micro_plans": [],
            "revision_chain": [],
            "section_status": {},
            "section_token_usage": {},
            "section_budget_reports": [],
        }

    def _normalize_state(self, state: dict[str, Any]) -> dict[str, Any]:
        defaults = self._default_state()
        for key, value in defaults.items():
            state.setdefault(key, _clone_default(value))
        return state

    def load_state(self) -> dict[str, Any]:
        if self.state_path.exists():
            return self._normalize_state(json.loads(self.state_path.read_text(encoding="utf-8-sig")))
        state = self._default_state()
        self.save_state(state)
        return state

    def save_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = datetime.now().isoformat()
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        index = {
            "project_id": self.project_id,
            "topic_id": self.topic_id,
            "title": self.title,
            "status": state["status"],
            "approved": state["approved"],
            "approvals": state.get("approvals", {}),
            "completed_nodes": state["completed_nodes"],
            "failed_nodes": state["failed_nodes"],
            "current_micro_plan_id": state.get("current_micro_plan_id", ""),
            "last_completed_micro_plan_id": state.get("last_completed_micro_plan_id", ""),
            "micro_plan_status": state.get("micro_plan_status", ""),
        }
        self.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        self._sync_run_ledger(state)

    def _load_expanded_for_ledger(self) -> dict[str, Any]:
        path = self.project_dir / "expanded-workflow.json"
        if path.exists():
            return _safe_json_loads(_read_text(path), {"nodes": [], "edges": []})
        return {
            "nodes": [
                {
                    "node_id": node.node_id,
                    "role": node.role,
                    "node_type": node.node_type,
                    "output_file": node.output_file,
                    "parallel": node.parallel,
                    "schema_check_id": node.schema_check_id,
                    "provider": node.provider,
                }
                for node in self.nodes
            ],
            "edges": [{"from_node": edge.from_node, "to_node": edge.to_node} for edge in self.edges],
        }

    def _sync_run_ledger(self, state: dict[str, Any] | None = None) -> None:
        if _ledger_sync_project is None:
            return
        try:
            _ledger_sync_project(
                self.project_dir,
                AGENT_ID,
                skill_root=self.skill_root,
                state=state or self.load_state(),
                expanded=self._load_expanded_for_ledger(),
                ensure_node_events=False,
                memory_policy={
                    "allowed_global_memory": {
                        "read_policy": "promoted_active_only",
                        "examples": [
                            "memory/review-comment-experience.md as promoted reusable writing guidance",
                        ],
                    },
                    "write_policy": {
                        "run_memory": "outputs/{run_id}/memory/",
                        "topic_feedback": "outputs/{run_id}/memory/interaction-journal.md",
                        "promoted_global_memory": "manual promotion to memory/review-comment-experience.md only",
                    },
                },
            )
        except Exception:
            return

    def _ledger_event(self, event_type: str, node_id: str = "", status: str = "", message: str = "", payload: dict[str, Any] | None = None) -> None:
        if _ledger_append_event is None:
            return
        try:
            _ledger_append_event(self.project_dir, AGENT_ID, event_type, node_id=node_id, status=status, message=message, payload=payload)
        except Exception:
            return

    def _node_event_payload(self, node: NodeConfig, **extra: Any) -> dict[str, Any]:
        output_path = self._resolve_path(node.output_file) if node.output_file else None
        input_paths = [self._resolve_path(raw) for raw in node.input_files]
        payload: dict[str, Any] = {
            "role": node.role,
            "node_type": node.node_type,
            "parallel": node.parallel,
            "provider": node.provider,
            "model_override": node.model_override,
            "temperature": node.temperature,
            "max_input_tokens": node.max_input_tokens,
            "max_output_tokens": node.max_output_tokens,
            "max_retries": node.max_retries,
            "schema_check_id": node.schema_check_id,
            "output": _path_info(output_path, self.project_root),
            "inputs": [_path_info(path, self.project_root) for path in input_paths[:20]],
            "input_count": len(input_paths),
            "skill_file": _path_info(node.skill_file, self.project_root),
            "micro_plan_id": node.micro_plan_id,
            "micro_plan_file": node.micro_plan_file,
            "micro_plan_mode": node.micro_plan_mode,
            "verification_profile": node.verification_profile,
            "package_type": node.package_type,
            "package_score": node.package_score,
            "package_order": node.package_order,
            "risk_tier": node.risk_tier,
            "section_group": node.section_group,
            "component_parent": node.component_parent,
        }
        if node.command:
            try:
                payload["command"] = self._format_command(node)
            except Exception as exc:
                payload["command_error"] = f"{type(exc).__name__}: {exc}"
        for key, value in extra.items():
            if value is not None:
                payload[key] = value
        return payload

    def _record_node_started(self, node: NodeConfig, phase: str, **extra: Any) -> None:
        self._ledger_event(
            "node_started",
            node_id=node.node_id,
            status="running",
            message=f"{phase} node started",
            payload=self._node_event_payload(node, phase=phase, **extra),
        )

    def _record_artifact_available(self, node: NodeConfig, path: Path | None, source_event: str = "") -> None:
        if path is None:
            return
        self._ledger_event(
            "artifact_available",
            node_id=node.node_id,
            status="available" if path.exists() else "missing",
            message=_safe_relative_path(path, self.project_root),
            payload=self._node_event_payload(
                node,
                artifact=_path_info(path, self.project_root),
                source_event=source_event,
            ),
        )

    def _record_validation_event(self, node: NodeConfig, ok: bool, detail: str) -> None:
        if node.schema_check_id == "none":
            event_type = "node_validation_skipped"
            status = "skipped"
        else:
            event_type = "node_validation_passed" if ok else "node_validation_failed"
            status = "passed" if ok else "failed"
        output_path = self._resolve_path(node.output_file) if node.output_file else None
        self._ledger_event(
            event_type,
            node_id=node.node_id,
            status=status,
            message=_truncate_chars(detail or status, 800),
            payload={
                "schema_check_id": node.schema_check_id,
                "output": _path_info(output_path, self.project_root),
                "detail": _truncate_chars(detail or "", 2000),
            },
        )

    def _record_semantic_gate_event(self, node: NodeConfig, ok: bool, reason: str) -> None:
        if node.schema_check_id != "review-diff-result":
            return
        self._ledger_event(
            "semantic_gate_passed" if ok else "semantic_gate_failed",
            node_id=node.node_id,
            status="passed" if ok else "failed",
            message=_truncate_chars(reason or "review diff gate passed", 800),
            payload={
                "gate": "review-diff-result",
                "reason": _truncate_chars(reason or "", 2000),
                "output": _path_info(self._resolve_path(node.output_file), self.project_root),
            },
        )

    def _record_provider_event(
        self,
        node: NodeConfig,
        event_type: str,
        provider_key: str,
        status: str,
        detail: str = "",
        model: str = "",
        **extra: Any,
    ) -> None:
        payload: dict[str, Any] = {
            "provider": provider_key,
            "status": status,
            "model": model,
            "detail": _truncate_chars(detail or "", 2000),
        }
        payload.update({key: value for key, value in extra.items() if value is not None})
        self._ledger_event(
            event_type,
            node_id=node.node_id,
            status=status,
            message=f"{provider_key}: {status}",
            payload=payload,
        )

    def _journal(self, node_id: str, status: str, summary: str) -> None:
        path = self.project_dir / "memory" / "interaction-journal.md"
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"## [{stamp}] {node_id} - {status}\n{summary}\n")

    def _micro_plan_status_snapshot(self, node: NodeConfig, micro_plan: dict[str, Any], status: str) -> dict[str, Any]:
        if not micro_plan:
            return {}
        return {
            "recorded_at": datetime.now().isoformat(),
            "status": status,
            "node_id": node.node_id,
            "micro_plan_id": micro_plan.get("micro_plan_id", node.micro_plan_id),
            "mode": micro_plan.get("mode", node.micro_plan_mode or "standard"),
            "allowed_inputs": micro_plan.get("allowed_inputs", node.allowed_inputs),
            "plan": micro_plan,
        }

    def _remember_micro_plan_state(self, node: NodeConfig, micro_plan: dict[str, Any], status: str) -> None:
        if not micro_plan:
            return
        snapshot = self._micro_plan_status_snapshot(node, micro_plan, status)
        state = self.load_state()
        state["micro_plan_status"] = status
        if status in {"started", "instruction"}:
            state["current_micro_plan_id"] = snapshot.get("micro_plan_id", "")
            state["current_micro_plan"] = snapshot
        else:
            state["current_micro_plan_id"] = ""
            state["current_micro_plan"] = {}
            if status == "completed":
                state["last_completed_micro_plan_id"] = snapshot.get("micro_plan_id", "")
            recent = [item for item in state.get("recent_micro_plans", []) if item.get("micro_plan_id") != snapshot.get("micro_plan_id")]
            recent.insert(0, snapshot)
            state["recent_micro_plans"] = recent[:10]
        self.save_state(state)

    def _append_execution_log(self, node: NodeConfig, micro_plan: dict[str, Any], status: str) -> None:
        if not micro_plan:
            return
        self.execution_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _safe_json_loads(_read_text(self.execution_log_path), {"events": []})
        payload.setdefault("events", []).append(self._micro_plan_status_snapshot(node, micro_plan, status))
        payload["current_micro_plan"] = {} if status in {"completed", "failed", "failed-validation"} else self._micro_plan_status_snapshot(node, micro_plan, status)
        recent = [item for item in payload.get("recent_micro_plans", []) if item.get("micro_plan_id") != micro_plan.get("micro_plan_id", node.micro_plan_id)]
        if status in {"completed", "failed", "failed-validation"}:
            recent.insert(0, self._micro_plan_status_snapshot(node, micro_plan, status))
        payload["recent_micro_plans"] = recent[:10]
        self.execution_log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _mark_workflow_completed(self) -> None:
        state = self.load_state()
        if state.get("status") != "completed":
            state["status"] = "completed"
            self.save_state(state)
            self._ledger_event(
                "run_completed",
                status="completed",
                message="all nodes completed",
                payload={
                    "completed_nodes": len(state.get("completed_nodes", [])),
                    "failed_nodes": len(state.get("failed_nodes", [])),
                    "project_id": self.project_id,
                    "topic_id": self.topic_id,
                },
            )

    def _has_unresolved_failures(self, state: dict[str, Any]) -> bool:
        done = set(state.get("completed_nodes", []))
        failed = set(state.get("failed_nodes", []))
        return any(node_id not in done for node_id in failed)

    def _node_map(self) -> dict[str, NodeConfig]:
        return {node.node_id: node for node in self.nodes}

    def _ready_nodes(self, state: dict[str, Any]) -> list[NodeConfig]:
        done = set(state["completed_nodes"])
        pending: list[NodeConfig] = []
        for node in self.nodes:
            if node.node_id in done:
                continue
            parents = [edge.from_node for edge in self.edges if edge.to_node == node.node_id]
            if all(parent in done for parent in parents):
                pending.append(node)
        return pending

    def _retry_limit_reached(self, state: dict[str, Any], node: NodeConfig) -> bool:
        if node.max_retries < 0:
            return False
        retry_count = int(state.get("retry_counts", {}).get(node.node_id, 0) or 0)
        return retry_count >= node.max_retries

    def _stop_for_retry_limit(self, state: dict[str, Any], node: NodeConfig) -> bool:
        if not self._retry_limit_reached(state, node):
            return False
        retry_count = int(state.get("retry_counts", {}).get(node.node_id, 0) or 0)
        state["status"] = "waiting-human-review"
        self.save_state(state)
        payload = {
            "type": "RETRY_LIMIT_REACHED",
            "project_id": self.project_id,
            "topic_id": self.topic_id,
            "node_id": node.node_id,
            "retry_count": retry_count,
            "max_retries": node.max_retries,
            "revision_source": node.revision_source,
            "message": "Retry limit reached; review failure context before rerunning this node.",
        }
        self._ledger_event("node_retry_limit_reached", node_id=node.node_id, status="waiting_human", payload=payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return True

    def _select_parallel_nodes(self, nodes: list[NodeConfig]) -> list[NodeConfig]:
        section_nodes = [node for node in nodes if node.section_group]
        if not section_nodes:
            return nodes
        selected: list[NodeConfig] = []
        seen_sections: set[str] = set()
        for node in section_nodes:
            if node.section_group in seen_sections:
                continue
            if len(seen_sections) >= MAX_PARALLEL_SECTIONS:
                break
            selected.append(node)
            seen_sections.add(node.section_group)
        return selected

    def _approval_key_for_node(self, node: NodeConfig) -> str:
        explicit = (node.env or {}).get("approval_key", "").strip()
        if explicit:
            return explicit
        return node.node_id

    def _human_approval_payload(self, node: NodeConfig) -> dict[str, Any]:
        approval_key = self._approval_key_for_node(node)
        default_message = "Human approval is required before the workflow can continue."
        if approval_key == "outline-confirmation":
            default_message = "大纲和细纲已生成并完成检查，请先人工确认后再进入正文分包与写作。"
        message = (node.env or {}).get("approval_message", "").strip() or default_message
        return {
            "type": "HUMAN_APPROVAL",
            "project_id": self.project_id,
            "topic_id": self.topic_id,
            "title": self.title,
            "node_id": node.node_id,
            "approval_key": approval_key,
            "message": message,
        }

    def _is_node_approved(self, state: dict[str, Any], node: NodeConfig) -> bool:
        approval_key = self._approval_key_for_node(node)
        approvals = state.get("approvals", {})
        return bool(approvals.get(approval_key, {}).get("approved"))

    def _resolve_path(self, raw: str) -> Path:
        path = Path(raw)
        return path if path.is_absolute() else self.project_root / path

    def _estimate_tokens(self, *parts: str) -> int:
        total_chars = sum(len(part or "") for part in parts)
        return max(1, total_chars // 2)

    def _section_dir(self, section_group: str) -> Path:
        return self.project_dir / "sections" / section_group

    def _write_section_budget_report(
        self,
        node: NodeConfig,
        used_tokens: int,
        threshold: int,
        level: str,
    ) -> Path:
        section_dir = self._section_dir(node.section_group)
        section_dir.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for path in sorted(section_dir.glob("*")):
            if path.is_file():
                artifacts.append(path.name)
        report_path = section_dir / "budget-report.md"
        report = [
            f"# Section Budget Report: {node.section_group}",
            "",
            f"- level: {level}",
            f"- current_node: {node.node_id}",
            f"- estimated_tokens: {used_tokens}",
            f"- threshold: {threshold}",
            f"- status: {'waiting-human-review' if level == 'hard' else 'soft-warning'}",
            "",
            "## Current Artifacts",
        ]
        report.extend([f"- {name}" for name in artifacts] or ["- none"])
        report.extend(
            [
                "",
                "## Human Checkpoint",
                "- Review current progress, blockers, and artifacts before continuing if the hard cap was reached.",
                "- If the output is acceptable, mark the failed node done or raise the cap before rerunning.",
            ]
        )
        report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
        return report_path

    def _record_section_usage(self, node: NodeConfig, prompt_text: str, response_text: str) -> tuple[bool, str]:
        if not node.section_group:
            return True, ""
        added = self._estimate_tokens(prompt_text, response_text)
        state = self.load_state()
        usage = state.setdefault("section_token_usage", {})
        used_tokens = int(usage.get(node.section_group, 0) or 0) + added
        usage[node.section_group] = used_tokens
        section_status = state.setdefault("section_status", {})
        section_status[node.section_group] = {
            "last_node": node.node_id,
            "estimated_tokens": used_tokens,
            "updated_at": datetime.now().isoformat(),
        }
        if used_tokens >= SECTION_HARD_TOKEN_CAP:
            report_path = self._write_section_budget_report(node, used_tokens, SECTION_HARD_TOKEN_CAP, "hard")
            state["status"] = "waiting-human-review"
            state.setdefault("section_budget_reports", []).append(
                {
                    "time": datetime.now().isoformat(),
                    "section_group": node.section_group,
                    "node_id": node.node_id,
                    "level": "hard",
                    "estimated_tokens": used_tokens,
                    "report": str(report_path),
                }
            )
            self.save_state(state)
            return False, f"section token hard cap exceeded: {node.section_group} used≈{used_tokens}; report={report_path}"
        if used_tokens >= SECTION_SOFT_TOKEN_CAP:
            report_path = self._write_section_budget_report(node, used_tokens, SECTION_SOFT_TOKEN_CAP, "soft")
            state.setdefault("section_budget_reports", []).append(
                {
                    "time": datetime.now().isoformat(),
                    "section_group": node.section_group,
                    "node_id": node.node_id,
                    "level": "soft",
                    "estimated_tokens": used_tokens,
                    "report": str(report_path),
                }
            )
        self.save_state(state)
        return True, ""

    def _format_command(self, node: NodeConfig) -> list[str]:
        mapping = {
            "python": sys.executable,
            "project_root": str(self.project_root),
            "skill_root": str(self.skill_root),
            "topic_id": self.topic_id,
            "project_id": self.project_id,
            "title": self.title,
        }
        return [part.format(**mapping) for part in node.command]

    def _validate_output(self, node: NodeConfig) -> tuple[bool, str]:
        if node.schema_check_id == "none":
            return True, ""
        output_path = self._resolve_path(node.output_file)
        if not output_path.exists():
            return False, f"missing output file: {output_path}"
        validator = self.skill_root / "scripts" / "validate_output.py"
        result = subprocess.run(
            [sys.executable, str(validator), "--output", str(output_path), "--schema", node.schema_check_id],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return True, _completed_process_payload(result)
        return False, _completed_process_payload(result)

    def _run_script_node(self, node: NodeConfig) -> bool:
        if not node.command:
            self._record_node_started(node, "script", error="missing command")
            self.mark_failed(node.node_id, "script node missing command")
            return False
        output_path = self._resolve_path(node.output_file) if node.output_file else None
        output_snapshot: tuple[bool, int, int] | None = None
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.exists():
                stat = output_path.stat()
                output_snapshot = (True, stat.st_mtime_ns, stat.st_size)
            else:
                output_snapshot = (False, 0, 0)
        command = self._format_command(node)
        self._record_node_started(node, "script", command=command)
        env = os.environ.copy()
        env.update(node.env)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(self.project_root),
        )
        payload = _completed_process_payload(result)
        self._ledger_event(
            "script_process_completed",
            node_id=node.node_id,
            status="completed" if result.returncode == 0 else "failed",
            message=_truncate_chars(payload or f"returncode={result.returncode}", 800),
            payload={
                "returncode": result.returncode,
                "command": command,
                "stdout_chars": len(result.stdout or ""),
                "stderr_chars": len(result.stderr or ""),
                "stdout_preview": _truncate_chars((result.stdout or "").strip(), 1200),
                "stderr_preview": _truncate_chars((result.stderr or "").strip(), 1200),
            },
        )
        script_wrote_output = False
        if output_path and output_path.exists() and output_snapshot is not None:
            stat = output_path.stat()
            existed, mtime_ns, size = output_snapshot
            script_wrote_output = (not existed) or stat.st_mtime_ns != mtime_ns or stat.st_size != size
        if output_path and payload and not script_wrote_output:
            output_path.write_text(payload, encoding="utf-8")
            self._record_artifact_available(node, output_path, source_event="script_process_completed")
        elif output_path and script_wrote_output:
            self._record_artifact_available(node, output_path, source_event="script_process_completed")
        if result.returncode != 0:
            self.mark_failed(node.node_id, payload or f"command failed: {command}")
            return False
        ok, validation_payload = self._validate_output(node)
        self._record_validation_event(node, ok, validation_payload)
        if not ok:
            self.mark_failed(node.node_id, validation_payload)
            return False
        semantic_ok, semantic_reason = self._evaluate_script_gate(node)
        self._record_semantic_gate_event(node, semantic_ok, semantic_reason)
        if not semantic_ok:
            self.mark_failed(node.node_id, semantic_reason)
            return False
        self.mark_done(node.node_id, payload or validation_payload)
        return True

    def _latest_revision_entry(self, node_id: str) -> dict[str, Any]:
        state = self.load_state()
        entries = [item for item in state.get("revision_chain", []) if item.get("node_id") == node_id]
        if not entries:
            return {}
        return entries[-1]

    def _load_micro_plan(self, node: NodeConfig) -> dict[str, Any]:
        plan: dict[str, Any] = {}
        latest_revision = self._latest_revision_entry(node.node_id)
        preferred_file = str(latest_revision.get("revision_plan") or "")
        if not preferred_file:
            preferred_file = node.micro_plan_file
        if preferred_file:
            plan_path = self._resolve_path(preferred_file)
            if plan_path.exists():
                raw_text = _read_text(plan_path).strip()
                payload = _safe_json_loads(raw_text, None)
                if payload is None:
                    try:
                        payload = ast.literal_eval(raw_text)
                    except (SyntaxError, ValueError):
                        payload = {}
                if isinstance(payload, dict):
                    if isinstance(payload.get("micro_plans"), list) and node.micro_plan_id:
                        for item in payload.get("micro_plans", []):
                            if item.get("micro_plan_id") == node.micro_plan_id:
                                plan.update(item)
                                break
                    else:
                        plan.update(payload)
        if node.micro_plan:
            plan.update(node.micro_plan)
        if plan and node.micro_plan_id and "micro_plan_id" not in plan:
            plan["micro_plan_id"] = node.micro_plan_id
        if plan and node.micro_plan_mode and "mode" not in plan:
            plan["mode"] = node.micro_plan_mode
        if "allowed_inputs" not in plan and node.allowed_inputs:
            plan["allowed_inputs"] = node.allowed_inputs
        if latest_revision and "revision_source" not in plan:
            plan["revision_source"] = latest_revision.get("revision_plan", "")
        return plan

    def _evaluate_script_gate(self, node: NodeConfig) -> tuple[bool, str]:
        if node.schema_check_id != "review-diff-result":
            return True, ""
        output_path = self._resolve_path(node.output_file)
        payload = _read_json(output_path, {})
        if not isinstance(payload, dict):
            return False, "review diff output is not valid json object"
        if payload.get("pass") is True and payload.get("consensus") == "approved":
            return True, ""
        if payload.get("consensus") == "human-review":
            return True, ""
        rollback_target = payload.get("rollback_target", "manual-triage")
        blocking = payload.get("blocking_issues", [])
        summary = str(payload.get("summary") or "review diff gate failed")
        if isinstance(blocking, list):
            blocking_preview = []
            for item in blocking[:3]:
                if isinstance(item, dict):
                    blocking_preview.append(str(item.get("issue") or item.get("message") or ""))
                else:
                    blocking_preview.append(str(item))
            blocking_text = "; ".join([item for item in blocking_preview if item])
        else:
            blocking_text = ""
        reason = f"{summary}; rollback={rollback_target}"
        if blocking_text:
            reason += f"; blocking={blocking_text}"
        return False, reason

    def _append_execution_log(self, node: NodeConfig, micro_plan: dict[str, Any], status: str) -> None:
        if not micro_plan:
            return
        self.execution_log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _safe_json_loads(_read_text(self.execution_log_path), {"events": []})
        snapshot = self._micro_plan_status_snapshot(node, micro_plan, status)
        payload.setdefault("events", []).append(snapshot)
        payload["current_micro_plan"] = {} if status in {"completed", "failed", "failed-validation"} else snapshot
        recent = [item for item in payload.get("recent_micro_plans", []) if item.get("micro_plan_id") != snapshot.get("micro_plan_id")]
        if status in {"completed", "failed", "failed-validation"}:
            recent.insert(0, snapshot)
        payload["recent_micro_plans"] = recent[:10]
        self.execution_log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _resolve_allowed_inputs(self, node: NodeConfig, micro_plan: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
        explicit = "allowed_inputs" in micro_plan or bool(node.allowed_inputs)
        raw_entries = micro_plan.get("allowed_inputs", node.allowed_inputs)
        entries: list[dict[str, Any]] = []
        for item in _as_list(raw_entries):
            if isinstance(item, str):
                if item in {"full_text", "markdown_sections", "article_package"}:
                    entries.append({"mode": item})
                else:
                    entries.append({"mode": "full_text", "path": item})
                continue
            if isinstance(item, dict):
                entry = dict(item)
                entry["mode"] = str(entry.get("mode") or entry.get("kind") or "full_text").strip()
                entries.append(entry)
        return entries, explicit

    def _candidate_input_paths(self, node: NodeConfig, entry: dict[str, Any]) -> list[Path]:
        raw_paths: list[str] = []
        for key in ("path", "file", "source", "input_file"):
            if entry.get(key):
                raw_paths.append(str(entry[key]))
        raw_paths.extend(str(item) for item in _as_list(entry.get("paths")))
        raw_paths.extend(str(item) for item in _as_list(entry.get("input_files")))
        if raw_paths:
            return [self._resolve_path(raw) for raw in raw_paths]
        candidates = [self._resolve_path(raw) for raw in node.input_files]
        mode = entry.get("mode", "full_text")
        if mode == "markdown_sections":
            return [path for path in candidates if path.suffix.lower() in {".md", ".markdown"}]
        if mode == "article_package":
            preferred = [path for path in candidates if path.name == "article-packages.json"]
            return preferred or [path for path in candidates if "package" in path.stem.lower()]
        return candidates

    def _extract_markdown_sections(self, text: str, headings: list[str]) -> str:
        return _extract_markdown_sections(text, headings)

    def _extract_article_package(self, text: str, package_id: str, package_order: int = 0) -> str:
        payload = _safe_json_loads(text, {})
        if not isinstance(payload, dict):
            return text
        packages = payload.get("packages", [])
        if not isinstance(packages, list):
            return text
        for package in packages:
            if package_id and package.get("package_id") == package_id:
                return json.dumps(package, ensure_ascii=False, indent=2)
            if package_order and int(package.get("package_order", 0) or 0) == int(package_order):
                return json.dumps(package, ensure_ascii=False, indent=2)
        return text

    def _section_headings_for_entry(self, node: NodeConfig, entry: dict[str, Any], micro_plan: dict[str, Any]) -> list[str]:
        headings = [
            str(item)
            for item in _as_list(
                entry.get("section_headings") or entry.get("headings") or micro_plan.get("section_headings")
            )
            if str(item).strip()
        ]
        if headings:
            return headings
        package_id = entry.get("package_id") or micro_plan.get("package_id")
        if not package_id:
            return []
        for raw_path in node.input_files:
            if Path(raw_path).name != "article-packages.json":
                continue
            payload = _read_json(self._resolve_path(raw_path), {})
            for package in payload.get("packages", []):
                if package.get("package_id") == package_id:
                    return [str(item) for item in package.get("section_headings", []) if str(item).strip()]
        return []

    def _section_ids_for_entry(self, node: NodeConfig, entry: dict[str, Any], micro_plan: dict[str, Any]) -> list[str]:
        section_ids = [
            str(item).strip()
            for item in _as_list(entry.get("section_id") or entry.get("section_ids") or micro_plan.get("section_ids"))
            if str(item).strip()
        ]
        if section_ids:
            return section_ids
        if node.section_group:
            return [node.section_group]
        return []

    def _extract_manifest_section(self, text: str, node: NodeConfig, entry: dict[str, Any], micro_plan: dict[str, Any]) -> str:
        payload = _safe_json_loads(text, {})
        if not isinstance(payload, dict):
            return text
        section_ids = set(self._section_ids_for_entry(node, entry, micro_plan))
        if not section_ids:
            return text
        sections = [
            section
            for section in payload.get("sections", [])
            if str(section.get("section_id") or "") in section_ids
        ]
        compact = {
            "topic_id": payload.get("topic_id", self.topic_id),
            "section_count": payload.get("section_count", len(payload.get("sections", []))),
            "sections": sections,
        }
        return json.dumps(compact, ensure_ascii=False, indent=2)

    def _extract_manifest_summary(self, text: str) -> str:
        payload = _safe_json_loads(text, {})
        if not isinstance(payload, dict):
            return text
        sections = []
        for section in payload.get("sections", []):
            sections.append(
                {
                    "section_id": section.get("section_id", ""),
                    "heading": section.get("heading", ""),
                    "target_word_count": section.get("target_word_count", 0),
                    "risk_tier": section.get("risk_tier", ""),
                }
            )
        compact = {
            "topic_id": payload.get("topic_id", self.topic_id),
            "section_count": payload.get("section_count", len(sections)),
            "sections": sections,
        }
        return json.dumps(compact, ensure_ascii=False, indent=2)

    def _render_allowed_input(
        self,
        node: NodeConfig,
        entry: dict[str, Any],
        fallback_limit: int,
        micro_plan: dict[str, Any],
    ) -> list[tuple[str, str]]:
        rendered_entries: list[tuple[str, str]] = []
        mode = entry.get("mode", "full_text")
        for path in self._candidate_input_paths(node, entry):
            if not path.exists():
                continue
            text = _read_text(path)
            if not text:
                continue
            if mode == "markdown_sections":
                headings = self._section_headings_for_entry(node, entry, micro_plan)
                text = self._extract_markdown_sections(text, headings) or text
            elif mode == "article_package":
                package_id = entry.get("package_id") or micro_plan.get("package_id") or ""
                package_order = int(entry.get("package_order", 0) or micro_plan.get("package_order", 0) or node.package_order or 0)
                text = self._extract_article_package(text, package_id, package_order)
            elif mode in {"section_manifest", "manifest_section"}:
                text = self._extract_manifest_section(text, node, entry, micro_plan)
            elif mode in {"section_manifest_summary", "manifest_summary"}:
                text = self._extract_manifest_summary(text)
            max_chars = int(entry.get("max_chars") or fallback_limit * 2)
            rendered_entries.append((path.name, _truncate_chars(text, max_chars)))
        return rendered_entries

    def _build_context(self, node: NodeConfig, micro_plan: dict[str, Any]) -> str:
        chunks: list[str] = [
            "\n\n## Workflow Context\n"
            f"topic_id: {self.topic_id}\n"
            f"title: {self.title}\n"
            f"brief: {self.brief or '(none)'}\n"
            f"strategy: {self.strategy or '(none)'}"
        ]
        if micro_plan:
            plan_text = json.dumps(micro_plan, ensure_ascii=False, indent=2)
            chunks.append("\n\n## Micro Plan\n" + _truncate_chars(plan_text, max(node.max_input_tokens * 2, 2000)))
        allowed_inputs, explicit = self._resolve_allowed_inputs(node, micro_plan)
        if explicit:
            for entry in allowed_inputs:
                for label, rendered in self._render_allowed_input(node, entry, node.max_input_tokens, micro_plan):
                    if rendered:
                        chunks.append(f"\n\n## Input ({entry.get('mode', 'full_text')}): {label}\n{rendered}")
            return "".join(chunks).strip()
        for raw_path in node.input_files:
            path = self._resolve_path(raw_path)
            if not path.exists():
                continue
            text = _read_text(path)
            chunks.append(f"\n\n## Input: {path.name}\n{_truncate_chars(text, node.max_input_tokens * 2)}")
        return "".join(chunks).strip()

    async def _run_agent_node_async(self, node: NodeConfig, provider: Any, model: str = "", provider_key: str = "") -> tuple[bool, str]:
        if provider is None:
            return False, "no provider available"
        skill_text = _read_text(node.skill_file)
        micro_plan = self._load_micro_plan(node)
        context = self._build_context(node, micro_plan)
        if micro_plan:
            self._remember_micro_plan_state(node, micro_plan, "started")
            self._append_execution_log(node, micro_plan, "started")
        user_content = f"{node.task_prefix}\n\n{context}".strip() if node.task_prefix else context
        request_model = node.model_override or model or getattr(provider, "default_model", "")
        if self._provider_mode() == "single":
            request_model = self._single_provider_model(provider)
        effective_provider = provider_key or node.provider or "auto"
        self._ledger_event(
            "agent_context_built",
            node_id=node.node_id,
            status="ready",
            message=f"context_chars={len(context or '')}",
            payload=self._node_event_payload(
                node,
                provider=effective_provider,
                model=request_model,
                context_chars=len(context or ""),
                skill_chars=len(skill_text or ""),
                user_content_chars=len(user_content or ""),
                has_micro_plan=bool(micro_plan),
            ),
        )
        self._record_provider_event(
            node,
            "provider_request_started",
            effective_provider,
            "running",
            model=request_model,
            context_chars=len(context or ""),
            user_content_chars=len(user_content or ""),
        )
        try:
            response_text = await provider.create_message(
                model=request_model,
                max_tokens=node.max_output_tokens,
                temperature=node.temperature,
                system=skill_text,
                user_content=user_content or f"请按 {node.role} 的角色执行任务。",
            )
        except Exception as exc:
            self._record_provider_event(
                node,
                "provider_request_failed",
                effective_provider,
                "failed",
                detail=f"{type(exc).__name__}: {exc}",
                model=request_model,
            )
            return False, f"{type(exc).__name__}: {exc}"
        self._record_provider_event(
            node,
            "provider_request_completed",
            effective_provider,
            "completed",
            detail=f"response_chars={len(response_text or '')}",
            model=request_model,
            response_chars=len(response_text or ""),
        )
        output_path = self._resolve_path(node.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(response_text, encoding="utf-8")
        self._record_artifact_available(node, output_path, source_event="provider_request_completed")
        budget_ok, budget_reason = self._record_section_usage(node, user_content, response_text)
        if not budget_ok:
            self._ledger_event(
                "section_budget_failed",
                node_id=node.node_id,
                status="failed",
                message=_truncate_chars(budget_reason, 800),
                payload={
                    "section_group": node.section_group,
                    "reason": _truncate_chars(budget_reason, 2000),
                    "output": _path_info(output_path, self.project_root),
                },
            )
            return False, budget_reason
        ok, validation_payload = self._validate_output(node)
        self._record_validation_event(node, ok, validation_payload)
        if not ok:
            return False, validation_payload
        return True, response_text

    def _provider_keys_for(self, node: NodeConfig) -> list[str]:
        return [self._single_provider_key()]

    def _provider_for_key(self, key: str) -> Any | None:
        if key not in self._provider_cache:
            self._provider_cache[key] = create_provider(key)
        return self._provider_cache[key]

    def _write_provider_status(self, node_id: str, tried: list[dict[str, str]]) -> None:
        payload = {
            "updated_at": datetime.now().isoformat(),
            "node_id": node_id,
            "provider_mode": f"single-{self._single_provider_key()}",
            "effective_provider": self._single_provider_key(),
            "effective_model": self._single_provider_model(None),
            "tried": tried,
        }
        self.provider_status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _codex_task_path(self, node: NodeConfig) -> Path:
        return self.project_dir / "codex-tasks" / f"{node.node_id}.json"

    def _public_codex_task_payload(self, task_payload: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in task_payload.items() if k not in {"system_prompt", "user_content"}}

    def _build_codex_task_payload(self, node: NodeConfig) -> dict[str, Any]:
        self._record_node_started(node, "codex-handoff")
        skill_text = _read_text(node.skill_file)
        micro_plan = self._load_micro_plan(node)
        context = self._build_context(node, micro_plan)
        if micro_plan:
            self._remember_micro_plan_state(node, micro_plan, "instruction")
            self._append_execution_log(node, micro_plan, "instruction")
        user_content = f"{node.task_prefix}\n\n{context}".strip() if node.task_prefix else context
        output_path = self._resolve_path(node.output_file) if node.output_file else None
        task_payload = {
            "type": "CODEX_NODE_TASK",
            "project_id": self.project_id,
            "topic_id": self.topic_id,
            "title": self.title,
            "node_id": node.node_id,
            "role": node.role,
            "execution_mode": "codex-desktop-subscription",
            "reason": "Use the current Codex paid desktop session. Do not call OpenAI/DeepSeek/Anthropic API providers.",
            "skill_file": str(node.skill_file),
            "output_file": node.output_file,
            "output_path": str(output_path) if output_path else "",
            "schema_check_id": node.schema_check_id,
            "temperature": node.temperature,
            "package_type": node.package_type,
            "risk_tier": node.risk_tier,
            "section_group": node.section_group,
            "input_files": node.input_files,
            "allowed_inputs": micro_plan.get("allowed_inputs", node.allowed_inputs) if micro_plan else node.allowed_inputs,
            "micro_plan": micro_plan,
            "system_prompt": skill_text,
            "user_content": user_content or f"请按 {node.role} 的角色执行任务。",
            "validation": {
                "submit_command": (
                    "python skills\\article-director\\scripts\\workflow_runner.py "
                    "--script <workflow-script> "
                    f"--submit-codex-node {node.node_id} --content-file <output-file>"
                ),
                "must_write_output_path_first": bool(output_path),
            },
        }
        task_path = self._codex_task_path(node)
        task_path.parent.mkdir(parents=True, exist_ok=True)
        task_path.write_text(json.dumps(task_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        state = self.load_state()
        state["status"] = "waiting-codex-node"
        state["current_codex_node_id"] = node.node_id
        state["current_codex_task_path"] = str(task_path)
        self.save_state(state)
        self._ledger_event(
            "codex_node_task_ready",
            node_id=node.node_id,
            status="waiting_codex",
            message=str(task_path),
            payload=self._node_event_payload(
                node,
                execution_mode="codex-desktop-subscription",
                codex_task=_path_info(task_path, self.project_root),
                output=_path_info(output_path, self.project_root),
                context_chars=len(context or ""),
                user_content_chars=len(user_content or ""),
                skill_chars=len(skill_text or ""),
            ),
        )
        return task_payload

    def _prepare_codex_node(self, node: NodeConfig) -> dict[str, Any]:
        task_payload = self._build_codex_task_payload(node)
        task_path = self._codex_task_path(node)
        state = self.load_state()
        state["status"] = "waiting-codex-node"
        state["current_codex_node_id"] = node.node_id
        state["current_codex_task_path"] = str(task_path)
        state.pop("current_codex_node_ids", None)
        state.pop("current_codex_task_paths", None)
        state.pop("current_codex_batch_path", None)
        self.save_state(state)
        print(json.dumps(self._public_codex_task_payload(task_payload), ensure_ascii=False, indent=2))
        return task_payload

    def _prepare_codex_nodes(self, nodes: list[NodeConfig]) -> list[dict[str, Any]]:
        if len(nodes) == 1:
            return [self._prepare_codex_node(nodes[0])]
        task_payloads = [self._build_codex_task_payload(node) for node in nodes]
        task_paths = [str(self._codex_task_path(node)) for node in nodes]
        batch_path = self.project_dir / "codex-tasks" / f"batch-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        batch_payload = {
            "type": "CODEX_NODE_TASK_BATCH",
            "project_id": self.project_id,
            "topic_id": self.topic_id,
            "title": self.title,
            "max_parallel": MAX_PARALLEL_SECTIONS,
            "node_ids": [node.node_id for node in nodes],
            "task_paths": task_paths,
            "tasks": [self._public_codex_task_payload(payload) for payload in task_payloads],
        }
        batch_path.parent.mkdir(parents=True, exist_ok=True)
        batch_path.write_text(json.dumps(batch_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        state = self.load_state()
        state["status"] = "waiting-codex-batch"
        state["current_codex_node_id"] = nodes[0].node_id
        state["current_codex_task_path"] = str(batch_path)
        state["current_codex_node_ids"] = [node.node_id for node in nodes]
        state["current_codex_task_paths"] = task_paths
        state["current_codex_batch_path"] = str(batch_path)
        self.save_state(state)
        self._ledger_event(
            "codex_node_batch_ready",
            status="waiting_codex",
            message=str(batch_path),
            payload={
                "node_ids": [node.node_id for node in nodes],
                "task_paths": task_paths,
                "batch_path": str(batch_path),
                "max_parallel": MAX_PARALLEL_SECTIONS,
            },
        )
        print(json.dumps(batch_payload, ensure_ascii=False, indent=2))
        return task_payloads

    def submit_codex_node(self, node_id: str, content_file: str) -> None:
        node = self._node_map().get(node_id)
        if node is None:
            raise SystemExit(f"unknown node: {node_id}")
        source_path = Path(content_file)
        if not source_path.is_absolute():
            source_path = self.project_root / source_path
        if not source_path.exists():
            raise SystemExit(f"content file not found: {source_path}")
        content = source_path.read_text(encoding="utf-8")
        output_path = self._resolve_path(node.output_file) if node.output_file else source_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != output_path.resolve():
            output_path.write_text(content, encoding="utf-8")
        self._record_artifact_available(node, output_path, source_event="codex_node_submitted")
        ok, validation_payload = self._validate_output(node)
        self._record_validation_event(node, ok, validation_payload)
        if not ok:
            self.mark_failed(node.node_id, f"codex node validation failed: {validation_payload}")
            raise SystemExit(1)
        self._ledger_event(
            "codex_node_submitted",
            node_id=node.node_id,
            status="completed",
            message=_safe_relative_path(output_path, self.project_root),
            payload=self._node_event_payload(
                node,
                execution_mode="codex-desktop-subscription",
                submitted_from=_path_info(source_path, self.project_root),
                output=_path_info(output_path, self.project_root),
            ),
        )
        state = self.load_state()
        pending_ids = [str(item) for item in state.get("current_codex_node_ids", []) if str(item) != node_id]
        pending_paths = [
            str(item)
            for item in state.get("current_codex_task_paths", [])
            if Path(str(item)).stem != node_id
        ]
        if pending_ids:
            state["status"] = "waiting-codex-batch"
            state["current_codex_node_ids"] = pending_ids
            state["current_codex_task_paths"] = pending_paths
            state["current_codex_node_id"] = pending_ids[0]
            state["current_codex_task_path"] = str(state.get("current_codex_batch_path") or "")
        else:
            state.pop("current_codex_node_id", None)
            state.pop("current_codex_task_path", None)
            state.pop("current_codex_node_ids", None)
            state.pop("current_codex_task_paths", None)
            state.pop("current_codex_batch_path", None)
            state["status"] = "running"
        self.save_state(state)
        self.mark_done(node.node_id, f"codex submitted: {_safe_relative_path(output_path, self.project_root)}")

    def _find_image_component(self, node: NodeConfig) -> tuple[dict[str, Any], dict[str, Any]]:
        component_manifest = _read_json(
            self.project_root / "skills" / "article-director" / "outputs" / self.topic_id / "image-component-manifest.json",
            {"components": []},
        )
        image_manifest = _read_json(
            self.project_root / "skills" / "article-director" / "outputs" / self.topic_id / "image-manifest-source.json",
            {"images": []},
        )
        component_payload: dict[str, Any] = {}
        image_payload: dict[str, Any] = {}
        for item in component_manifest.get("components", []):
            if item.get("component_id") == node.node_id:
                component_payload = item
                break
        image_id = str(component_payload.get("image_id") or node.component_parent or "")
        if image_id:
            for item in image_manifest.get("images", []):
                if item.get("image_id") == image_id:
                    image_payload = item
                    break
        return component_payload, image_payload

    def _render_image_component_fallback(self, node: NodeConfig) -> str:
        component_payload, image_payload = self._find_image_component(node)
        component_name = str(component_payload.get("component_name") or node.node_id.rsplit("-", 1)[-1] or "component")
        image_id = str(component_payload.get("image_id") or node.component_parent or "")
        kind = str(component_payload.get("kind") or image_payload.get("kind") or "diagram")
        section_id = str(image_payload.get("target_section_id") or "")
        heading = str(image_payload.get("target_heading") or image_payload.get("insert_after_heading") or "")
        output_asset = f"assets/publish-ready/{self.topic_id}/{image_id}.png" if image_id else ""
        kind_note_map = {
            "chart": "本图属于概念型图表，重点是把正文里的判断关系画清楚，不承担精确统计证明。",
            "diagram": "本图属于结构说明图，重点是把角色关系、流程顺序或控制边界讲清楚。",
            "comparison": "本图属于对照图，重点是把两种做法和结果差异并排讲清楚。",
            "screenshot": "本图属于截图说明图，重点是圈定读者应该注意的区域和操作顺序。",
            "cover": "本图属于封面图，重点是压缩主题信息并建立统一识别感。",
        }
        component_note_map = {
            "frame": "定义画布比例、留白、安全边距、标题区与主体区的版面关系，避免信息拥挤。",
            "axes": "定义坐标轴的含义、刻度表达方式与是否显示精确数值，让读者先看懂趋势。",
            "series": "定义主趋势线或主数据系列如何承接正文论点，突出方向变化而不是伪精确数字。",
            "legend": "定义图例标签、颜色映射和线型说明，避免读者把示意图误读成真实统计表。",
            "labels": "定义节点标签、短注释和必要说明应该出现在哪里，只保留帮助理解的文字。",
            "notes": "定义图下注释、数据性质说明和使用边界，明确哪些是示意趋势，哪些是正文判断。",
            "nodes": "定义图中关键节点、模块或角色卡片的命名与层级，让阅读顺序一眼可见。",
            "connectors": "定义节点之间的连接方向、主链路和必要分支，突出因果或流程关系。",
            "callouts": "定义重点提示框、风险提示或结论标签的位置，用来承接正文中的关键判断。",
            "numbering": "定义编号顺序和阅读路径，保证读者按既定顺序理解图中的结构。",
        }
        lines = [
            f"# {image_id or node.node_id} 组件 {component_name} 设计说明",
            "",
            "## 基本信息",
            f"- **component_id**：`{node.node_id}`",
            f"- **image_id**：`{image_id or node.component_parent or ''}`",
            f"- **图类型**：`{kind}`",
        ]
        if section_id or heading:
            section_line = f"- **目标章节**：`{section_id}` {heading}".rstrip()
            lines.append(section_line)
        if output_asset:
            lines.append(f"- **输出路径**：`{output_asset}`")
        lines.extend(
            [
                "",
                "## 组件目标",
                kind_note_map.get(kind, "本图用于承接正文核心判断，服务于读者理解。"),
                component_note_map.get(component_name, "本组件负责承接该图的局部信息表达，并保持与整图风格一致。"),
                "",
                "## 设计要求",
                f"1. 组件名称固定为 `{component_name}`，不得漂移到其他组件职责。",
                "2. 只补足读者理解这张图所需的信息，不额外引入正文没有展开的新论点。",
                "3. 文案保持短句、标签化、可视化友好，优先服务后续渲染与 QA。",
                "4. 如果正文属于示意关系，本组件也按示意图处理，不伪造精确数据来源。",
                "",
                "## 稳定性说明",
                "- 本说明由本地确定性 fallback 生成，用于覆盖模型调用抖动时的图片子组件空缺。",
                "- 图片最终渲染仍以后续 compositor 和 QA 节点的结果为准。",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    def _write_image_component_fallback(self, node: NodeConfig) -> tuple[bool, str]:
        try:
            payload = self._render_image_component_fallback(node)
        except Exception as exc:
            return False, f"image-component fallback failed: {type(exc).__name__}: {exc}"
        output_path = self._resolve_path(node.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
        return True, payload

    async def _run_agent_node_with_fallback_async(self, node: NodeConfig, model: str = "") -> tuple[bool, str]:
        self._record_node_started(node, "agent", provider_chain=self._provider_keys_for(node), requested_model=model)
        tried: list[dict[str, str]] = []
        for key in self._provider_keys_for(node):
            provider = self._provider_for_key(key)
            if provider is None:
                tried.append({"provider": key, "status": "unavailable", "detail": "missing env or init failed"})
                self._record_provider_event(
                    node,
                    "provider_attempt_skipped",
                    key,
                    "unavailable",
                    detail="missing env or init failed",
                    model=model,
                )
                continue
            ok, payload = await self._run_agent_node_async(node, provider, model=model, provider_key=key)
            if ok:
                tried.append({"provider": key, "status": "ok", "detail": "completed"})
                self._record_provider_event(
                    node,
                    "provider_attempt_completed",
                    key,
                    "completed",
                    detail="completed",
                    model=model,
                )
                self._write_provider_status(node.node_id, tried)
                return True, payload
            tried.append({"provider": key, "status": "failed", "detail": payload[:500]})
            self._record_provider_event(
                node,
                "provider_attempt_failed",
                key,
                "failed",
                detail=payload[:500],
                model=model,
            )
        if node.role == "image-component":
            self._ledger_event(
                "deterministic_fallback_started",
                node_id=node.node_id,
                status="running",
                message="image component local fallback started",
                payload=self._node_event_payload(node, fallback="image-component"),
            )
            fallback_ok, fallback_payload = self._write_image_component_fallback(node)
            if fallback_ok:
                tried.append({"provider": "deterministic-fallback", "status": "ok", "detail": "generated local component spec"})
                fallback_path = self._resolve_path(node.output_file) if node.output_file else None
                self._record_artifact_available(node, fallback_path, source_event="deterministic_fallback_completed")
                self._ledger_event(
                    "deterministic_fallback_completed",
                    node_id=node.node_id,
                    status="completed",
                    message="generated local component spec",
                    payload=self._node_event_payload(node, fallback="image-component"),
                )
                self._write_provider_status(node.node_id, tried)
                return True, fallback_payload
            self._ledger_event(
                "deterministic_fallback_failed",
                node_id=node.node_id,
                status="failed",
                message=_truncate_chars(fallback_payload, 800),
                payload=self._node_event_payload(node, fallback="image-component", reason=_truncate_chars(fallback_payload, 2000)),
            )
        self._write_provider_status(node.node_id, tried)
        details = " | ".join(f"{item['provider']}={item['status']}:{item['detail']}" for item in tried) or "no provider attempts"
        return False, f"provider chain failed for {node.node_id}: {details}"

    def _provider_for(self, node: NodeConfig) -> Any | None:
        key = (node.provider or "auto").lower()
        if key not in self._provider_cache:
            self._provider_cache[key] = create_provider(key)
        return self._provider_cache[key]

    def _run_agent_node_instruction(self, node: NodeConfig) -> None:
        self._record_node_started(node, "instruction")
        micro_plan = self._load_micro_plan(node)
        if micro_plan:
            self._remember_micro_plan_state(node, micro_plan, "instruction")
            self._append_execution_log(node, micro_plan, "instruction")
        payload = {
            "type": "INSTRUCTION",
            "project_id": self.project_id,
            "topic_id": self.topic_id,
            "title": self.title,
            "node_id": node.node_id,
            "role": node.role,
            "temperature": node.temperature,
            "skill_file": str(node.skill_file),
            "input_files": node.input_files,
            "output_file": node.output_file,
            "schema_check_id": node.schema_check_id,
            "task_prefix": node.task_prefix,
            "parallel": node.parallel,
            "provider": node.provider,
            "model_override": node.model_override,
            "package_type": node.package_type,
            "package_score": node.package_score,
            "package_order": node.package_order,
            "risk_tier": node.risk_tier,
            "section_group": node.section_group,
            "component_parent": node.component_parent,
            "micro_plan": micro_plan,
            "allowed_inputs": micro_plan.get("allowed_inputs", node.allowed_inputs),
        }
        self._ledger_event(
            "node_instruction_ready",
            node_id=node.node_id,
            status="waiting_operator",
            message="manual agent instruction emitted",
            payload=self._node_event_payload(node, micro_plan=micro_plan),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    def print_plan(self) -> None:
        print("=" * 80)
        print(f"Article workflow: {self.project_id}")
        if self._provider_mode() == "single":
            print(
                f"Provider mode: single | effective provider: {self._single_provider_key()} | "
                f"effective model: {self._single_provider_model(None) or '(provider default)'}"
            )
        else:
            print("Provider mode: role-routed")
        for idx, node in enumerate(self.nodes, start=1):
            extras = []
            if node.parallel:
                extras.append("parallel")
            if node.package_type:
                extras.append(node.package_type)
            if node.section_group:
                extras.append(f"section={node.section_group}")
            if node.package_score:
                extras.append(f"score={node.package_score:.1f}")
            extra_text = f" [{' '.join(extras)}]" if extras else ""
            print(
                f"{idx:02d}. {node.node_id:<30} {node.role:<16} "
                f"T={node.temperature:.2f} {node.node_type:<14} -> {node.output_file}{extra_text}"
            )
        print("=" * 80)

    def status(self) -> None:
        print(json.dumps(self.load_state(), ensure_ascii=False, indent=2))

    def preflight(self) -> None:
        if self._single_provider_key() == "codex":
            payload = {
                "checked_at": datetime.now().isoformat(),
                "provider_mode": self._provider_mode(),
                "effective_single_provider": "codex",
                "effective_single_model": self._single_provider_model(None),
                "providers": [
                    {
                        "requested_provider": "codex",
                        "chain": [
                            {
                                "provider": "codex",
                                "status": "handoff",
                                "detail": "Codex desktop subscription mode: API calls disabled; agent nodes emit CODEX_NODE_TASK packets.",
                            }
                        ],
                    }
                ],
            }
            self.provider_status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        async def _probe() -> None:
            requested = (
                [self._single_provider_key()]
                if self._provider_mode() == "single"
                else sorted({(node.provider or "auto").lower() for node in self.nodes if node.node_type == "agent"})
            )
            report: list[dict[str, Any]] = []
            for key in requested:
                chain_results: list[dict[str, str]] = []
                for candidate in self._provider_keys_for(NodeConfig("", "", Path(), 0.0, "", "none", provider=key)):
                    provider = self._provider_for_key(candidate)
                    if provider is None:
                        chain_results.append({"provider": candidate, "status": "unavailable", "detail": "missing env or init failed"})
                        continue
                    try:
                        reply = await provider.create_message(
                            model=self._single_provider_model(provider)
                            if self._provider_mode() == "single"
                            else getattr(provider, "default_model", ""),
                            max_tokens=8,
                            temperature=0.0,
                            system="You are a provider health check. Reply with ok.",
                            user_content="ok",
                        )
                        preview = (reply or "").strip().replace("\n", " ")
                        chain_results.append({"provider": candidate, "status": "ok", "detail": preview[:80] or "ok"})
                    except Exception as exc:
                        last_detail = f"{type(exc).__name__}: {exc}"[:240]
                        chain_results.append({"provider": candidate, "status": "failed", "detail": last_detail})
                    if chain_results and chain_results[-1]["status"].startswith("ok"):
                        break
                report.append({"requested_provider": key, "chain": chain_results})
            payload = {
                "checked_at": datetime.now().isoformat(),
                "provider_mode": self._provider_mode(),
                "effective_single_provider": self._single_provider_key() if self._provider_mode() == "single" else "",
                "effective_single_model": self._single_provider_model(None) if self._provider_mode() == "single" else "",
                "providers": report,
            }
            self.provider_status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(payload, ensure_ascii=False, indent=2))

        asyncio.run(_probe())

    def run(self, dry_run: bool = False) -> None:
        if dry_run:
            self.print_plan()
            return
        self._ledger_event(
            "run_started",
            status="running",
            message="step run started",
            payload={"mode": "step", "project_id": self.project_id, "topic_id": self.topic_id},
        )
        while True:
            state = self.load_state()
            ready = self._ready_nodes(state)
            if not ready:
                self._mark_workflow_completed()
                print("[DONE] all nodes completed")
                return
            node = ready[0]
            if self._stop_for_retry_limit(state, node):
                return
            if node.node_type == "human-approval":
                if self._is_node_approved(state, node):
                    approval_key = self._approval_key_for_node(node)
                    approval_payload = state.get("approvals", {}).get(approval_key, {})
                    self.mark_done(node.node_id, json.dumps(approval_payload, ensure_ascii=False, indent=2))
                    continue
                state["status"] = "waiting-human-approval"
                self.save_state(state)
                approval_payload = self._human_approval_payload(node)
                self._ledger_event("human_gate_waiting", node_id=node.node_id, status="waiting_human", payload=approval_payload)
                print(json.dumps(approval_payload, ensure_ascii=False, indent=2))
                return
            if node.node_type == "script":
                if self._run_script_node(node):
                    continue
                return
            if self._single_provider_key() == "codex":
                self._prepare_codex_node(node)
                return
            self._run_agent_node_instruction(node)
            return

    def run_autonomous(self, model: str = "") -> None:
        self._ledger_event(
            "run_started",
            status="running",
            message="autonomous run started",
            payload={"mode": "autonomous", "project_id": self.project_id, "topic_id": self.topic_id, "model": model},
        )
        async def _runner() -> None:
            while True:
                state = self.load_state()
                ready = self._ready_nodes(state)
                if not ready:
                    self._mark_workflow_completed()
                    print("[DONE] all nodes completed")
                    return

                parallel_nodes = self._select_parallel_nodes(
                    [node for node in ready if node.parallel and node.node_type == "agent"]
                )
                script_nodes = [node for node in ready if node.node_type == "script"]
                single = ready[0]

                if script_nodes:
                    script_node = script_nodes[0]
                    if self._stop_for_retry_limit(state, script_node):
                        return
                    if not self._run_script_node(script_node):
                        return
                    continue
                if self._stop_for_retry_limit(state, single):
                    return
                if single.node_type == "human-approval":
                    if self._is_node_approved(state, single):
                        approval_key = self._approval_key_for_node(single)
                        approval_payload = state.get("approvals", {}).get(approval_key, {})
                        self.mark_done(single.node_id, json.dumps(approval_payload, ensure_ascii=False, indent=2))
                        continue
                    state["status"] = "waiting-human-approval"
                    self.save_state(state)
                    approval_payload = self._human_approval_payload(single)
                    self._ledger_event("human_gate_waiting", node_id=single.node_id, status="waiting_human", payload=approval_payload)
                    print(json.dumps(approval_payload, ensure_ascii=False, indent=2))
                    return

                if self._single_provider_key() == "codex":
                    if parallel_nodes:
                        for node in parallel_nodes:
                            if self._stop_for_retry_limit(state, node):
                                return
                        self._prepare_codex_nodes(parallel_nodes)
                    else:
                        self._prepare_codex_node(single)
                    return

                if parallel_nodes:
                    for node in parallel_nodes:
                        if self._stop_for_retry_limit(state, node):
                            return
                    results = await asyncio.gather(
                        *[
                            self._run_agent_node_with_fallback_async(node, model=model)
                            for node in parallel_nodes
                        ],
                        return_exceptions=True,
                    )
                    for node, result in zip(parallel_nodes, results):
                        if isinstance(result, Exception):
                            self.mark_failed(node.node_id, str(result))
                            return
                        ok, payload = result
                        if ok:
                            self.mark_done(node.node_id, payload)
                        else:
                            self.mark_failed(node.node_id, payload)
                            return
                    continue

                ok, payload = await self._run_agent_node_with_fallback_async(single, model=model)
                if ok:
                    self.mark_done(single.node_id, payload)
                    continue
                self.mark_failed(single.node_id, payload)
                return

        asyncio.run(_runner())

    def mark_done(self, node_id: str, content: str = "") -> None:
        state = self.load_state()
        if node_id not in state["completed_nodes"]:
            state["completed_nodes"].append(node_id)
        if node_id in state["failed_nodes"]:
            state["failed_nodes"].remove(node_id)
        node = self._node_map().get(node_id)
        if node and node.section_group:
            section_status = state.setdefault("section_status", {})
            existing = section_status.get(node.section_group, {})
            section_status[node.section_group] = {
                **existing,
                "last_node": node.node_id,
                "status": "completed" if node.node_id.startswith("section-complete-") else "running",
                "updated_at": datetime.now().isoformat(),
            }
        state["history"].append({"time": datetime.now().isoformat(), "node_id": node_id, "status": "completed"})
        self.save_state(state)
        review_path = self.project_dir / "HUMAN-REVIEW.md"
        if review_path.exists():
            review_path.unlink(missing_ok=True)
        if node:
            micro_plan = self._load_micro_plan(node)
            if micro_plan:
                self._remember_micro_plan_state(node, micro_plan, "completed")
                self._append_execution_log(node, micro_plan, "completed")
        self._journal(node_id, "completed", content[:400])
        completion_payload = self._node_event_payload(node) if node else {"node_id": node_id}
        self._ledger_event("node_completed", node_id=node_id, status="completed", message=content[:400], payload=completion_payload)
        print(f"[OK] {node_id}")

    def mark_failed(self, node_id: str, reason: str) -> None:
        state = self.load_state()
        retry_counts = state.setdefault("retry_counts", {})
        retry_counts[node_id] = retry_counts.get(node_id, 0) + 1
        node = self._node_map()[node_id]
        failure_context: dict[str, Any] = {
            "node_id": node_id,
            "retry": retry_counts[node_id],
            "reason": reason[:800],
            "node": self._node_event_payload(node),
        }
        output_path = self._resolve_path(node.output_file) if node.output_file else None
        if output_path and output_path.exists() and output_path.suffix.lower() == ".json":
            parsed_output = _read_json(output_path, {})
            if isinstance(parsed_output, dict):
                failure_context["output_summary"] = {
                    "pass": parsed_output.get("pass"),
                    "consensus": parsed_output.get("consensus", ""),
                    "rollback_target": parsed_output.get("rollback_target", ""),
                    "rollback_targets": parsed_output.get("rollback_targets", []),
                    "summary": parsed_output.get("summary", ""),
                }
        state["history"].append(
            {"time": datetime.now().isoformat(), "node_id": node_id, "status": "failed", "reason": reason, "failure_context": failure_context}
        )
        revision_script = self.skill_root / "scripts" / "build_revision_micro_plan.py"
        if node.micro_plan_id and revision_script.exists():
            package_id = ""
            package_match = re.search(r"(package-\d+)", node.node_id)
            if package_match:
                package_id = package_match.group(1)
            result = subprocess.run(
                [
                    sys.executable,
                    str(revision_script),
                    "--topic-id",
                    self.topic_id,
                    "--node-id",
                    node.node_id,
                    "--reason",
                    reason[:800],
                    "--package-id",
                    package_id,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self.project_root),
            )
            revision_path = (result.stdout.strip() or result.stderr.strip()).strip()
            if revision_path:
                state.setdefault("revision_chain", []).append(
                    {
                        "node_id": node.node_id,
                        "micro_plan_id": node.micro_plan_id,
                        "revision_plan": revision_path,
                        "reason": reason[:400],
                        "retry": retry_counts[node_id],
                        "rollback_target": failure_context.get("output_summary", {}).get("rollback_target", ""),
                    }
                )
        if node_id not in state["failed_nodes"]:
            state["failed_nodes"].append(node_id)
        self.save_state(state)
        micro_plan = self._load_micro_plan(node)
        if micro_plan:
            self._remember_micro_plan_state(node, micro_plan, "failed")
            self._append_execution_log(node, micro_plan, "failed")
        self._journal(node_id, "failed", reason[:400])
        self._ledger_event("node_failed", node_id=node_id, status="failed", message=reason[:800], payload=failure_context)
        print(f"[FAILED] {node_id}: {reason}")

    def approve(self, approver: str, publish_url: str = "", approval_key: str = "") -> None:
        state = self.load_state()
        resolved_key = (approval_key or "").strip() or "final-article-approval"
        approval_payload = {
            "approver": approver,
            "approved_at": datetime.now().isoformat(),
            "publish_url": publish_url,
            "approval_key": resolved_key,
        }
        approvals = state.setdefault("approvals", {})
        approvals[resolved_key] = {
            **approval_payload,
            "approved": True,
        }
        if state["status"] == "waiting-human-approval":
            state["status"] = "running"
        self.save_state(state)
        self._ledger_event("human_gate_approved", node_id=resolved_key, status="approved", payload=approval_payload)
        self._journal("human-approval-01", "approved", f"{resolved_key}: {approver}")
        print(f"[APPROVED] {self.project_id} | {resolved_key} | {approver}")


def _guard_workflow_script_path(script_path: str) -> Path:
    path = Path(script_path).resolve()
    if not path.exists():
        raise SystemExit(f"workflow script not found: {path}")
    if path.suffix.lower() != ".py":
        raise SystemExit(f"workflow script must be a Python file: {path}")
    if path.name.endswith("_short.py"):
        raise SystemExit(
            "refusing deprecated short workflow script. "
            "Use init_workflow.py -> compile_expanded_workflow.py instead."
        )
    parent_names = {part.lower() for part in path.parts}
    blocked_dirs = {name.lower() for name in DISABLED_OUTPUT_DIR_NAMES}
    blocked_hit = parent_names & blocked_dirs
    if blocked_hit:
        raise SystemExit(f"refusing workflow script under disabled/archive directory: {path}")
    stem = path.stem
    if stem.startswith("run_"):
        stem = stem[4:]
    if stem.endswith("_expanded"):
        stem = stem[: -len("_expanded")]
    for prefix in DISABLED_TOPIC_PREFIXES:
        if stem == prefix or stem.startswith(prefix + "-"):
            raise SystemExit(f"refusing known-bad or validation workflow topic: {stem}")
    return path


def load_runner(script_path: str, allow_legacy_script: bool = False) -> WorkflowRunner:
    guarded_path = _guard_workflow_script_path(script_path)
    script_text = guarded_path.read_text(encoding="utf-8")
    if "ARTICLE_DIRECTOR_WORKFLOW_VERSION" not in script_text and not allow_legacy_script:
        raise SystemExit(
            "refusing legacy generated workflow without ARTICLE_DIRECTOR_WORKFLOW_VERSION. "
            "Reinitialize from init_workflow.py, or pass --allow-legacy-script only for historical inspection."
        )
    spec = importlib.util.spec_from_file_location("article_workflow", guarded_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    workflow_version = str(getattr(module, "ARTICLE_DIRECTOR_WORKFLOW_VERSION", "") or "")
    if not workflow_version and not allow_legacy_script:
        raise SystemExit(
            "refusing legacy generated workflow without ARTICLE_DIRECTOR_WORKFLOW_VERSION. "
            "Reinitialize from init_workflow.py, or pass --allow-legacy-script only for historical inspection."
        )
    namespace = vars(module)
    nodes = [
        NodeConfig(
            node_id=item["node_id"],
            role=item["role"],
            skill_file=Path(str(_materialize_module_value(item.get("skill_file", ""), namespace))),
            temperature=item.get("temperature", 0.0),
            output_file=str(_materialize_module_value(item.get("output_file", ""), namespace)),
            schema_check_id=item.get("schema_check_id", "none"),
            input_files=[
                str(_materialize_module_value(raw_path, namespace))
                for raw_path in _as_list(_materialize_module_value(item.get("input_files", []), namespace))
            ],
            micro_plan=_materialize_module_value(item.get("micro_plan", {}), namespace) or {},
            allowed_inputs=_materialize_module_value(item.get("allowed_inputs", []), namespace) or [],
            micro_plan_id=str(_materialize_module_value(item.get("micro_plan_id", ""), namespace) or ""),
            micro_plan_file=str(_materialize_module_value(item.get("micro_plan_file", ""), namespace) or ""),
            micro_plan_version=str(_materialize_module_value(item.get("micro_plan_version", ""), namespace) or ""),
            micro_plan_mode=str(_materialize_module_value(item.get("micro_plan_mode", ""), namespace) or ""),
            revision_source=str(_materialize_module_value(item.get("revision_source", ""), namespace) or ""),
            verification_profile=str(_materialize_module_value(item.get("verification_profile", ""), namespace) or ""),
            max_input_tokens=item.get("max_input_tokens", 2000),
            max_output_tokens=item.get("max_output_tokens", 4096),
            max_retries=item.get("max_retries", 2),
            memory_write=item.get("memory_write", {}),
            estimated_tokens=item.get("estimated_tokens", {}),
            task_prefix=item.get("task_prefix", ""),
            node_type=item.get("node_type", "agent"),
            parallel=item.get("parallel", False),
            provider=item.get("provider", "auto"),
            model_override=item.get("model_override", ""),
            package_type=item.get("package_type", ""),
            package_score=float(item.get("package_score", 0.0) or 0.0),
            package_order=int(item.get("package_order", 0) or 0),
            risk_tier=item.get("risk_tier", "medium"),
            section_group=str(item.get("section_group", "") or ""),
            component_parent=item.get("component_parent", ""),
            command=item.get("command", []),
            env=item.get("env", {}),
        )
        for item in module.NODE_DEFS
    ]
    edges = [EdgeConfig(edge["from_node"], edge["to_node"]) for edge in module.EDGE_DEFS]
    return WorkflowRunner(
        project_id=module.PROJECT_ID,
        topic_id=module.TOPIC_ID,
        title=module.TITLE,
        brief=getattr(module, "BRIEF", ""),
        strategy=getattr(module, "STRATEGY", "knowledge-explainer"),
        skill_root=module.SKILL_ROOT,
        project_root=module.PROJECT_ROOT,
        nodes=nodes,
        edges=edges,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Article Director workflow runner")
    parser.add_argument("--script", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--mark-done", default="")
    parser.add_argument("--submit-codex-node", default="")
    parser.add_argument("--content-file", default="")
    parser.add_argument("--mark-failed", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--approver", default="用户")
    parser.add_argument("--publish-url", default="")
    parser.add_argument("--approval-key", default="")
    parser.add_argument("--autonomous", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--model", default="")
    parser.add_argument("--allow-legacy-script", action="store_true")
    args = parser.parse_args()

    runner = load_runner(args.script, allow_legacy_script=args.allow_legacy_script)
    if args.dry_run:
        runner.run(dry_run=True)
    elif args.status:
        runner.status()
    elif args.mark_done:
        content = ""
        if args.content_file:
            content = Path(args.content_file).read_text(encoding="utf-8")
        runner.mark_done(args.mark_done, content)
    elif args.submit_codex_node:
        if not args.content_file:
            raise SystemExit("--submit-codex-node requires --content-file")
        runner.submit_codex_node(args.submit_codex_node, args.content_file)
    elif args.mark_failed:
        runner.mark_failed(args.mark_failed, args.reason)
    elif args.approve:
        runner.approve(args.approver, args.publish_url, args.approval_key)
    elif args.preflight:
        runner.preflight()
    elif args.autonomous:
        runner.run_autonomous(model=args.model)
    else:
        runner.run()


if __name__ == "__main__":
    main()
