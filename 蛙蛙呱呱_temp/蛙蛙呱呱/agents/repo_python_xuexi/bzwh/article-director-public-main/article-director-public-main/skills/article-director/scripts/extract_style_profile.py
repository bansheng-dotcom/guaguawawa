"""
extract_style_profile.py — 从用户文章中提取文体特征，生成风格经验库

用法：
    python extract_style_profile.py --input-dir1 "D:\知识库\knowledge\...\深度解读" --input-dir2 "D:\知识库\knowledge\...\初级"

输出：
    style-profiles/profile.json          机器可读的风格指纹
    style-profiles/style-guide.md        人类可读的风格指南
    style-profiles/exemplars/            范例段落
    style-profiles/anti-patterns.json    AI 味特征 + 用户不用的表达

设计参考：
    - write-like-me (github.com/Hiro-Inagawa/write-like-me) 的 7-stage pipeline
    - stylometric-transfer (github.com/ngpepin/stylometric-transfer) 的 JSON fingerprint 方案
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


# ══════════════════════════════════════════════════════════════
# 特征提取函数
# ══════════════════════════════════════════════════════════════

def clean_text(text: str) -> str:
    """去掉 markdown 标记和元数据，保留纯文本"""
    # 去掉 YAML frontmatter
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    # 去掉标题行的元数据（作者/时间/类型/ID）
    text = re.sub(r"\*\*作者\*\*:.*?\n", "", text)
    text = re.sub(r"\*\*时间\*\*:.*?\n", "", text)
    text = re.sub(r"\*\*类型\*\*:.*?\n", "", text)
    text = re.sub(r"\*\*ID\*\*:.*?\n", "", text)
    # 去掉 markdown 格式标记
    text = re.sub(r"```[\s\S]*?```", "[CODE]", text)  # 代码块
    text = re.sub(r"`[^`]+`", "[CODE]", text)  # 行内代码
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)  # 图片
    text = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)  # 链接保留文字
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # 标题标记
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # 加粗
    text = re.sub(r"\*([^*]+)\*", r"\1", text)  # 斜体
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)  # 列表标记
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)  # 有序列表
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)  # 引用
    text = re.sub(r"---+", "", text)  # 分隔线
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """中文分句"""
    # 按中文句号、问号、叹号、分号分句
    sentences = re.split(r"[。！？；\n]+", text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]


def split_paragraphs(text: str) -> list[str]:
    """分段落"""
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]


def extract_features(text: str) -> dict:
    """从单篇文章提取文体特征"""
    clean = clean_text(text)
    sentences = split_sentences(clean)
    paragraphs = split_paragraphs(clean)

    if not sentences or not paragraphs:
        return {}

    # ── 句长分布 ──
    sent_lengths = [len(s) for s in sentences]
    sent_lengths.sort()

    # ── 段落长度（按句数）──
    para_sent_counts = []
    for p in paragraphs:
        sents = split_sentences(p)
        para_sent_counts.append(len(sents))

    # ── 标点密度 ──
    comma_count = clean.count("，") + clean.count(",")
    period_count = clean.count("。") + clean.count("！") + clean.count("？")
    question_count = clean.count("？") + clean.count("?")

    # ── 过渡词/短语 ──
    transitions = [
        "但是", "所以", "而", "因此", "然而", "不过", "同时", "另外",
        "例如", "比如", "换句话说", "也就是说", "具体来说", "总的来说",
        "你会发现", "你会发现", "在实际", "对于", "如果说", "那么",
        "答案是", "问题是", "关键是", "本质", "其实", "说实话",
    ]
    transition_counts = {}
    for t in transitions:
        count = clean.count(t)
        if count > 0:
            transition_counts[t] = count

    # ── 开头模式 ──
    first_para = paragraphs[0] if paragraphs else ""
    opening_patterns = {
        "starts_with_question": bool(re.search(r"[？?]", first_para[:100])),
        "starts_with_data": bool(re.search(r"\d+", first_para[:100])),
        "starts_with_scenario": bool(re.search(r"当你|假如|如果|假设", first_para[:100])),
        "starts_with_direct": first_para.startswith("写这") or first_para.startswith("本篇") or first_para.startswith("前言"),
    }

    # ── 第一人称 ──
    first_person_count = len(re.findall(r"我[^们]", clean)) + len(re.findall(r"我们", clean))
    second_person_count = len(re.findall(r"你[^们]", clean)) + len(re.findall(r"你们", clean))

    # ── 疑问句密度 ──
    question_density = question_count / max(len(sentences), 1)

    # ── 四字短语 ──
    four_char_phrases = re.findall(r"[一-鿿]{4}", clean)
    four_char_count = len(four_char_phrases)

    # ── 口语化表达 ──
    colloquial_markers = ["说实话", "老实说", "坦白说", "简单来说", "说白了",
                          "其实就是", "本质上", "说到底", "归根结底"]
    colloquial_count = sum(clean.count(m) for m in colloquial_markers)

    return {
        "char_count": len(clean),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "sentence_length": {
            "mean": sum(sent_lengths) / len(sent_lengths),
            "median": sent_lengths[len(sent_lengths) // 2],
            "min": min(sent_lengths),
            "max": max(sent_lengths),
        },
        "paragraph_length": {
            "mean_sentences": sum(para_sent_counts) / len(para_sent_counts) if para_sent_counts else 0,
            "median_sentences": sorted(para_sent_counts)[len(para_sent_counts) // 2] if para_sent_counts else 0,
        },
        "punctuation": {
            "comma_per_sentence": comma_count / max(len(sentences), 1),
            "question_per_paragraph": question_count / max(len(paragraphs), 1),
        },
        "transitions": transition_counts,
        "opening_patterns": opening_patterns,
        "pronouns": {
            "first_person_per_1000": first_person_count / max(len(clean) / 1000, 1),
            "second_person_per_1000": second_person_count / max(len(clean) / 1000, 1),
        },
        "question_density": question_density,
        "four_char_phrase_density": four_char_count / max(len(sentences), 1),
        "colloquial_density": colloquial_count / max(len(paragraphs), 1),
    }


def aggregate_features(all_features: list[dict]) -> dict:
    """聚合所有文章的特征"""
    if not all_features:
        return {}

    n = len(all_features)

    # 聚合句长
    all_sent_means = [f["sentence_length"]["mean"] for f in all_features if f]
    all_sent_medians = [f["sentence_length"]["median"] for f in all_features if f]

    # 聚合段落长度
    all_para_means = [f["paragraph_length"]["mean_sentences"] for f in all_features if f]

    # 聚合标点
    all_comma_rates = [f["punctuation"]["comma_per_sentence"] for f in all_features if f]
    all_question_rates = [f["punctuation"]["question_per_paragraph"] for f in all_features if f]

    # 聚合过渡词
    all_transitions = Counter()
    for f in all_features:
        if f and "transitions" in f:
            all_transitions.update(f["transitions"])

    # 聚合开头模式
    opening_counts = Counter()
    for f in all_features:
        if f and "opening_patterns" in f:
            for k, v in f["opening_patterns"].items():
                if v:
                    opening_counts[k] += 1

    # 聚合代词
    all_first_person = [f["pronouns"]["first_person_per_1000"] for f in all_features if f]
    all_second_person = [f["pronouns"]["second_person_per_1000"] for f in all_features if f]

    # 聚合疑问句密度
    all_question_densities = [f["question_density"] for f in all_features if f]

    # 聚合四字短语密度
    all_four_char = [f["four_char_phrase_density"] for f in all_features if f]

    # 聚合口语化密度
    all_colloquial = [f["colloquial_density"] for f in all_features if f]

    return {
        "article_count": n,
        "total_chars": sum(f["char_count"] for f in all_features if f),
        "sentence_length": {
            "mean": sum(all_sent_means) / len(all_sent_means) if all_sent_means else 0,
            "median": sorted(all_sent_medians)[len(all_sent_medians) // 2] if all_sent_medians else 0,
        },
        "paragraph_length": {
            "mean_sentences": sum(all_para_means) / len(all_para_means) if all_para_means else 0,
        },
        "punctuation": {
            "comma_per_sentence": sum(all_comma_rates) / len(all_comma_rates) if all_comma_rates else 0,
            "question_per_paragraph": sum(all_question_rates) / len(all_question_rates) if all_question_rates else 0,
        },
        "top_transitions": dict(all_transitions.most_common(20)),
        "opening_patterns": {k: v for k, v in opening_counts.most_common()},
        "pronouns": {
            "first_person_per_1000": sum(all_first_person) / len(all_first_person) if all_first_person else 0,
            "second_person_per_1000": sum(all_second_person) / len(all_second_person) if all_second_person else 0,
        },
        "question_density": sum(all_question_densities) / len(all_question_densities) if all_question_densities else 0,
        "four_char_phrase_density": sum(all_four_char) / len(all_four_char) if all_four_char else 0,
        "colloquial_density": sum(all_colloquial) / len(all_colloquial) if all_colloquial else 0,
    }


# ══════════════════════════════════════════════════════════════
# 范例提取
# ══════════════════════════════════════════════════════════════

def extract_exemplars(text: str, max_per_type: int = 5) -> dict:
    """从文章中提取范例段落"""
    clean = clean_text(text)
    paragraphs = split_paragraphs(clean)

    exemplars = {
        "opening": [],      # 开头段落
        "transition": [],   # 过渡段落
        "evidence": [],     # 论证段落
        "closing": [],      # 结尾段落
    }

    for i, para in enumerate(paragraphs):
        # 开头段落（前 2 段）
        if i < 2 and len(para) > 50 and len(exemplars["opening"]) < max_per_type:
            exemplars["opening"].append(para[:500])

        # 过渡段落（包含过渡词的段落）
        transition_words = ["但是", "所以", "而", "你会发现", "换句话说", "不过", "然而"]
        if any(w in para for w in transition_words) and len(para) > 50:
            if len(exemplars["transition"]) < max_per_type:
                exemplars["transition"].append(para[:500])

        # 论证段落（包含数字和案例的段落）
        if re.search(r"\d+", para) and len(para) > 100:
            has_case = any(kw in para for kw in ["比如", "例如", "就像", "拿", "假设"])
            if has_case and len(exemplars["evidence"]) < max_per_type:
                exemplars["evidence"].append(para[:500])

        # 结尾段落（最后 2 段）
        if i >= len(paragraphs) - 2 and len(para) > 50:
            if len(exemplars["closing"]) < max_per_type:
                exemplars["closing"].append(para[:500])

    return exemplars


# ══════════════════════════════════════════════════════════════
# AI 味模式检测
# ══════════════════════════════════════════════════════════════

# 用户文章中从未出现的 AI 典型表达
AI_TYPICAL_PATTERNS = [
    "值得注意的是", "值得注意的是", "综上所述", "总而言之", "不难看出",
    "毋庸置疑", "由此可见", "标志着", "开辟了新纪元", "迎来了新的里程碑",
    "具有深远的意义", "在当今社会", "随着科技的飞速发展", "引发了广泛关注",
    "成为了热门话题", "取得了显著成效", "呈现出蓬勃发展的态势",
    "注入了新的活力", "提供了有力支撑", "奠定了坚实基础", "发挥了重要作用",
    "实现了历史性跨越", "开启了新征程", "谱写了新篇章", "构建了新格局",
    "首先", "其次", "再次", "最后", "总之", "总的来说",
    "希望这有帮助", "如有疑问请随时", "好问题", "你说得太对了",
    "由于现有资料有限", "未来充满希望", "前景广阔",
    "从这个角度看", "换个角度看", "可以这样理解", "更准确地说",
    "说白了", "简单来说", "本质上", "某种意义上", "可以看到", "不难发现",
    "delve", "fascinating", "showcasing", "additionally", "testament",
    "landscape", "pivotal", "transformative", "revolutionary",
    "cutting-edge", "state-of-the-art",
]


def detect_anti_patterns(text: str) -> list[str]:
    """检测文章中出现的 AI 味表达"""
    hits = []
    for pattern in AI_TYPICAL_PATTERNS:
        if pattern in text:
            hits.append(pattern)
    return hits


# ══════════════════════════════════════════════════════════════
# 输出生成
# ══════════════════════════════════════════════════════════════

def generate_style_guide(profile: dict) -> str:
    """从 profile.json 生成人类可读的风格指南"""
    sl = profile.get("sentence_length", {})
    pl = profile.get("paragraph_length", {})
    pu = profile.get("punctuation", {})
    pr = profile.get("pronouns", {})
    top_trans = profile.get("top_transitions", {})
    opening = profile.get("opening_patterns", {})

    guide = f"""# 作者风格指南

