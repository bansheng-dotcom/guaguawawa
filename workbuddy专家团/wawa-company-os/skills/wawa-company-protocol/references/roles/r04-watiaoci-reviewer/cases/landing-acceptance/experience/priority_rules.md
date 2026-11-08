# priority_rules（判据优先级：R04 评审排序）

1. 身份红线最优先：reviewer==producer 一票否决，任何产出不采纳。
2. 无证据的完成声明 > 无证据的判据 fail > 禁词措辞 > 绝对词：先砍"无证据"再管"怎么说"。
3. keep 项降级必须带 resolution_reason，无理由的降级视为复评违例。
4. warn 不阻断验收：只在报告里记观察项，不得借 warn 私自放行 fail。
5. 修复后复评只评本轮 change 区：新增 fail 无法定位到 change 区即打回。
