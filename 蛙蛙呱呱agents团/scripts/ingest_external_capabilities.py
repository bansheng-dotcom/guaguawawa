# -*- coding: utf-8 -*-
"""把 26 个外部能力（Trae 插件 + WorkBuddy 技能）的入口文档摄取进对应角色，并生成目录。"""
import json
import os
import shutil

BASE = r"D:\蛙蛙呱呱\蛙蛙呱呱agents团"
TRAE = r"C:\Users\18238\.trae-cn\plugins\trae-remote-official"
WB = r"C:\Users\18238\.workbuddy\skills"

ROLES = {
    "r01": "r01-waquanju-ceo", "r02": "r02-wapaibu-coo", "r03": "r03-washouxian-cfo",
    "r04": "r04-watiaoci-reviewer", "r05": "r05-washenyuan-research",
    "r06": "r06-wadeqing-analyst", "r07": "r07-wademing-pm", "r08": "r08-wajiancheng-mvp",
    "r09": "r09-wawenma-engineer", "r10": "r10-wachengmei-design",
    "r11": "r11-wadianti-copy", "r12": "r12-wayingliu-growth",
    "r13": "r13-wakecheng-csm", "r14": "r14-wajiaoyi-commerce",
    "r15": "r15-wagongying-erp", "r16": "r16-warenshi-hr",
    "r17": "r17-wazhiwang-automation", "r18": "r18-washucang-dataeng",
    "r19": "r19-wazhimo-ml", "r20": "r20-washouzhi-sre",
}

# id, title, kind, owner, consumers, triggers, requires
CAPS = [
    ("omnichannel-commerce-assistant", "全渠道电商经营诊断", "skill", "r14", ["r12", "r02"],
     ["电商诊断", "店铺经营", "全渠道", "选品", "转化"], "files"),
    ("rednote-post", "小红书笔记图文爆款", "skill", "r11", ["r10", "r12"],
     ["小红书", "笔记", "爆款", "封面", "种草"], "files"),
    ("xhs-content-skills", "小红书内容流水线（9 技能）", "multi", "r11", ["r10", "r12", "r03"],
     ["标题", "选题", "合规", "打分", "发布"], "files"),
    ("ppt-generator", "单文件 HTML 幻灯片", "skill", "r08", ["r10", "r02"],
     ["PPT", "幻灯片", "演示文稿", "deck", "汇报"], "files"),
    ("meitu-local-mcp", "美图本地 MCP（图像/视频 30 工具）", "mcp", "r10", ["r14", "r12", "r11"],
     ["抠图", "修图", "商品图", "换脸", "证件照", "图片编辑"], "mcp:node"),
    ("marketing-toolkit", "营销全链路工具箱", "skill", "r12", ["r11", "r10"],
     ["营销活动", "文案", "投放", "SEO", "转化"], "files"),
    ("volcengine-pro-dataset", "火山专业数据集 MCP", "mcp", "r05", ["r06", "r19"],
     ["学术文献", "企业信息", "工商", "专利", "宏观经济"], "mcp:http"),
    ("agent-earth", "AgentEarth 1500+ API MCP", "mcp", "r05", ["r06", "r12", "r14", "r19"],
     ["全网检索", "电商数据", "金融", "爬取", "新闻"], "mcp:http"),
    ("tashan-research-skills", "学术研究与写作（20 技能）", "multi", "r05", ["r11", "r04"],
     ["论文", "综述", "实验设计", "审稿", "投稿"], "files"),
    ("build-web-data-visualization", "Web 数据可视化（18 技能）", "multi", "r06", ["r08", "r09", "r10"],
     ["ECharts", "D3", "大屏", "图表", "可视化"], "files"),
    ("rapid-prototype-craft", "高保真可交互原型", "skill", "r08", ["r10", "r09"],
     ["原型", "高保真", "HTML 原型", "交互"], "files"),
    ("data-processing", "数据处理与可视化", "skill", "r06", ["r18", "r02"],
     ["CSV", "Excel", "清洗", "透视", "合并"], "files"),
    ("miniapp-builder", "Taro 小程序构建 MCP", "mcp", "r09", ["r08", "r17"],
     ["小程序", "微信小程序", "抖音小程序", "Taro", "二维码"], "mcp:node"),
    ("industry-panorama-research", "行业全景研究", "skill", "r05", ["r01", "r12"],
     ["行业研究", "市场规模", "竞争格局", "商业模式"], "files"),
    ("analyze-procurement", "采购与供应链分析", "skill", "r15", ["r14", "r03"],
     ["采购", "供应商", "RFx", "TCO", "补货", "物流"], "files"),
    ("brand-guardian", "品牌一致性守卫", "skill", "r10", ["r04", "r11", "r12"],
     ["品牌一致性", "VI 检查", "语气", "品牌审查"], "files"),
    ("user-research-toolkit", "用户研究工具箱", "skill", "r07", ["r05", "r11"],
     ["用户访谈", "问卷", "可用性", "用户研究"], "files"),
    ("market-intelligence-radar", "市场情报雷达", "skill", "r05", ["r12", "r01"],
     ["竞品监控", "情报", "基线变化", "市场监测"], "files"),
    ("strategic-growth-compass", "战略与增长罗盘", "skill", "r01", ["r07", "r12"],
     ["战略", "SWOT", "PESTEL", "路线图", "增长"], "files"),
    ("business-ops-analysis", "经营运营分析", "skill", "r02", ["r06", "r12"],
     ["经营分析", "异常识别", "运营", "指标"], "files"),
    ("trae-design", "设计系统与 solo 设计（4 技能）", "multi", "r10", ["r08", "r09"],
     ["设计系统", "design token", "海报", "图像编辑"], "files"),
    ("whiteboard", "可编辑白板/架构图", "skill", "r10", ["r07", "r08", "r02"],
     ["白板", "架构图", "信息架构", "excalidraw"], "files"),
    ("web-app-development", "uicraft 生产级 Web 界面", "skill", "r09", ["r08", "r10"],
     ["前端", "落地页", "响应式", "可访问性"], "files"),
    ("frontend-design", "高质量前端界面", "skill", "r09", ["r08", "r10"],
     ["前端组件", "页面", "视觉质量"], "files"),
    ("ecommerce-designer", "电商视觉设计", "skill", "r10", ["r14", "r12"],
     ["主图", "详情页", "电商设计", "卖点视觉"], "files"),
    ("smart-product-selector", "智能选品分析", "skill", "r14", ["r01", "r06", "r12"],
     ["选品", "利润测算", "竞品对标", "选品报告"], "files"),
]