基于 {profile.get('article_count', 0)} 篇文章、{profile.get('total_chars', 0):,} 字的分析结果。
生成时间：{_now()}

## 一、句式特征

- **平均句长**：{sl.get('mean', 0):.1f} 字（中位数 {sl.get('median', 0):.0f} 字）
- **风格**：长短交替，短句用于强调（10 字以内），长句用于解释复杂逻辑（30-60 字）
- **逗号密度**：每句 {pu.get('comma_per_sentence', 0):.1f} 个逗号

### 好的句式
- 短句强调：「因为没有用。」「答案是，实际做法并不是那么做的。」
- 长句解释：用逗号串联多个分句，形成递进或对比

### 避免的句式
- 均匀句长（每句都 20-30 字）
- 过多被动句
- 过多"的"字连缀

## 二、段落特征

- **平均段落长度**：{pl.get('mean_sentences', 0):.1f} 句
- **风格**：段落短小精悍，一个段落只说一件事

## 三、过渡方式

**偏好过渡词**（按频率排序）：
"""

    for word, count in list(top_trans.items())[:10]:
        guide += f"- 「{word}」（出现 {count} 次）\n"

    guide += f"""
**过渡原则**：
- 用具体例子过渡，不用抽象过渡词
- 「你会发现」是高频模式——用它引入新的认知
- 用反问句引出下一个论点
- 不用「首先...其次...最后...」

