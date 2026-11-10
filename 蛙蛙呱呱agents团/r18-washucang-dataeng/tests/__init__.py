# -*- coding: utf-8 -*-
"""R18 测试包标记（SOP §5.5）。

必须显式存在：否则 `python -m unittest tests.test_xxx` 在异构 cwd 下可能优先
索引到 site-packages 中的同名包，产生 AttributeError / ModuleNotFoundError。
"""
