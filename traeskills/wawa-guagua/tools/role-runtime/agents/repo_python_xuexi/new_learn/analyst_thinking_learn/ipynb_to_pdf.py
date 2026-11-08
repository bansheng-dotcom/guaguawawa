"""
ipynb → PDF 转换工具
====================

将 Jupyter Notebook (.ipynb) 转换为排版良好的 PDF 文件。
针对中文内容优化：行间距、表格、引用块、列表等。

用法:
    # 命令行（PDF 自动输出到 pdf/week_xx/day_xx/ 镜像目录）
    python ipynb_to_pdf.py week_01/day_06/笔记.ipynb

    # 指定输出路径
    python ipynb_to_pdf.py 笔记.ipynb -o 指定路径.pdf

    # 保留中间 HTML
    python ipynb_to_pdf.py 笔记.ipynb --keep-html

    # 只转 HTML 不转 PDF
    python ipynb_to_pdf.py 笔记.ipynb --to-html-only

    # 作为模块导入
    from ipynb_to_pdf import ipynb_to_pdf
    ipynb_to_pdf("week_01/day_06/笔记.ipynb")

依赖:
    pip install nbconvert nbformat playwright
    playwright install chromium
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path
from typing import Optional


# ============================================================
# 路径配置 —— 脚本所在目录即 analyst_thinking_learn 根目录
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent  # analyst_thinking_learn/
PDF_ROOT = SCRIPT_DIR / "pdf"                 # pdf/ 镜像根目录


# ============================================================
# 中文排版 CSS —— 经过多轮迭代优化的配置
# 如需调整行间距/字体/表格样式，修改此处的 CSS 即可
# ============================================================

CHINESE_TYPOGRAPHY_CSS = """
<style>
/* === 全局中文排版 === */
body {
    font-family: 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB',
                 'Noto Sans CJK SC', sans-serif;
    line-height: 1.9;
    font-size: 14px;
    color: #333;
}

/* === 段落 === */
p {
    margin-bottom: 0.9em;
    line-height: 1.9;
    orphans: 3;
    widows: 3;
}

/* === 标题 === */
h1 { line-height: 1.4; margin: 1.4em 0 0.7em 0; }
h2 { line-height: 1.5; margin: 1.3em 0 0.6em 0; }
h3 { line-height: 1.5; margin: 1.1em 0 0.5em 0; }
h4 { line-height: 1.5; margin: 1.0em 0 0.4em 0; }
h5, h6 { line-height: 1.5; margin: 0.9em 0 0.3em 0; }

/* === 列表 === */
li {
    line-height: 1.9;
    margin-bottom: 0.4em;
}
ul, ol {
    margin-bottom: 0.8em;
}

/* === 表格 === */
table {
    margin: 1em 0;
    border-collapse: collapse;
    width: 100%;
}
td, th {
    line-height: 1.8;
    padding: 8px 12px;
    vertical-align: top;
}
th {
    background: #f0f3f7;
    font-weight: 600;
    white-space: nowrap;
}
td {
    border-bottom: 1px solid #e8e8e8;
}
td p, th p {
    margin-bottom: 0.3em;
    line-height: 1.8;
}

/* === 引用块 === */
blockquote {
    line-height: 1.85;
    margin: 1em 0;
    padding: 0.6em 1.2em;
    border-left: 4px solid #4a90d9;
    background: #f5f7fa;
    border-radius: 0 4px 4px 0;
}
blockquote p {
    line-height: 1.85;
    margin-bottom: 0.5em;
}
blockquote p:last-child {
    margin-bottom: 0;
}

/* === 粗体 === */
strong {
    font-weight: 600;
}

/* === 行内代码 === */
code {
    font-family: 'Cascadia Code', 'Fira Code', Consolas, monospace;
    background: #f0f0f0;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.9em;
}

/* === 分隔线 === */
hr {
    margin: 1.5em 0;
    border: none;
    border-top: 1px solid #e0e0e0;
}

