# 采购总拥有成本

> 归属：R15　消费：r14, r03

## 定位

多报价 landed cost 对比 + 生命周期 TCO。

## 我们怎么用

- 命令：`python agent.py tco compare / lifecycle`
- 这是本团队自有的确定性技能，规则与门禁已写进代码。

## 规则要点

- landed cost 含货值/起运/主运/保险/关税/不可抵扣税/报关/到港/杂费
- 用可用数量（扣不良）计算单位成本
- 资金占用按账期折算进 effective unit cost
- 仅货值+运费不叫 TCO，至少 3 类成本
