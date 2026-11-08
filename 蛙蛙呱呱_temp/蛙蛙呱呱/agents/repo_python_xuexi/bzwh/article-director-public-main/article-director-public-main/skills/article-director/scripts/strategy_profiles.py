import json
from functools import lru_cache
from pathlib import Path


DEFAULT_STRATEGY = "knowledge-explainer"
WORKFLOW_FAMILY = "article-director-fixed-graph"
WORKFLOW_FAMILY_VERSION = "2026-05-23.v1"
STRATEGY_DIR = Path(__file__).resolve().parents[1] / "references" / "strategies"
DISALLOWED_STRATEGY_KEYS = {
    "nodes",
    "edges",
    "graph",
    "workflow_nodes",
    "workflow_edges",
    "providers",
    "models",
    "node_graph",
    "execution_graph",
}
REQUIRED_PROMPT_KEYS = {
    "topic_architect_plan_suffix",
    "topic_architect_exec_suffix",
    "writer_contract_suffix",
    "primer_contract_suffix",
    "concept_bridge_contract_suffix",
    "deep_dive_contract_suffix",
    "structure_contract_suffix",
    "smoother_contract_suffix",
    "review_contract_suffix",
    "appendix_contract_suffix",
}


def _deep_copy(payload: dict) -> dict:
    return json.loads(json.dumps(payload, ensure_ascii=False))


def _contract_path(strategy_name: str) -> Path:
    return STRATEGY_DIR / f"{strategy_name}.json"


def _validate_strategy_contract(payload: dict, source: Path) -> None:
    missing = [
        key
        for key in (
            "strategy",
            "display_name",
            "version",
            "primary_goal",
            "section_intent",
            "concept_policy",
            "step_boundary_rules",
            "required_step_fields",
            "auto_infer_signals",
            "manifest_rules",
            "prompt_contracts",
        )
        if key not in payload
    ]
    if missing:
        raise ValueError(f"strategy contract missing keys in {source}: {missing}")

    illegal = sorted(DISALLOWED_STRATEGY_KEYS.intersection(payload.keys()))
    if illegal:
        raise ValueError(f"strategy contract may not define workflow structure in {source}: {illegal}")

    prompt_contracts = payload.get("prompt_contracts", {})
    missing_prompt_keys = sorted(REQUIRED_PROMPT_KEYS.difference(prompt_contracts.keys()))
    if missing_prompt_keys:
        raise ValueError(f"strategy contract missing prompt contracts in {source}: {missing_prompt_keys}")

    auto_infer = payload.get("auto_infer_signals", {})
    for key in ("explicit_aliases", "title_keywords", "brief_keywords"):
        if not isinstance(auto_infer.get(key, []), list):
            raise ValueError(f"strategy contract field auto_infer_signals.{key} must be a list in {source}")

    manifest_rules = payload.get("manifest_rules", {})
    if not isinstance(manifest_rules.get("prefer_procedural_steps", False), bool):
        raise ValueError(f"strategy contract field manifest_rules.prefer_procedural_steps must be bool in {source}")
    for index, rule in enumerate(manifest_rules.get("presentation_rules", []), start=1):
        if not isinstance(rule, dict):
            raise ValueError(f"strategy contract manifest_rules.presentation_rules[{index}] must be object in {source}")
        if not isinstance(rule.get("heading_keywords", []), list):
            raise ValueError(
                f"strategy contract manifest_rules.presentation_rules[{index}].heading_keywords must be list in {source}"
            )
        if not isinstance(rule.get("mode", ""), str):
            raise ValueError(f"strategy contract manifest_rules.presentation_rules[{index}].mode must be string in {source}")


def _flatten_prompt_contracts(payload: dict, source: Path) -> dict:
    prompt_contracts = payload["prompt_contracts"]
    profile = _deep_copy(payload)
    profile["contract_path"] = str(source)
    for key in REQUIRED_PROMPT_KEYS:
        profile[key] = prompt_contracts.get(key, "").strip()
    return profile


@lru_cache(maxsize=1)
def load_strategy_contracts() -> dict[str, dict]:
    contracts: dict[str, dict] = {}
    for path in sorted(STRATEGY_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        _validate_strategy_contract(payload, path)
        contracts[payload["strategy"]] = _flatten_prompt_contracts(payload, path)
    if DEFAULT_STRATEGY not in contracts:
        raise ValueError(f"default strategy contract not found: {DEFAULT_STRATEGY}")
    return contracts


def normalize_strategy(strategy_name: str | None) -> str:
    contracts = load_strategy_contracts()
    if not strategy_name:
        return DEFAULT_STRATEGY
    normalized = str(strategy_name).strip().lower()
    if normalized in contracts:
        return normalized
    for key, payload in contracts.items():
        aliases = [item.strip().lower() for item in payload.get("auto_infer_signals", {}).get("explicit_aliases", [])]
        if normalized in aliases:
            return key
    return DEFAULT_STRATEGY


def infer_strategy(title: str, brief: str = "", explicit_strategy: str | None = None) -> str:
    if explicit_strategy and str(explicit_strategy).strip().lower() not in {"", "auto"}:
        return normalize_strategy(explicit_strategy)

    haystack = f"{title}\n{brief}".lower()
    contracts = load_strategy_contracts()

    scored: list[tuple[int, str]] = []
    for strategy_name, payload in contracts.items():
        infer_config = payload.get("auto_infer_signals", {})
        score = 0
        for keyword in infer_config.get("title_keywords", []):
            if keyword and keyword.lower() in str(title).lower():
                score += 3
        for keyword in infer_config.get("brief_keywords", []):
            if keyword and keyword.lower() in haystack:
                score += 1
        scored.append((score, strategy_name))

    scored.sort(reverse=True)
    best_score, best_strategy = scored[0] if scored else (0, DEFAULT_STRATEGY)
    return best_strategy if best_score > 0 else DEFAULT_STRATEGY


def get_strategy_profile(strategy_name: str | None = None) -> dict:
    contracts = load_strategy_contracts()
    key = normalize_strategy(strategy_name)
    return _deep_copy(contracts.get(key, contracts[DEFAULT_STRATEGY]))


def build_workflow_profile(strategy_name: str, title: str, brief: str = "") -> dict:
    profile = get_strategy_profile(strategy_name)
    return {
        "strategy": profile["strategy"],
        "strategy_display_name": profile["display_name"],
        "strategy_version": profile["version"],
        "strategy_contract_path": profile["contract_path"],
        "workflow_family": WORKFLOW_FAMILY,
        "workflow_family_version": WORKFLOW_FAMILY_VERSION,
        "title": title,
        "brief": brief,
        "content_contract": {
            "primary_goal": profile["primary_goal"],
            "section_intent": profile["section_intent"],
            "concept_policy": profile["concept_policy"],
            "step_boundary_rules": profile["step_boundary_rules"],
            "required_step_fields": profile["required_step_fields"],
            "manifest_rules": profile["manifest_rules"],
        },
        "prompt_contracts": profile["prompt_contracts"],
    }
