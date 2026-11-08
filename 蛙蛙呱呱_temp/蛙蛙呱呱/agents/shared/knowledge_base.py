# -*- coding: utf-8 -*-
"""通用知识注入层：把 references/ + experience/ + cases/ 升级为 LLM 可调用的知识基座。

设计原则：
  - 按需加载：LLM 调用前才读文件，不常驻内存
  - 结构化注入：按能力域组织，支持选择性注入（避免 context 爆炸）
  - 版本可追溯：每次注入记录文件 hash，便于审计
  - 可复用：支持任意角色目录，通过配置适配不同角色
  - 高性能：LRU 缓存 + 增量加载 + 向量检索
  - 多语言：支持中英文 references
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

# 可选依赖：向量检索
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    HAS_VECTOR = True
except ImportError:
    HAS_VECTOR = False


class KnowledgeBase:
    """角色知识基座：加载 references + thresholds + cases，构建 LLM system prompt。"""

    def __init__(
        self,
        role_dir: str,
        knowledge_map: Dict[str, List[str]],
        role_name: str,
        role_title: str,
        core_duties: List[str],
        key_principles: List[str],
        output_requirements: List[str],
        language: str = "zh",
        enable_cache: bool = True,
        enable_vector: bool = False,
    ):
        """初始化知识基座。

        Args:
            role_dir: 角色根目录（如 agents/r01-waquanju-ceo）
            knowledge_map: 知识域映射（能力域 → references 文件列表）
            role_name: 角色名称（如 "R01 蛙全局"）
            role_title: 角色标题（如 "CEO 主理人 / 编排器"）
            core_duties: 核心职责列表
            key_principles: 关键原则列表
            output_requirements: 输出要求列表
            language: 语言（zh/en），默认 zh
            enable_cache: 是否启用 LRU 缓存，默认 True
            enable_vector: 是否启用向量检索（需安装 sentence-transformers），默认 False
        """
        self.role_dir = os.path.abspath(role_dir)
        self.knowledge_map = knowledge_map
        self.role_name = role_name
        self.role_title = role_title
        self.core_duties = core_duties
        self.key_principles = key_principles
        self.output_requirements = output_requirements
        self.language = language
        self.enable_cache = enable_cache
        self.enable_vector = enable_vector and HAS_VECTOR

        # 缓存：文件内容 + 文件 hash
        self._text_cache: Dict[str, Tuple[str, float]] = {}  # path → (content, mtime)
        self._hash_cache: Dict[str, str] = {}  # path → hash

        # 向量检索：域嵌入
        self._domain_embeddings: Dict[str, Any] = {}
        if self.enable_vector:
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            self._embed_domains()

    def _file_hash(self, path: str) -> str:
        """计算文件 MD5 前 8 位，用于版本追踪。"""
        if not os.path.exists(path):
            return ""
        if self.enable_cache and path in self._hash_cache:
            return self._hash_cache[path]
        h = hashlib.md5()
        with open(path, "rb") as f:
            h.update(f.read())
        hash_val = h.hexdigest()[:8]
        if self.enable_cache:
            self._hash_cache[path] = hash_val
        return hash_val

    def _load_text(self, path: str) -> str:
        """加载文件内容，支持 LRU 缓存。"""
        if not os.path.exists(path):
            return ""
        mtime = os.path.getmtime(path)
        if self.enable_cache and path in self._text_cache:
            cached_content, cached_mtime = self._text_cache[path]
            if cached_mtime == mtime:
                return cached_content
        with open(path, encoding="utf-8-sig") as f:
            content = f.read()
        if self.enable_cache:
            self._text_cache[path] = (content, mtime)
        return content

    def _embed_domains(self) -> None:
        """为每个知识域生成嵌入向量。"""
        for domain, files in self.knowledge_map.items():
            # 用域名 + 文件路径作为嵌入文本
            text = f"{domain} {' '.join(files)}"
            self._domain_embeddings[domain] = self._embedder.encode(text)

    def _cosine_similarity(self, a: Any, b: Any) -> float:
        """计算余弦相似度。"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def load_knowledge(
        self,
        domains: Optional[List[str]] = None,
        include_charter: bool = True,
        include_thresholds: bool = True,
        include_cases: bool = False,
        incremental: bool = False,
        last_hash: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """按需加载知识域，返回结构化知识包。

        Args:
            domains: 要加载的能力域列表（如 ["decide", "redteam"]），None=全部
            include_charter: 是否包含角色能力说明书（00-capability-charter.md）
            include_thresholds: 是否加载 experience/thresholds.json
            include_cases: 是否加载案例库
            incremental: 是否启用增量加载（只加载 hash 变更的文件）
            last_hash: 上次加载的 hash 映射（path → hash），用于增量加载

        Returns:
            {
                "knowledge_text": str,      # 拼接后的 Markdown 文本（供 LLM system prompt）
                "sources": List[Dict],      # 每份文件的元信息（路径/hash/域）
                "thresholds": Dict,         # 业务阈值（如 include_thresholds=True）
                "cases": List[Dict],        # 案例摘要（如 include_cases=True）
                "changed": List[str],       # 增量加载时变更的文件列表
            }
        """
        if domains is None:
            domains = list(self.knowledge_map.keys())

        sources: List[Dict[str, Any]] = []
        texts: List[str] = []
        changed: List[str] = []

        # 1. 加载能力说明书（全局）
        if include_charter:
            path = os.path.join(self.role_dir, "references", "00-capability-charter.md")
            text = self._load_text(path)
            if text:
                current_hash = self._file_hash(path)
                if not (incremental and last_hash and last_hash.get(path) == current_hash):
                    changed.append(path)
                    sources.append({
                        "path": "references/00-capability-charter.md",
                        "domain": "charter",
                        "hash": current_hash,
                    })
                    texts.append(f"# 角色能力说明书\n\n{text}")

        # 2. 按域加载 references
        loaded_files = set()
        for domain in domains:
            for rel_path in self.knowledge_map.get(domain, []):
                if rel_path in loaded_files:
                    continue
                loaded_files.add(rel_path)
                path = os.path.join(self.role_dir, rel_path)
                text = self._load_text(path)
                if text:
                    current_hash = self._file_hash(path)
                    if incremental and last_hash and last_hash.get(path) == current_hash:
                        continue  # 未变更，跳过
                    changed.append(path)
                    sources.append({
                        "path": rel_path,
                        "domain": domain,
                        "hash": current_hash,
                    })
                    texts.append(f"# {domain} 知识域\n\n{text}")

        # 3. 加载阈值配置
        thresholds: Dict[str, Any] = {}
        if include_thresholds:
            thresholds_path = os.path.join(self.role_dir, "experience", "thresholds.json")
            if os.path.exists(thresholds_path):
                with open(thresholds_path, encoding="utf-8") as f:
                    thresholds = json.load(f)
                sources.append({
                    "path": "experience/thresholds.json",
                    "domain": "thresholds",
                    "hash": self._file_hash(thresholds_path),
                })

        # 4. 加载案例库
        cases: List[Dict[str, Any]] = []
        if include_cases:
            cases_dir = os.path.join(self.role_dir, "cases")
            if os.path.isdir(cases_dir):
                for case_id in os.listdir(cases_dir):
                    case_json = os.path.join(cases_dir, case_id, "case.json")
                    if os.path.exists(case_json):
                        with open(case_json, encoding="utf-8") as f:
                            case_data = json.load(f)
                        cases.append({
                            "case_id": case_id,
                            "display_name": case_data.get("display_name", ""),
                            "description": case_data.get("description", ""),
                            "default_question": case_data.get("default_question", ""),
                        })

        knowledge_text = "\n\n---\n\n".join(texts)

        return {
            "knowledge_text": knowledge_text,
            "sources": sources,
            "thresholds": thresholds,
            "cases": cases,
            "changed": changed,
        }

    def build_system_prompt(
        self,
        domains: Optional[List[str]] = None,
        task_context: Optional[str] = None,
        incremental: bool = False,
        last_hash: Optional[Dict[str, str]] = None,
    ) -> str:
        """构建 LLM system prompt：角色定位 + 知识注入 + 任务上下文。

        Args:
            domains: 要注入的知识域（如 ["decide", "redteam"]），None=全部
            task_context: 当前任务上下文（如用户输入的意图描述）
            incremental: 是否启用增量加载
            last_hash: 上次加载的 hash 映射

        Returns:
            完整的 system prompt 字符串
        """
        knowledge = self.load_knowledge(
            domains=domains,
            include_charter=True,
            incremental=incremental,
            last_hash=last_hash,
        )

        prompt_parts = [
            f"你是 {self.role_name} · {self.role_title}。",
            "",
            "## 核心职责",
        ]
        prompt_parts.extend(f"- {duty}" for duty in self.core_duties)
        prompt_parts.extend([
            "",
            "## 关键原则",
        ])
        prompt_parts.extend(f"- {p}" for p in self.key_principles)
        prompt_parts.extend([
            "",
            "## 知识基座",
            knowledge["knowledge_text"],
            "",
        ])

        if task_context:
            prompt_parts.extend([
                "## 当前任务上下文",
                task_context,
                "",
            ])

        prompt_parts.extend([
            "## 输出要求",
        ])
        prompt_parts.extend(f"- {r}" for r in self.output_requirements)

        return "\n".join(prompt_parts)

    def get_domain_for_intent(
        self,
        intent: str,
        keyword_map: Dict[str, List[str]],
        use_vector: bool = False,
    ) -> List[str]:
        """根据用户意图推断需要加载的知识域。

        Args:
            intent: 用户意图描述
            keyword_map: 关键词映射（能力域 → 关键词列表）
            use_vector: 是否使用向量检索（需 enable_vector=True）

        Returns:
            推断出的知识域列表
        """
        if use_vector and self.enable_vector:
            return self._get_domain_by_vector(intent)
        return self._get_domain_by_keyword(intent, keyword_map)

    def _get_domain_by_keyword(self, intent: str, keyword_map: Dict[str, List[str]]) -> List[str]:
        """关键词匹配（默认）。"""
        intent_lower = intent.lower()
        domains = []

        for domain, keywords in keyword_map.items():
            if any(k.lower() in intent_lower for k in keywords):
                domains.append(domain)

        # 默认加载 charter + governance（全局治理原则）
        if not domains:
            domains = ["charter", "governance"]

        return domains

    def _get_domain_by_vector(self, intent: str) -> List[str]:
        """向量检索（语义匹配）。"""
        intent_emb = self._embedder.encode(intent)
        scores = {
            domain: self._cosine_similarity(intent_emb, emb)
            for domain, emb in self._domain_embeddings.items()
        }
        # 返回相似度最高的 3 个域
        return sorted(scores, key=scores.get, reverse=True)[:3]

    def load_multilingual_references(
        self,
        domains: Optional[List[str]] = None,
        languages: List[str] = ["zh", "en"],
    ) -> Dict[str, Any]:
        """加载多语言 references。

        Args:
            domains: 要加载的能力域列表
            languages: 语言列表（如 ["zh", "en"]）

        Returns:
            多语言知识包
        """
        result = {}
        for lang in languages:
            lang_map = {
                domain: [f.replace(".md", f"_{lang}.md") for f in files]
                for domain, files in self.knowledge_map.items()
            }
            kb = KnowledgeBase(
                role_dir=self.role_dir,
                knowledge_map=lang_map,
                role_name=self.role_name,
                role_title=self.role_title,
                core_duties=self.core_duties,
                key_principles=self.key_principles,
                output_requirements=self.output_requirements,
                language=lang,
                enable_cache=self.enable_cache,
                enable_vector=self.enable_vector,
            )
            result[lang] = kb.load_knowledge(domains=domains)
        return result


