# 测试保护重构 优先级规则

1. 先 debug（复现+根因）再 refactor，顺序固定。
2. root_cause 为空不进 refactor。
3. 回归测试不绿不进交付。
4. 热点劣化（after>before）优先修代码，不硬凑度量。
