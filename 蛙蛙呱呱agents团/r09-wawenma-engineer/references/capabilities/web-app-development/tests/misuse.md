# 负向测试集（misuse cases）

> 运行方式：`python references/capabilities/web-app-development/scripts/gate_selftest.py --self-test`
> → 必须 `PASS 6/6`（含 3 个反例）。版本：v2.0.0

---

## 一、已被门禁拦住（机器可验）

| # | 错误片段 | 应被拦住的判定 | 实测 |
|---|---|---|---|
| MU-01 | 模块只写名字，没有 inputs/outputs | `spec.spec` 契约结构 | ✅ exit=1（`examples/spec_spec_dirty.json`） |
| MU-02 | 端到端切片链路不闭合（缺落库或可见结果） | `fullstack.feature` | ✅ exit=1（`examples/fullstack_feature_dirty.json`） |
| MU-03 | 鉴权规则不完整（只在前端隐藏） | `fullstack.auth` | ✅ exit=1（`examples/fullstack_auth_dirty.json`） |

## 二、门禁抓不到，靠 §6 自检与越权实测

| # | 错误片段 | 问题 | 谁来抓 |
|---|---|---|---|
| MU-04 | 出现孤儿输出（产出了没人用） | 白写的代码 | §6 契约连线检查 |
| MU-05 | 出现无源输入（要了没人给） | 永远跑不通 | §6 |
| MU-06 | 前端隐藏按钮当鉴权 | **安全事故**：直接调接口即可越权 | §3 三规则 + 越权实测 |
| MU-07 | 默认放行再补规则 | 新接口忘配＝谁都能进 | §3 默认拒绝 |
| MU-08 | 没做越权测试（横向/纵向/未登录） | 不知道是否真安全 | §6 三条实测 |
| MU-09 | 单测过就以为链路通 | 单测 ≠ 端到端 | §7 EX-12 |
| MU-10 | 测试跳过不说明 | 隐藏风险 | `harness testreport` 部分覆盖 |
| MU-11 | 材料不写影响面 | 下游不知影响范围 | `harness materials` 部分覆盖 |
| MU-12 | 循环依赖 / 下层反向依赖 | 改一处崩一片 | `spec arch` 部分覆盖 + §6 |
| MU-13 | 只做前端或只做后端就叫切片 | 两半各自不可验证 | §7 EX-04 |

---

## 三、自检

- [ ] 第一节每条"✅"都能在 `gate_selftest.py` 找到 fixture
- [ ] 契约表连过线：每个 outputs 有下游、每个 inputs 有上游
- [ ] 用低权限账号实测过三条越权路径（横向/纵向/未登录）
- [ ] 端到端切片亲手跑过一遍（不是只跑单测）
- [ ] 每次改 `spec`/`fullstack` 相关技能后重跑 `--self-test`

> **纪律**：鉴权结构合规 ≠ 真的安全。
> 门禁只能证明"规则写了"，证明不了"服务端真的验了"——后者只能靠越权实测。