## 四、开头模式

"""
    for pattern, count in opening.items():
        label = {
            "starts_with_question": "以问题开头",
            "starts_with_data": "以数据/数字开头",
            "starts_with_scenario": "以场景/假设开头",
            "starts_with_direct": "以直接声明/前言开头",
        }.get(pattern, pattern)
        guide += f"- {label}：{count} 篇\n"

    guide += f"""
**开头原则**：
- 直接进入场景或问题，不用抽象定义开头
- 前言部分交代背景和写作目的
- 不用「在当今社会」「随着...的发展」这类空话

## 五、人称与语气

- **第一人称密度**：{pr.get('first_person_per_1000', 0):.1f} 次/千字
- **第二人称密度**：{pr.get('second_person_per_1000', 0):.1f} 次/千字
- **疑问句密度**：{profile.get('question_density', 0):.2f}（每句）

**语气特征**：
- 口语化、直率，偶尔用粗口强调
- 大量反问句引导读者思考
- 用「你会发现」引入新认知
- 用「说实话」「老实说」表达真诚

## 六、论证方式

- **数据驱动**：大量具体数字（{profile.get('four_char_phrase_density', 0):.1f} 个四字短语/句）
- **案例优先**：先给案例，再给结论
- **公司案例**：拼多多、阿里、字节跳动、哈啰出行等真实公司
- **SQL 示例**：在需要时给出实际 SQL 代码

