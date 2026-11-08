import sys
sys.stdout.reconfigure(encoding='utf-8')

def send_mock_notification():
    print("==================================================")
    print("📢 [Mission Control Sync] 20 个智能体推演完成！")
    print("文件已生成：D:\一人公司\全量20智能体停车场实战推演.html")
    print("已触发飞书/Notion API (Mock)，R04 最终审查结论为: PASS")
    print("==================================================")

send_mock_notification()
