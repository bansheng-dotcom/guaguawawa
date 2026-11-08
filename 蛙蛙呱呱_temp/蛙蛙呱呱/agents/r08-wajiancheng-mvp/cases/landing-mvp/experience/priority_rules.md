# 取舍与优先级规则（落地页 MVP 场景）

1. 优先验证「最重要的一条假设」，不贪多；一个 slice 对应一个假设。
2. 技术约束不可妥协：no_js_library=false 直接 BLOCKER，不得上 React/Vue。
3. 佐证点多不如真：3 条可证实的 proof 优于 10 条空话。
4. 单文件优先：不能 single_file_index_html 就退化成多页，交给 R09，不做。
5. 表单可交付是底线：不能 form_deliverable 的页面只算静态展示，不算 MVP。