## 七、禁用表达

详见 `anti-patterns.json`。核心原则：
- 避免空泛套话；AI 味判断与修订标准见 `D:\知识库\skills\内容生产\ai-tone-director`
- 不用「首先...其次...最后...」结构
- 不用英文禁词（delve, fascinating, showcasing 等）
"""
    return guide


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ══════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════

def load_articles(input_dirs: list[str]) -> list[tuple[str, str]]:
    """加载所有文章，返回 [(filename, content), ...]"""
    articles = []
    for dir_path in input_dirs:
        p = Path(dir_path)
        if not p.exists():
            print(f"  [WARN] 目录不存在: {dir_path}")
            continue
        for f in sorted(p.glob("*.md")):
            if f.name == "README.md":
                continue
            try:
                content = f.read_text(encoding="utf-8")
                if len(content) > 100:  # 跳过太短的文件
                    articles.append((f.name, content))
            except Exception as e:
                print(f"  [WARN] 读取失败 {f.name}: {e}")
    return articles


def main():
    parser = argparse.ArgumentParser(description="从用户文章提取文体特征")
    parser.add_argument("--input-dirs", nargs="+", required=True, help="文章目录列表")
    parser.add_argument("--output-dir", default=None, help="输出目录（默认：style-profiles/）")
    args = parser.parse_args()

    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).resolve().parent.parent / "style-profiles"

    output_dir.mkdir(parents=True, exist_ok=True)
    exemplars_dir = output_dir / "exemplars"
    exemplars_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"风格提取开始")
    print(f"输入目录: {args.input_dirs}")
    print(f"输出目录: {output_dir}")
    print(f"{'='*60}")

    # ── 1. 加载文章 ──
    articles = load_articles(args.input_dirs)
    print(f"\n加载 {len(articles)} 篇文章")

    if not articles:
        print("[ERROR] 没有找到文章")
        sys.exit(1)

    # ── 2. 提取每篇文章的特征 ──
    print("\n提取文体特征...")
    all_features = []
    all_exemplars = {"opening": [], "transition": [], "evidence": [], "closing": []}
    all_anti_patterns = []

    for filename, content in articles:
        features = extract_features(content)
        if features:
            all_features.append(features)

        # 提取范例
        exemplars = extract_exemplars(content)
        for key in all_exemplars:
            all_exemplars[key].extend(exemplars[key])

        # 检测 AI 味
        anti_hits = detect_anti_patterns(content)
        all_anti_patterns.extend(anti_hits)

    # ── 3. 聚合特征 ──
    print("聚合特征...")
    profile = aggregate_features(all_features)

    # ── 4. 保存 profile.json ──
    profile_path = output_dir / "profile.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    print(f"  保存: {profile_path}")

    # ── 5. 生成 style-guide.md ──
    guide = generate_style_guide(profile)
    guide_path = output_dir / "style-guide.md"
    guide_path.write_text(guide, encoding="utf-8")
    print(f"  保存: {guide_path}")

    # ── 6. 保存范例 ──
    for key, exemplars in all_exemplars.items():
        if exemplars:
            # 去重，取前 5 个
            seen = set()
            unique = []
            for e in exemplars:
                short = e[:100]
                if short not in seen:
                    seen.add(short)
                    unique.append(e)
            unique = unique[:5]

            exemplar_path = exemplars_dir / f"{key}-patterns.md"
            content = f"# {key.title()} 范例\n\n"
            for i, e in enumerate(unique, 1):
                content += f"## 范例 {i}\n\n{e}\n\n---\n\n"
            exemplar_path.write_text(content, encoding="utf-8")
            print(f"  保存: {exemplar_path}")

    # ── 7. 保存 anti-patterns.json ──
    anti_pattern_counts = Counter(all_anti_patterns)
    anti_patterns = {
        "description": "AI 味表达 + 用户文章中未出现的典型 AI 模式",
        "found_in_corpus": dict(anti_pattern_counts.most_common()),
        "ai_typical_patterns": AI_TYPICAL_PATTERNS,
        "user_style_anti_patterns": [
            "不用「首先...其次...最后...」结构",
            "不用「值得注意的是」「综上所述」等空话",
            "不用「在当今社会」「随着...的发展」开头",
            "不用英文禁词（delve, fascinating, showcasing）",
            "不用均匀句长，保持长短交替",
            "不用抽象过渡词，用具体例子过渡",
        ],
    }
    anti_path = output_dir / "anti-patterns.json"
    with open(anti_path, "w", encoding="utf-8") as f:
        json.dump(anti_patterns, f, ensure_ascii=False, indent=2)
    print(f"  保存: {anti_path}")

    # ── 8. 输出摘要 ──
    print(f"\n{'='*60}")
    print(f"提取完成")
    print(f"  文章数: {profile.get('article_count', 0)}")
    print(f"  总字数: {profile.get('total_chars', 0):,}")
    print(f"  平均句长: {profile.get('sentence_length', {}).get('mean', 0):.1f} 字")
    print(f"  平均段落长: {profile.get('paragraph_length', {}).get('mean_sentences', 0):.1f} 句")
    print(f"  疑问句密度: {profile.get('question_density', 0):.2f}")
    print(f"  第一人称密度: {profile.get('pronouns', {}).get('first_person_per_1000', 0):.1f}/千字")
    print(f"  范例段落: {sum(len(v) for v in all_exemplars.values())} 个")
    print(f"  AI 味命中: {len(all_anti_patterns)} 个")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
