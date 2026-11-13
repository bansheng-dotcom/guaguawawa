r"""
工作流状态管理 + 归档清理 — 文章撰写流水线的轻量编排器。

Author: 首辅
Created: 2026-05-05
Updated: 2026-05-05 添加归档和清理逻辑

用法:
    python workflow_writer.py <选题需求文件路径> [--draft <草稿路径>] [--archive <选题ID>] [--cleanup] [--dry-run]
    python workflow_writer.py --director-init --topic-id <选题ID> --title <标题> [--brief <摘要>]
    python workflow_writer.py --approve <选题ID> --title <标题> [--publish-url <链接>]

归档机制（硬编码）:
    --archive <选题ID>
    1. 将 tmp/{id}-draft.md 优先归档到 D:\知识库\knowledge\docs\知识星球-ai数据分析社区/
    2. 将 tmp/{id}-detailed-outline.md 归档到 state/topic-requirements/
    3. 清理 tmp/ 中该选题的所有中间文件
    4. 保留 tmp/ 中最近一次选题的中间文件，删除更早的

清理规则:
    --cleanup
    1. 扫描 tmp/ 中所有 {id}-* 格式的中间文件
    2. 按选题ID分组
    3. 如果某ID已有归档文件在知识库正式存稿目录，删除其中间文件
    4. 保留最近一次选题的中间文件（用于调试）
    5. 删除超过 7 天的孤立中间文件
"""
import json
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 当前内容生产根目录承载 tmp/、state/、platforms/ 等项目级资源。
CONTENT_ROOT = PROJECT_ROOT
LEGACY_PROJECT_ROOT = Path(r"D:\知识库\projects\知识星球自动更新-AI社群")
TMP_DIR = CONTENT_ROOT / "tmp"
STATE_DIR = CONTENT_ROOT / "state" / "workflow-runs"
PLATFORM_DIR = CONTENT_ROOT / "platforms" / "知识星球"
KNOWLEDGE_DOCS_DIR = Path(r"D:\知识库\knowledge\docs\知识星球-ai数据分析社区")
DEFAULT_SERIES_DIR = KNOWLEDGE_DOCS_DIR / "大模型工作流系列"
TOPIC_REQ_DIR = CONTENT_ROOT / "state" / "topic-requirements"

# 工作流配置
MAX_RETRIES = 2
TMP_KEEP_DAYS = 7  # 超过7天的临时文件自动清理


class WorkflowState:
    """工作流状态文件"""

    def __init__(self, topic_path: str):
        self.topic_path = Path(topic_path)
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.state_file = STATE_DIR / f"run-{self.run_id}.json"
        self.state = {
            "run_id": self.run_id,
            "topic_file": str(self.topic_path),
            "stage": "init",
            "draft_path": None,
            "check_passed": False,
            "check_retries": 0,
            "check_issues": [],
            "review_result": None,
            "approved": False,
            "published_url": None,
            "history": [],
        }
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    def transition(self, new_stage: str, note: str = ""):
        old = self.state["stage"]
        self.state["stage"] = new_stage
        entry = {
            "time": datetime.now().isoformat(),
            "from": old, "to": new_stage, "note": note
        }
        self.state["history"].append(entry)
        self._save()
        print(f"  [{old} → {new_stage}] {note}")

    def set_draft(self, path: str):
        self.state["draft_path"] = path
        self._save()

    def set_check_result(self, passed: bool, issues: list):
        self.state["check_passed"] = passed
        self.state["check_issues"] = issues
        if not passed:
            self.state["check_retries"] += 1
        self._save()

    def set_review_result(self, result: dict):
        self.state["review_result"] = result
        self._save()

    def set_approved(self):
        self.state["approved"] = True
        self._save()

    def set_published(self, url: str):
        self.state["published_url"] = url
        self._save()

    def _save(self):
        self.state_file.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def can_retry(self) -> bool:
        return self.state["check_retries"] < MAX_RETRIES

    def status(self) -> str:
        s = self.state
        return (
            f"运行ID: {s['run_id']}\n"
            f"选题: {s['topic_file']}\n"
            f"阶段: {s['stage']}\n"
            f"草稿: {s['draft_path'] or '未生成'}\n"
            f"代码检查: {'✓通过' if s['check_passed'] else f'✗未通过 (重试{s['check_retries']}/{MAX_RETRIES})'}\n"
            f"AI审查: {'已完成' if s['review_result'] else '未执行'}\n"
            f"人工审批: {'✓已批准' if s['approved'] else '待审批'}\n"
            f"发布: {s['published_url'] or '未发布'}"
        )


