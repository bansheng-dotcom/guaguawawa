> status: ARCHIVED · 2026-11-27 · 现行规则见 docs/README.md

# 采集合规清单（COLLECTION-COMPLIANCE · v1.1 · 2026-11-24）

> 配套 `COLLECTION-SOP.md` 与 `configs/collections/_template.yaml`。
>
> **目标原则：默认拒绝，逐源取得证据后才允许执行；宁可少采，不可越线。**
>
> 实现边界：当前模板有 compliance 字段，但静态审查未确认其已成为所有采集入口的硬门。本文描述的是未来必须接线的规则，不表示门禁已经生效。本轮只更新文档，未修改代码、配置或测试。

---

## 一、适用范围与总原则

### 1.1 所有入口同门

`collection_spec.validate()` 必须执行完整的合同与合规校验；以下入口必须复用**同一个校验结果与同一个受控 fetch 层**，不得只在 CLI 或 `from_collection()` 增加检查：

- `collection_spec.preview()`
- `collection_spec.quality()`
- `collection_spec.run()`
- `card_probe` 对 preview/quality 的间接调用
- 未来新增的任何直接函数调用、批处理或 CLI 入口

**缺少规格、规格读取失败、YAML 解析失败、schema 不合法、合规证据缺失、合规明确拒绝，必须是不同错误。** 不得把异常统一吞成 `{}`，再按“没有采集规格”静默降级。

### 1.2 robots 不是完整授权

robots.txt 只回答爬虫协议的一部分，不等于服务条款许可、著作权许可、个人信息处理依据或对外分发授权。每源审核必须同时覆盖：

- 页面公开性与访问方式；
- robots 与目标路径；
- 服务条款、转载声明和站点规则；
- license、attribution 与二次分发范围；
- 个人信息与敏感内容；
- 频控、缓存、留存、复核和撤销后的下游处理。

### 1.3 不做整包 blanket claim

不得再写“本项目 78 个源都是政府/行情页，因此天然满足”。机构类型不能替代逐源、逐路径、逐时点的审核；政府公开页也可能有转载限制、个人信息、频控或技术措施。

当前 `configs/collections/` 静态核查仅见 `_template.yaml`，不能把模板声明当成任何真实源已通过审核。

---

## 二、六条硬红线

任何一条不满足，都不得进入 preview、quality 或 run。

| # | 红线 | 合格证据 | 违反时 |
|---|---|---|---|
| **R1 公开访问** | 无需登录、验证码、付费墙或特殊会话即可访问目标页；URL 与访问方式已记录。 | 停止，记 `blocked_private`。 |
| **R2 robots** | 已按抓取时的 robots 规则核对目标路径，保存 `robots_url / robots_checked_at / robots_result / evidence_hash`。 | 停止，记 `blocked_robots`；不得用“政府网站”豁免。 |
| **R3 不绕过技术措施** | 不伪造 Cookie、不破解签名、不轮换 IP 规避封禁、不绕过验证码或访问控制。 | 停止，记 `blocked_anticrawl`；不得改用其他通道继续同一绕过行为。 |
| **R4 不采个人信息** | 页面与目标字段均不含姓名、手机、身份证、个人地址等个人信息；字段级检查已记录。 | 停止，记 `blocked_pii`。**不是“先采进 staging 再脱敏”**；误采后立即隔离并按留存规则清理，同时核查下游。 |
| **R5 条款与许可** | 服务条款/转载声明已审核，`terms_reviewed=true`，license、署名和分发范围明确；需授权而尚无授权时不得采。 | 停止，记 `blocked_terms` 或 `blocked_license`。 |
| **R6 行为与留痕可执行** | 频控、UA、重试、快照、留存和撤销策略齐全；无法留痕的源不得进入 mart。 | 停止，记 `blocked_execution_policy`。 |