def version_dir(plugin):
    p = os.path.join(TRAE, plugin)
    if not os.path.isdir(p):
        return None
    versions = [d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))]
    return os.path.join(p, sorted(versions)[-1]) if versions else None


def copy_docs(src_root, dest_root):
    copied = 0
    if not src_root or not os.path.isdir(src_root):
        return copied
    for dirpath, dirnames, filenames in os.walk(src_root):
        dirnames[:] = [d for d in dirnames if d not in ("assets", "node_modules", "references",
                                                        "scripts", "layouts", "licenses", ".git")]
        for name in filenames:
            if name != "SKILL.md" and name != "README.md" and not name.upper().startswith("LICENSE"):
                continue
            src = os.path.join(dirpath, name)
            rel = os.path.relpath(src, src_root)
            dest = os.path.join(dest_root, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1
    return copied


catalog = []
for cap_id, title, kind, owner, consumers, triggers, requires in CAPS:
    is_wb = cap_id in ("ecommerce-designer", "smart-product-selector")
    src_root = (os.path.join(WB, cap_id) if is_wb else version_dir(cap_id))
    if not src_root:
        print("MISSING", cap_id)
        continue
    dest_root = os.path.join(BASE, ROLES[owner], "references", "external", cap_id)
    if os.path.isdir(dest_root):
        shutil.rmtree(dest_root)
    n = copy_docs(src_root, dest_root)
    skills = []
    for dirpath, _dirnames, filenames in os.walk(dest_root):
        if "SKILL.md" in filenames:
            rel = os.path.relpath(os.path.join(dirpath, "SKILL.md"), dest_root)
            skills.append({"name": os.path.basename(os.path.dirname(rel)) or cap_id,
                           "doc": rel.replace("\\", "/")})
    skills.sort(key=lambda s: s["doc"])
    catalog.append({
        "id": cap_id, "title": title, "kind": kind,
        "owner": owner, "owner_dir": ROLES[owner], "consumers": consumers,
        "triggers": triggers, "requires": requires,
        "source": src_root, "docs_dir": os.path.relpath(dest_root, BASE).replace("\\", "/"),
        "docs_files": n, "skills": skills,
    })
    print(f"{cap_id:<34} -> {ROLES[owner]:<26} docs={n:<3} skills={len(skills)}")

out_dir = os.path.join(BASE, "shared", "external_capabilities")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "catalog.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump({"version": 1, "generated_for": "蛙蛙呱呱agents团",
               "count": len(catalog), "capabilities": catalog}, fh,
              ensure_ascii=False, indent=1)

# 每个角色的外部能力索引
by_role = {}
for c in catalog:
    by_role.setdefault(c["owner"], []).append(c)
for role, caps in sorted(by_role.items()):
    p = os.path.join(BASE, ROLES[role], "references", "external", "README.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    lines = [f"# {role.upper()} 外部能力索引",
             "",
             "由 `shared/external_capabilities` 生成；入口文档已拷入本目录，",
             "深层 references/ 与可执行脚本仍以 `source` 指向的原目录为准。",
             ""]
    for c in sorted(caps, key=lambda x: x["id"]):
        lines += [f"## {c['id']} · {c['title']}",
                  f"- 类型：`{c['kind']}`；消费方：{', '.join(c['consumers']) or '—'}",
                  f"- 触发词：{' / '.join(c['triggers'])}",
                  f"- 文档：`{c['docs_dir']}`（{c['docs_files']} 个文件，{len(c['skills'])} 个技能入口）",
                  f"- 源目录：`{c['source']}`",
                  ""]
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))

print(f"\ncatalog entries={len(catalog)} -> shared/external_capabilities/catalog.json")
