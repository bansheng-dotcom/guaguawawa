# -*- coding: utf-8 -*-
"""pytest 夹具：把角色目录与仓库根注入 sys.path，任何 cwd 下都能收集。"""
import os
import sys

ROLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.dirname(ROLE_DIR)
REPO = os.path.dirname(AGENTS)
for _p in (ROLE_DIR, AGENTS, REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def role_dir() -> str:
    return ROLE_DIR


@pytest.fixture(scope="session")
def agents_root() -> str:
    return AGENTS