> 本文是工程合规门槛，不替代针对具体司法辖区和业务场景的法律意见。涉及个人信息时还应遵守适用的个人信息保护法律与最小必要原则。[《中华人民共和国个人信息保护法》](http://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html)

---

## 三、执行前门（目标契约）

| 门禁 | 判据 | 级别 | 未来实现位点 |
|---|---|---|---|
| **G-F 合规可执行** | R1–R6 所需证据齐全、有效且未过期；不是只检查几个布尔值。 | **hard / 拒绝执行** | `collection_spec` 共用前置校验；所有直接/间接入口必经 |
| **G-G 留痕完整** | 每行有 `url/fetched_at/html_sha256/quote/fetch_id/compliance_review_id`，mart 能回溯到不可变快照。 | hard | 受控 fetch + staging/mart 发布前检查 |
| **G-H 个人信息阻断** | 规格与字段检查均声明不采个人信息；检测到疑似个人信息即停止并隔离。 | hard | fetch 前后字段检查与 mart 发布门 |
| **G-I 快照一致** | 同一 run/source 的 preview、quality、run 使用同一 fetch_id；重复请求必须有显式原因。 | hard（数据图/质量声明） | `card_probe` + collection fetch/session |
| **G-J 合规时效** | `reviewed_at/review_due/terms_version` 有效；过期、条款变化或授权撤销后不得继续复用旧许可。 | hard | validate + 资产复用检查 |

### 3.1 fail-closed 的最小结果字段

```yaml
status: blocked                 # allowed | blocked | error
reason: blocked_terms           # 不用空字符串或 None 代替
source_id: example
path: /target/path
review_id: CR-...
reviewed_at: 2026-11-24T00:00:00+08:00
review_due: 2027-02-24
evidence:
  robots_url: ...
  terms_url: ...
  license: ...
  pii_scope_checked: true
recovery_condition: 完成条款复核并更新 review_id
```

布尔值只能作为审核结果的索引，不能替代原始证据、审核时间、适用路径和复核期限。

---

## 四、频控、缓存与重试

以下是本项目的保守默认值，不是法律规定的通用安全线；具体源可以更严格。

| 项 | 默认/要求 | 说明 |
|---|---|---|
| `rate_limit_rps` | ≤ 1 | 单源限速；不得通过并发绕过。站点条款更严格时从其规定。 |
| 并发 | 默认单源串行 | AutoThrottle 类机制只能辅助，不能替代明确的来源审核与上限。 |
| 抓取时段 | 按目标站点时区、条款和负载评估 | 不再把本地 22:00–06:00 当成所有站点都适用的默认“低峰”。 |
| `user_agent_note` | 项目标识与可联系渠道 | 不伪装成普通用户绕过站点管理。 |
| 重试 | 有限次数、指数退避并带抖动 | 4xx 不自动重试；429 尊重 `Retry-After`；5xx 也不能无限重试。 |
| 条件请求/缓存 | 复用 ETag、Last-Modified 与本地快照 | 遵循 HTTP 缓存语义，减少重复下载，不为“新鲜”制造无效请求。 |
| 抓取量 | 逐源设上限与熔断 | 超限、持续 429/5xx 或负载异常时停止并人工复核。 |
| 一次抓取复用 | 同一 run/source 只抓一次 | preview/quality/run 共享不可变快照，避免成本、频控和快照不一致。 |

参考标准：[RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)、[RFC 9110 Conditional Requests](https://www.rfc-editor.org/rfc/rfc9110.html#name-conditional-requests)、[RFC 9111](https://httpwg.org/specs/rfc9111.html)、[RFC 6585 §4](https://www.rfc-editor.org/rfc/rfc6585.html#section-4)。Scrapy 的 [settings](https://doc.scrapy.org/en/master/topics/settings.html) 与 [AutoThrottle](https://doc.scrapy.org/en/master/topics/autothrottle.html) 仅作工程机制参考，不要求本项目引入 Scrapy。

---

## 五、单快照与留痕

### 5.1 一次抓取，多处复用

同一 run/source 的流程应为：

```text
合规前置门 → 受控 fetch → 不可变快照 + fetch_id
                              ├─ preview（只读）
                              ├─ quality（只读）
                              └─ run/staging（同一输入版本）
```

不得让 preview 和 quality 各自重新 fetch。若确需重新抓取，必须新建 fetch_id，写明原因，并禁止把两个时点的结果拼成同一质量结论。

### 5.2 每行 staging/mart 的最低血缘字段

```text
url                    原始页面地址（归一化后）
fetched_at             抓取时间（ISO8601，带时区）
html_sha256            原始内容哈希
quote                  支撑该行的原文片段（按 source_verify 现行要求）
fetch_id               本次不可变抓取快照
compliance_review_id   本次执行依据的合规审核版本
source_id              来源登记 ID
transform_version      解析/转换逻辑版本
```

**缺少关键血缘的行不得进 mart。** 快照留存本身也受访问控制、保存期限、二次分发和撤销规则约束，不能以“缓存”为理由无限期保存。

---

## 六、署名、分发与撤销

| 项 | 要求 |
|---|---|
| `license` | 逐源填写真实许可或使用边界，如 CC BY 4.0、仅内部研究、需授权；“政府公开信息”不是可任意再分发的通用许可证。 |
| `attribution` | 报告出处写机构、页面标题、发布日期/抓取日期和 URL，不写“网络整理”。 |
| 二次分发 | “仅内部研究”或分发范围不明的源，不进入对外分享包；原始快照与派生 CSV 同样受限。 |
| 转载内容 | 尽量追溯到原始机构；转载页不能自动获得比原页更宽的使用权。 |
| 定期复核 | 保存 `reviewed_at/review_due/terms_version`；条款、robots、页面访问方式或许可变化时重新审核。 |
| 撤销响应 | 能沿血缘定位受影响 staging、mart、claims、chart、report 与外发包，按适用要求执行停用、删除或重建。 |

撤销不是只停止下一次抓取。若旧资产继续被缓存键复用，合规风险仍会通过报告和图表向下游扩散。

---

## 七、每源上线前检查单

- [ ] 目标 URL 与路径明确，无需登录、验证码、付费墙或特殊会话。
- [ ] robots 已按目标路径核对，证据和检查时间已保存。
- [ ] 服务条款、转载声明、license、署名与分发范围已审核，未用过期 review。
- [ ] 不绕过任何技术措施，不通过其他通道规避拒绝。
- [ ] 页面和字段均不采个人信息；没有“先采再脱敏”的例外。
- [ ] 单源限速、并发、重试、429/5xx 熔断、抓取量和快照策略已配置。
- [ ] UA 带真实项目标识与联系渠道。
- [ ] preview/quality/run 均经过同一前置门；配置损坏和证据缺失会拒绝而非跳过。
- [ ] 试跑只产生一次源请求，preview/quality/run 引用同一 fetch_id。
- [ ] 每行 mart 可回溯到 URL、时间、内容哈希、quote、fetch_id、review_id 和转换版本。
- [ ] 已演练条款/授权撤销：能列出并处理全部下游资产与报告。

全部满足才允许进入产线。任何后续变更都必须重新评估，不得继承整包“天然合规”的结论。

---

## 八、未来实施时的同步文件

| 改动 | 实现/测试同步 | 文档同步 |
|---|---|---|
| 共用合规前置门与 YAML 错误分类 | `core/sources/collection_spec.py`；`tests/test_derivation.py`、`tests/test_collection_contract.py`、`tests/test_cards.py` | 本文、`COLLECTION-SOP.md`、`UPGRADE-PLAN.md` WP5 |
| preview/quality/run 单快照 | `core/cards/pipeline.py`、collection/fetch 实现；增加请求次数和 fetch_id 断言 | 本文第四、五节 |
| 合规字段与审核版本 | `configs/collections/_template.yaml` 及真实逐源规格（未来实施时） | 本文检查单；不得只改模板不接校验 |
| 撤销与下游失效 | 资产 manifest、缓存键、mart/claims/report 血缘及相关测试 | 本文第六节、能力降级规则 |
| 活跃技能副本 | 经授权使用 `scripts/sync_trae_skill.py`，先 `--check` | D 盘文档保存不等于活跃技能已更新 |
