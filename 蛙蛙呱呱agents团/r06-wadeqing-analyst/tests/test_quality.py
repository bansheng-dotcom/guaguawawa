import pytest
import os
import pandas as pd
from skills import s02_quality

def test_quality_audit_schema():
    # 测试清洗模块输出结构是否符合契约
    # 使用 s02_quality 模块的 _audit 函数（虽然是私有，但在测试中可访问）
    # 或者通过 run() 函数模拟输入
    
    # 模拟数据
    rows = [{'a': '1', 'b': '1'}, {'a': '2', 'b': '2'}, {'a': '', 'b': '3'}]
    
    # 注入配置 mock (通过 _common.load_thresholds)
    # 鉴于我们不想修改 _common，这里直接验证 run 函数的返回结构
    
    # 这里演示调用 audit 逻辑
    result = s02_quality._audit(rows, pk=None, date_col=None)
    
    assert 'overall_score' in result
    assert 'findings' in result
    assert result['rows'] == 3
    assert result['missing']['a'] > 0
