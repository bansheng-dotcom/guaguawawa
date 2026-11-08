# core/enhanced_report_renderer.py
import json

def render_multimodal_html(title: str, markdown_html: str, echarts_data: dict = None, mermaid_logic: str = None) -> str:
    '''
    多模态企业级 HTML 报告渲染器 (Multi-Modal Renderer)。
    集合了：VI注入 + 动态ECharts + Mermaid脑图 + TTS语音播报占位
    '''
    
    mermaid_html = ""
    if mermaid_logic:
        mermaid_html = f'''
        <div class="mindmap-container" style="background:#f4f6f7; padding:20px; border-radius:8px; margin-bottom:20px;">
            <h3 style="margin-top:0;">🧠 架构/逻辑透视 (Mindmap)</h3>
            <pre class="mermaid">
            {mermaid_logic}
            </pre>
        </div>
        '''

    echarts_html = ""
    if echarts_data:
        echarts_html = f'''
        <div id="chart-main" style="width: 100%; height: 400px; border-radius: 8px; background: #fff; padding: 15px; margin-bottom:20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);"></div>
        <script>
            document.addEventListener('DOMContentLoaded', function () {{
                var chartDom = document.getElementById('chart-main');
                var myChart = echarts.init(chartDom);
                var option = {json.dumps(echarts_data, ensure_ascii=False)};
                option && myChart.setOption(option);
            }});
        </script>
        '''

    podcast_html = '''
    <div class="podcast-container" style="display:flex; align-items:center; background:#ebf5fb; padding:15px; border-radius:30px; margin-bottom:20px;">
        <span style="font-size:24px; margin-right:15px;">🎧</span>
        <div>
            <div style="font-weight:bold; color:#2980b9;">执行摘要播报 (AI Podcast)</div>
            <div style="font-size:12px; color:#555;">正在调用 TTS 引擎生成中...</div>
        </div>
    </div>
    '''

    full_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <!-- 引入自动编译的企业 VI CSS -->
    <link rel="stylesheet" href="../styles/color-system/corporate-vi.css">
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.4.0/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    <style>
        body {{
            font-family: var(--font-body, 'Helvetica Neue', sans-serif);
            color: var(--color-text_main, #333);
            background-color: var(--color-background, #fafafa);
            line-height: 1.6; padding: 40px; max-width: 900px; margin: 0 auto;
        }}
        .report-box {{ background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
        h1, h2 {{ color: var(--color-primary, #2c3e50); }}
        h1 {{ border-bottom: 3px solid var(--color-secondary, #3498db); padding-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="report-box">
        <h1>{title}</h1>
        {podcast_html}
        {mermaid_html}
        {echarts_html}
        <div class="content">
            {markdown_html}
        </div>
    </div>
</body>
</html>
    '''
    return full_html
