# s05 交互原型与动效（motion / motion·prototype）方法论
> 蒸馏自: 补充技能/01-当前能力域/LottieFiles__motion-design-skill/SKILL.md
>


来源沉淀：`LottieFiles__motion-design-skill`（三支柱：情绪意图/视觉叙事/动效工艺；
四人格：playful/premium/corporate/energetic）+ `mae616__design-skills`（creative-coder）。

## 一、方法论（什么时候用、核心口径）

「动效是信息，不是噪音」。两个动作：
- `motion`：校验动效规格——personality 白名单、时长在人格区间内、easing 非空、
  入场减速/出场加速（enter=decelerate、exit=accelerate）、reduced_motion 支持、三层动效齐备。
- `prototype`：校验交互原型——flow ≥1、screens ≥1、trigger 非空。

核心红线：**加速度方向与语义一致**——元素入场要减速（decelerate/ease-out）、出场要加速
（accelerate/ease-in），反了即 BLOCKER；`reduced_motion` 必须 `true` 或 `"supported"`。

## 二、可执行口径（公式 / 输出键 / 判读规则，与实现逐字对齐）

阈值外置：`motion.personalities`（4 人格）、`motion.duration_ms`（每人格的 [lo, hi] 区间）。

**motion 校验规则**：
- `personality` 不在 4 人格 → BLOCKER。
- `duration_ms` 非数字，或不在该人格区间（如 playful 150–300、premium 350–600）→ BLOCKER。
- `easing` 空 → BLOCKER。
- `acceleration.enter` ∉ {decelerate, ease-out} 或 `exit` ∉ {accelerate, ease-in} → BLOCKER。
- `reduced_motion` 非 true/"supported" → BLOCKER。
- `layers` 缺 primary/secondary/ambient 任一 → BLOCKER。

**prototype 校验规则**：`flow` 空、`screens` 空、`trigger` 空 → 各自 BLOCKER。

**输出键**：motion → `personality/duration_ms`；prototype → `flow_count/screen_count`。

## 三、已验证算例（run_tests.py 与 verify_loop.py 全绿，非新编）

- `examples/motion.json`：personality=playful、duration=220（在 150–300）、easing 非空、
  enter=decelerate/exit=accelerate、reduced_motion=true、三层齐 → ok=true。
- `examples/prototype.json`：flow/screens 各 3、trigger 非空 → ok=true。
- 脏夹具 `motion_dirty.json`：personality=violent（非法）、duration=9999（超区间）、
  easing 空、加减速反了、reduced_motion=false → ok=false / exit 1。
- 脏夹具 `prototype_dirty.json`：全空 → ok=false / exit 1。

## 四、实战踩坑（真拦下来的教训）

- **时长区间要按人格取**：`duration_ms[personality]` 是二级字典，先判 personality 合法
  再取区间，否则 `KeyError`。playful 150–300 与 premium 350–600 差很多，同一 duration
  在不同人格下合法与否不同。
- **加减速方向别写反**：语义是「入场缓入、出场缓出」。enter 集合是 {decelerate, ease-out}，
  exit 集合是 {accelerate, ease-in}，两组对调就是 BLOCKER。
- **reduced_motion 兼容字符串**：允许 `true` 或 `"supported"`（有的设计稿写字符串），
  `False` 或 `"unsupported"` 才拦，别只认布尔。
- **三层动效是 dict 不是 list**：primary/secondary/ambient 各是非空字符串，缺任一
  即 BLOCKER——主视觉动、环境动都得有层次。