/* === notebook 单元格间距 === */
.jp-MarkdownOutput {
    padding: 2px 0;
}
</style>
"""

# PDF 页面设置
PAGE_CONFIG = {
    "format": "A4",
    "print_background": True,
    "margin": {
        "top": "20mm",
        "bottom": "20mm",
        "left": "15mm",
        "right": "15mm",
    },
}


# ============================================================
# 核心转换函数
# ============================================================

def ipynb_to_html(ipynb_path: str, html_path: Optional[str] = None) -> str:
    """
    将 .ipynb 文件转换为带中文排版优化的 HTML。

    参数:
        ipynb_path: notebook 文件路径
        html_path: 输出 HTML 路径（可选，默认与 notebook 同目录同名）

    返回:
        生成的 HTML 文件路径

    异常:
        FileNotFoundError: notebook 文件不存在
        nbformat.reader.NotJSONError: notebook 格式无效
    """
    import nbformat
    from nbconvert import HTMLExporter
    from traitlets.config import Config

    # 验证输入文件
    ipynb_path = Path(ipynb_path).resolve()
    if not ipynb_path.exists():
        raise FileNotFoundError(f"找不到文件: {ipynb_path}")
    if ipynb_path.suffix.lower() != ".ipynb":
        raise ValueError(f"文件类型不正确（需要 .ipynb）: {ipynb_path}")

    # 确定输出路径
    if html_path is None:
        html_path = str(ipynb_path.with_suffix(".html"))
    else:
        html_path = str(Path(html_path).resolve())

    # 读取 notebook
    print(f"[1/3] 读取 notebook: {ipynb_path.name}")
    with open(ipynb_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    # 转换为 HTML（禁用可能缺失的预处理器）
    print(f"[2/3] 转换为 HTML（注入中文排版 CSS）...")
    config = Config()
    config.HTMLExporter.preprocessors = []

    exporter = HTMLExporter(config=config)
    (body, resources) = exporter.from_notebook_node(nb)

    # 注入中文排版样式
    body = body.replace("</head>", CHINESE_TYPOGRAPHY_CSS + "</head>")

    # 写入 HTML 文件
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(body)

    print(f"      HTML 已保存: {html_path}")
    return html_path


def html_to_pdf(html_path: str, pdf_path: str) -> str:
    """
    使用 Playwright/Chromium 将 HTML 渲染为 PDF。

    参数:
        html_path: HTML 文件路径
        pdf_path: 输出 PDF 文件路径

    返回:
        生成的 PDF 文件路径

    异常:
        FileNotFoundError: HTML 文件不存在
        RuntimeError: Playwright/Chromium 不可用
    """
    from playwright.sync_api import sync_playwright

    html_path = Path(html_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(f"找不到 HTML 文件: {html_path}")

    pdf_path = str(Path(pdf_path).resolve())

    print(f"[3/3] 渲染 PDF（Chromium 无头浏览器）...")

    # file:// URL 需要正斜杠
    file_url = f"file:///{str(html_path).replace(chr(92), chr(47))}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="load", timeout=60000)
        page.pdf(path=pdf_path, **PAGE_CONFIG)
        browser.close()

    # 检查输出
    pdf_size_kb = os.path.getsize(pdf_path) / 1024
    print(f"      PDF 已生成: {pdf_path}")
    print(f"      文件大小: {pdf_size_kb:.1f} KB")

    return pdf_path


def _resolve_pdf_path(ipynb_path: Path, pdf_path: Optional[str]) -> Path:
    """
    解析 PDF 输出路径。默认映射到 pdf/ 镜像目录：
        week_01/day_06/xxx.ipynb → pdf/week_01/day_06/xxx.pdf

    如果 ipynb 不在 analyst_thinking_learn 目录树下，则回退到同目录输出。
    """
    if pdf_path:
        return Path(pdf_path).resolve()

    ipynb_path = ipynb_path.resolve()

    try:
        # 尝试计算相对于 analyst_thinking_learn 的路径
        relative = ipynb_path.relative_to(SCRIPT_DIR)
        # 映射到 pdf/ 镜像
        target = PDF_ROOT / relative.with_suffix(".pdf")
        # 确保目标目录存在
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
    except ValueError:
        # ipynb 不在项目目录下 → 同目录输出
        return ipynb_path.with_suffix(".pdf")


def ipynb_to_pdf(
    ipynb_path: str,
    pdf_path: Optional[str] = None,
    keep_html: bool = False,
) -> str:
    """
    一站式：将 .ipynb 文件转换为 PDF。

    内部流程:
        1. ipynb → HTML（带中文排版优化）
        2. HTML → PDF（Playwright/Chromium 渲染）

    参数:
        ipynb_path: notebook 文件路径
        pdf_path:   输出 PDF 路径（默认自动映射到 pdf/ 镜像目录）
        keep_html:  是否保留中间 HTML 文件（默认 False，自动删除）

    返回:
        生成的 PDF 文件路径
    """
    ipynb_path = Path(ipynb_path).resolve()

    # 确定输出路径（自动映射到 pdf/ 镜像）
    resolved_pdf = _resolve_pdf_path(ipynb_path, pdf_path)

    # 中间 HTML 文件
    if keep_html:
        # 同样放在 pdf/ 镜像目录下
        html_path = str(resolved_pdf.with_suffix(".html"))
    else:
        tmp_fd, html_path = tempfile.mkstemp(suffix=".html", prefix="nb2pdf_")
        os.close(tmp_fd)

    try:
        # Step 1: ipynb → HTML
        generated_html = ipynb_to_html(str(ipynb_path), html_path)

        # Step 2: HTML → PDF
        result_pdf = html_to_pdf(generated_html, str(resolved_pdf))

        print(f"\n[OK] 转换完成: {result_pdf}")

    finally:
        # 清理临时 HTML
        if not keep_html and os.path.exists(html_path):
            os.remove(html_path)
            print(f"      (临时 HTML 已清理)")

    return result_pdf


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="将 Jupyter Notebook (.ipynb) 转换为中文排版优化的 PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ipynb_to_pdf.py 笔记.ipynb
  python ipynb_to_pdf.py 笔记.ipynb -o 输出.pdf
  python ipynb_to_pdf.py 笔记.ipynb --keep-html
        """,
    )
    parser.add_argument(
        "notebook",
        help="输入的 .ipynb 文件路径",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出 PDF 路径（默认与输入同目录同名）",
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="保留中间生成的 HTML 文件",
    )
    parser.add_argument(
        "--to-html-only",
        action="store_true",
        help="只转换为 HTML，不生成 PDF",
    )

    args = parser.parse_args()

    # 仅 HTML 模式
    if args.to_html_only:
        result = ipynb_to_html(args.notebook, args.output)
        print(f"\n[OK] HTML 已生成: {result}")
    else:
        result = ipynb_to_pdf(
            args.notebook,
            pdf_path=args.output,
            keep_html=args.keep_html,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
