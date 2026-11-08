# priority_rules（判据优先级：门禁强度审计）

1. error 存活即 FAIL：先数 error，再看分数分层；任何 error 都不允许 verdict=PASS。
2. not evaluable 不是 pass：证据空/无区段直接判 NOT_EVALUABLE，不给满分也不给及格。
3. 评分只做分层（solid/at-risk/theatre），不做放行：放行只由 error 数决定。
4. 修复后复评必须重跑全部 7 模式，不信任缓存/上一轮结果。
5. 「文档写明不阻断」比「命令跑不过」更优先处理：前者是门禁剧场，危害在制度层。