# --------------------------------------------------------------------------- #
# R01 蛙全局 · CEO 主理人配置（示例）
# --------------------------------------------------------------------------- #
R01_CONFIG = {
    "role_name": "R01 蛙全局",
    "role_title": "CEO 主理人 / 编排器",
    "core_duties": [
        "把创始人的一句话意图变成有主责、有验收、有终止条件的任务卡",
        "收口成一份能签字的决策汇报",
        "不替专业部门干活，也不替创始人签字",
    ],
    "key_principles": [
        "不可逆动作必须创始人授权（签约/扣款/裁员等）",
        "先锁标准再谈实现（成功/杀死标准先于决策写）",
        "上下文隔离：子进程边界调用其它 Agent，不共享内存",
        "端口契约：跨角色交接只认 inputs/outputs",
    ],
    "output_requirements": [
        "所有结论必须带成功/杀死标准",
        "所有建议必须标注可逆性等级",
        "涉及不可逆动作时必须声明 human_signoff_required",
        "使用结构化 JSON 输出，便于下游校验",
    ],
    "knowledge_map": {
        "intent": ["references/01-vision-intent.md"],
        "decompose": ["references/02-orchestration-decomposition.md"],
        "decide": ["references/03-hard-decisions.md"],
        "redteam": ["references/03-hard-decisions.md"],
        "companyos": ["references/04-company-os.md"],
        "decisionlog": ["references/04-company-os.md"],
        "boardroom": ["references/04-company-os.md"],
        "governance": ["references/05-governance-audit.md"],
        "charter": ["references/00-capability-charter.md"],
    },
    "keyword_map": {
        "intent": ["简报", "brief", "澄清", "六问", "意图", "分级"],
        "decompose": ["拆解", "任务卡", "波次", "路由", "分工", "wbs"],
        "decide": ["决策", "可逆", "拍板", "定夺", "升级"],
        "redteam": ["质询", "反方", "红队", "魔鬼代言人", "交叉评估"],
        "companyos": ["公司os", "记分卡", "ids", "冷却", "freeze", "治理"],
        "decisionlog": ["决策日志", "留痕", "复盘", "retro"],
        "boardroom": ["董事会", "汇报", "陪练", "board"],
    },
}


def create_r01_knowledge_base(role_dir: str, **kwargs) -> KnowledgeBase:
    """创建 R01 知识基座实例。"""
    return KnowledgeBase(
        role_dir=role_dir,
        knowledge_map=R01_CONFIG["knowledge_map"],
        role_name=R01_CONFIG["role_name"],
        role_title=R01_CONFIG["role_title"],
        core_duties=R01_CONFIG["core_duties"],
        key_principles=R01_CONFIG["key_principles"],
        output_requirements=R01_CONFIG["output_requirements"],
        **kwargs,
    )