def run_code_check(draft_path: str) -> dict:
    """运行代码检查脚本"""
    checker = CONTENT_ROOT / "scripts" / "check_article.py"
    result = subprocess.run(
        ["python", str(checker), draft_path],
        capture_output=True, text=True, encoding="utf-8"
    )
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"pass": False, "issues": [f"检查脚本异常: {result.stderr}"], "passed": []}


def archive_topic(topic_id: str, dry_run: bool = False) -> dict:
    r"""
    归档选题产出。

    1. tmp/{id}-draft.md → D:\知识库\knowledge\docs\知识星球-ai数据分析社区\大模型工作流系列\{id}.md
    2. tmp/{id}-detailed-outline.md → state/topic-requirements/{id}-outline.md
    3. 清理 tmp/ 中该ID的所有中间文件
    4. 清理 tmp/ 中的过期文件
    """
    result = {"archived": [], "cleaned": [], "errors": []}

    DEFAULT_SERIES_DIR.mkdir(parents=True, exist_ok=True)
    PLATFORM_DIR.mkdir(parents=True, exist_ok=True)
    TOPIC_REQ_DIR.mkdir(parents=True, exist_ok=True)

    # 归档草稿
    draft_src = TMP_DIR / f"{topic_id}-draft.md"
    if draft_src.exists():
        draft_dst = DEFAULT_SERIES_DIR / f"{topic_id}.md"
        if not dry_run:
            shutil.copy2(draft_src, draft_dst)
            draft_src.unlink()
        result["archived"].append(f"草稿: {draft_src.name} → {draft_dst}")

    # 归档细纲
    outline_src = TMP_DIR / f"{topic_id}-detailed-outline.md"
    if outline_src.exists():
        outline_dst = TOPIC_REQ_DIR / f"{topic_id}-outline.md"
        if not dry_run:
            shutil.copy2(outline_src, outline_dst)
            outline_src.unlink()
        result["archived"].append(f"细纲: {outline_src.name} → {outline_dst}")

    # 归档大纲（如果有）
    plain_outline = TMP_DIR / f"{topic_id}-outline.md"
    if plain_outline.exists():
        plain_outline.unlink()
        result["cleaned"].append(f"大纲(已归档): {plain_outline.name}")

    # 清理该ID的其他临时文件
    for f in TMP_DIR.glob(f"{topic_id}-*"):
        if f.is_file() and f.name not in [draft_src.name, outline_src.name]:
            if not dry_run:
                f.unlink()
            result["cleaned"].append(f"临时文件: {f.name}")

    # 清理过期临时文件
    cleanup_old_tmp(dry_run=dry_run, keep_recent=True, result=result)

    return result


