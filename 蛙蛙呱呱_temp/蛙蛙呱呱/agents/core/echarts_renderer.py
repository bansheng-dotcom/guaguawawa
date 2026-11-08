# core/echarts_renderer.py
import json

def render_echarts_html(title: str, chart_data: dict, container_id: str = "main") -> str:
    """将静态报表升级为 ECharts 交互式大屏。"""
    chart_config = json.dumps(chart_data, ensure_ascii=False)
    
    html = f'''
    <div id="{container_id}" style="width: 100%; height: 400px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); background: #fff; padding: 15px;"></div>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function () {{
            var chartDom = document.getElementById('{container_id}');
            var myChart = echarts.init(chartDom);
            var option = {chart_config};
            
            // 自动化注入企业品牌色 (Design Tokens MVP)
            option.color = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6'];
            
            option && myChart.setOption(option);
            
            // 下钻 (Drill-down) 交互预留
            myChart.on('click', function (params) {{
                console.log("Drill down into:", params.name);
                // 这里可以调用飞书/后端 API
            }});
            
            window.addEventListener('resize', function() {{
                myChart.resize();
            }});
        }});
    </script>
    '''
    return html
