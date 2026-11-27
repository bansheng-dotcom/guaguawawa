# -*- coding: utf-8 -*-
"""R09 工程链（T7）：adr → api → feature → testing → debug → release →
security → performance → incident → review 的 10 段可审计链路。

用法（Python）：
    from eng_chain import runner
    manifest = runner.run("eng_chain/fixtures/tiny-notes.json", out_dir)

各段也可单独调用：adr / api / feature / testing / debug / release /
security / performance / incident / review。
"""
from . import (adr, api, common, debug, feature, incident, performance,
               release, review, runner, security, testing)

__all__ = ["adr", "api", "feature", "testing", "debug", "release",
           "security", "performance", "incident", "review", "runner", "common"]
