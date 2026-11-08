# scripts/auto_retrospective.py
import json
import os
import datetime
from pathlib import Path

def generate_retrospective(task_id: str, error_context: str, project_name: str = "global"):
    '''
    自动化复盘机制 (Auto-Retrospective) MVP。
    当 R04 或流程报错时触发，将失败上下文转换为经验库候选记录。
    '''
    base_dir = Path("D:/一人公司/补充技能/product-manager/experience")
    inbox_dir = base_dir / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    filename = f"{project_name}-correction-{timestamp}.md"
    
    content = f'''---
experience_id: exp-{timestamp}-auto-correction
title: 自动复盘：{task_id} 错误规避
scope: project
project: {project_name}
experience_type: correction
trigger_signals:
  - 数据口径报错
  - R04 门禁失败
validation:
  status: candidate
  confidence: medium
  last_verified: {datetime.datetime.now().strftime("%Y-%m-%d")}
keywords:
  - 自动沉淀
  - 故障规避
---

## 经验结论
系统在执行任务 {task_id} 时遇到阻断。在后续处理同类逻辑时，请优先规避此模式。

## 为什么成立 (失败上下文)
`	ext
{error_context}
`

## 下次怎么用
执行前预检查上述模式，若发现重合，需提前请求人工介入或调用补充校验工具。
'''
    
    out_path = inbox_dir / filename
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"自动复盘卡片已生成: {out_path}")
    
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        generate_retrospective("task-demo-999", sys.argv[1])
    else:
        generate_retrospective("task-demo-999", "[R04 审查失败] 数据口径不一致，缺少时间窗约束。")