def cleanup_old_tmp(dry_run: bool = False, keep_recent: bool = True, result: dict = None):
    """
    清理 tmp/ 目录。

    规则：
    1. 扫描所有 {prefix}-* 格式的中间文件
    2. 按前缀分组（同一次选题的中间文件归一组）
    3. 如果某组对应的草稿已归档到知识库正式存稿目录，删除该组全部文件
    4. 保留最近一次选题的中间文件（按文件修改时间排序）
    5. 删除超过 TMP_KEEP_DAYS 天的孤立文件
    """
    if result is None:
        result = {"cleaned": []}

    cutoff = datetime.now() - timedelta(days=TMP_KEEP_DAYS)
    groups = {}

    # 按选题ID前缀分组
    for f in TMP_DIR.glob("*-*"):
        if not f.is_file():
            continue
        # 跳过非选题中间文件（如 _trim.py, charts/ 等）
        if f.name.startswith("_") or f.suffix not in [".md", ".json", ".html", ".png"]:
            continue

        # 提取前缀：token-consumption-draft.md → token-consumption
        parts = f.stem.split("-")
        for i in range(len(parts) - 1, 0, -1):
            candidate = "-".join(parts[:i])
            # 检查这是否是一个合法的选题ID前缀
            if len(candidate) >= 3:
                if candidate not in groups:
                    groups[candidate] = []
                groups[candidate].append(f)
                break

    # 找到最近一次选题
    latest_group = None
    latest_mtime = 0
    for group_id, files in groups.items():
      max_mtime = max(f.stat().st_mtime for f in files)
      if max_mtime > latest_mtime:
          latest_mtime = max_mtime
          latest_group = group_id

    # 清理逻辑
    for group_id, files in groups.items():
        should_delete = False

        # 条件1：已归档到知识库正式存稿目录；兼容旧 platforms/ 归档
        if (DEFAULT_SERIES_DIR / f"{group_id}.md").exists() or (PLATFORM_DIR / f"{group_id}.md").exists():
            should_delete = True

        # 条件2：不是最近一次选题（如果 keep_recent）
        if keep_recent and group_id != latest_group:
            # 检查文件是否超过保留天数
            oldest = min(f.stat().st_mtime for f in files)
            oldest_dt = datetime.fromtimestamp(oldest)
            if oldest_dt < cutoff:
                should_delete = True

        if should_delete and not dry_run:
            for f in files:
                f.unlink()
                result["cleaned"].append(f"过期: {f.name}")

    # 清理非选题相关文件（超过7天）
    for f in TMP_DIR.iterdir():
        if f.is_file() and f.name.startswith("_"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff and not dry_run:
                f.unlink()
                result["cleaned"].append(f"孤立: {f.name}")

    return result


def print_header(title: str):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


def init_director_workflow(topic_id: str, title: str, brief: str = "") -> int:
    script = PROJECT_ROOT / "scripts" / "article_director_init.py"
    cmd = [sys.executable, str(script), "--topic-id", topic_id, "--title", title]
    if brief:
        cmd.extend(["--brief", brief])
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def approve_director_content(topic_id: str, title: str, publish_url: str = "") -> int:
    output_dir = PROJECT_ROOT / "skills" / "article-director" / "outputs" / topic_id
    run_script = output_dir / f"run_{topic_id}_expanded.py"
    if not run_script.exists():
        run_script = output_dir / f"run_{topic_id}.py"
    runner_script = PROJECT_ROOT / "skills" / "article-director" / "scripts" / "workflow_runner.py"

    if run_script.exists():
        approve_cmd = [sys.executable, str(runner_script), "--script", str(run_script), "--approve", "--approver", "用户"]
        if publish_url:
            approve_cmd.extend(["--publish-url", publish_url])
        approve_result = subprocess.run(approve_cmd, capture_output=True, text=True, encoding="utf-8")
        if approve_result.stdout.strip():
            print(approve_result.stdout.strip())
        if approve_result.returncode != 0:
            if approve_result.stderr.strip():
                print(approve_result.stderr.strip(), file=sys.stderr)
            return approve_result.returncode

        run_result = subprocess.run(
            [sys.executable, str(runner_script), "--script", str(run_script)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        payload = run_result.stdout.strip() or run_result.stderr.strip()
        print(payload)
        return run_result.returncode

    script = CONTENT_ROOT / "scripts" / "content_ingest.py"
    if not script.exists():
        script = LEGACY_PROJECT_ROOT / "scripts" / "content_ingest.py"
    cmd = [sys.executable, str(script), "--topic-id", topic_id, "--title", title]
    if publish_url:
        cmd.extend(["--publish-url", publish_url])
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    payload = result.stdout.strip() or result.stderr.strip()
    print(payload)
    return result.returncode


def main():
    # 强制 UTF-8 输出
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    if "--director-init" in sys.argv:
        topic_id = ""
        title = ""
        brief = ""
        if "--topic-id" in sys.argv and sys.argv.index("--topic-id") + 1 < len(sys.argv):
            topic_id = sys.argv[sys.argv.index("--topic-id") + 1]
        if "--title" in sys.argv and sys.argv.index("--title") + 1 < len(sys.argv):
            title = sys.argv[sys.argv.index("--title") + 1]
        if "--brief" in sys.argv and sys.argv.index("--brief") + 1 < len(sys.argv):
            brief = sys.argv[sys.argv.index("--brief") + 1]
        if not topic_id or not title:
            print("用法: python workflow_writer.py --director-init --topic-id <选题ID> --title <标题> [--brief <摘要>]")
            sys.exit(2)
        sys.exit(init_director_workflow(topic_id, title, brief))

    if "--approve" in sys.argv:
        topic_id = ""
        title = ""
        publish_url = ""
        if sys.argv.index("--approve") + 1 < len(sys.argv):
            topic_id = sys.argv[sys.argv.index("--approve") + 1]
        if "--title" in sys.argv and sys.argv.index("--title") + 1 < len(sys.argv):
            title = sys.argv[sys.argv.index("--title") + 1]
        if "--publish-url" in sys.argv and sys.argv.index("--publish-url") + 1 < len(sys.argv):
            publish_url = sys.argv[sys.argv.index("--publish-url") + 1]
        if not topic_id or not title:
            print("用法: python workflow_writer.py --approve <选题ID> --title <标题> [--publish-url <链接>]")
            sys.exit(2)
        sys.exit(approve_director_content(topic_id, title, publish_url))

    if len(sys.argv) < 2:
        print("用法: python workflow_writer.py <选题需求文件路径> [选项]")
        print()
        print("选项:")
        print("  --draft <路径>    提交草稿进行代码检查")
        print("  --archive <选题ID>  归档已发布文章，清理临时文件")
        print("  --cleanup          仅清理过期临时文件")
        print("  --director-init    初始化 article-director workflow")
        print("  --approve <选题ID>  人工确认后执行正式入库")
        print("  --dry-run          预览模式，不实际修改文件")
        print()
        print("归档规则（硬编码）:")
        print("  1. tmp/{id}-draft.md → D:\\知识库\\knowledge\\docs\\知识星球-ai数据分析社区\\大模型工作流系列\\{id}.md")
        print("  2. tmp/{id}-detailed-outline.md → state/topic-requirements/{id}-outline.md")
        print("  3. 删除 tmp/ 中该选题所有中间文件")
        print("  4. 保留最近一次选题的中间文件")
        print("  5. 超过7天的孤立文件自动删除")
        sys.exit(2)

    topic_path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    # ── 归档模式 ──
    archive_idx = [i for i, a in enumerate(sys.argv) if a == "--archive"]
    if archive_idx and archive_idx[0] + 1 < len(sys.argv):
        topic_id = sys.argv[archive_idx[0] + 1]
        print_header(f"归档: {topic_id}")
        result = archive_topic(topic_id, dry_run=dry_run)

        if result["archived"]:
            print("\n已归档:")
            for a in result["archived"]:
                print(f"  ✓ {a}")
        if result["cleaned"]:
            print("\n已清理:")
            for c in result["cleaned"]:
                print(f"  ✓ {c}")
        if result["errors"]:
            print("\n错误:")
            for e in result["errors"]:
                print(f"  ✗ {e}")
        if dry_run:
            print("\n[预览模式，未实际修改]")
        return

    # ── 清理模式 ──
    if "--cleanup" in sys.argv:
        print_header("清理临时文件")
        result = cleanup_old_tmp(dry_run=dry_run)
        if result["cleaned"]:
            for c in result["cleaned"]:
                print(f"  ✓ {c}")
        else:
            print("  无过期文件")
        if dry_run:
            print("\n[预览模式，未实际修改]")
        return

    # ── 工作流模式 ──
    if not Path(topic_path).exists():
        print(f"选题文件不存在: {topic_path}")
        sys.exit(2)

    wf = WorkflowState(topic_path)
    wf.transition("init", "工作流初始化")

    print_header("工作流已初始化")
    print(wf.status())
    print(f"\n状态文件: {wf.state_file}")
    print(f"\n下一步: 完成草稿后运行 python {__file__} {topic_path} --draft <草稿路径>")

    # 如果传了 --draft，执行代码检查
    draft_idx = [i for i, a in enumerate(sys.argv) if a == "--draft"]
    if draft_idx and draft_idx[0] + 1 < len(sys.argv):
        draft_path = sys.argv[draft_idx[0] + 1]
        wf.set_draft(draft_path)
        wf.transition("draft", f"草稿已提交: {draft_path}")

        print_header("代码检查")
        check_result = run_code_check(draft_path)
        print(json.dumps(check_result, ensure_ascii=False, indent=2))
        wf.set_check_result(check_result["pass"], check_result.get("issues", []))

        if check_result["pass"]:
            wf.transition("check", "代码检查通过 → 进入AI审查")
            print("\n✓ 代码检查通过。下一步: AI审查")
            print(f"  审查Agent规范: {PROJECT_ROOT / 'agents' / 'reviewer.md'}")
            print(f"  调用方式: 将草稿+审查规范发给独立子Agent进行审查")
        else:
            if wf.can_retry():
                wf.transition("check", f"代码检查失败，可重试 ({wf.state['check_retries']}/{MAX_RETRIES})")
                print(f"\n✗ 代码检查不通过。请修改后重新检查（剩余重试{MAX_RETRIES - wf.state['check_retries']}次）")
            else:
                wf.transition("blocked", "代码检查重试次数耗尽，任务暂停，需人工介入")
                print(f"\n✗ 重试次数耗尽！任务已暂停。请人工检查问题并决定是否继续。")

    print(f"\n当前状态:\n{wf.status()}")


if __name__ == "__main__":
    main()
