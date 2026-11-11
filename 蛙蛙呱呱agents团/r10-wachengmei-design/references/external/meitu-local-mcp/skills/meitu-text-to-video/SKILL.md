---
name: meitu-text-to-video
description: Generate a dynamic video from a pure text description via the meitu-local MCP `text-to-video` tool, covering high-quality default mode and high-motion quick mode. Use for text-to-video, generate a video from text, ad video, product promo, or a short video from a written concept.
---

# 文生视频（text-to-video）

从纯文字描述生成动态视频，覆盖高画质默认模式与高动态快速模式。

## 工具

调用 `meitu-local` MCP Server 的 **`text-to-video`** 工具。

## 环境与前置

- 未连接美图账号先引导授权；`meitu_auth_status` 检查，绝不索取 AK/SK。
- 工具缺失用 `meitu_registry_status` / `meitu_registry_refresh`。
- 本地文件只用工作区内路径；交付给出媒体 URL / 任务 ID。

## Prompt 编写

- 明确：主体、动作、场景、运镜、光影、时长与氛围。
- 避免多物体同动、精细手势、大幅转身等易畸变内容。
- 需要口播/字幕时按目标语言给出，不自动生成无据文案。

## 场景

- 广告视频、产品宣传片、主题短视频成片。

## 执行对齐合约（知识库 k_video_execution_contract 必检）

- **语种继承三字段**：生成前锁定「用户原始语种」「目标输出语言（默认同原始语种，仅用户明确指定才改）」「用户意图与禁用词（否定词必须原样保留）」。**目标输出语言约束所有画面内可见文本**：对白、旁白、字幕、屏幕文字、招牌标识。禁止"用中文沟通就默认中文成片"，也禁止已锁定目标语言后夹带别国字幕/对白。
- **对白/旁白必须写进 prompt**：分镜里有对白或叙事旁白时逐句写进 prompt 要求模型直出，格式 `说话人(情绪)：「台词」`；**禁止**判成"后期叠加配音"从 prompt 删掉（平台后期配音不在能力内，删掉=成片没人说话）。台词语言跟随上述目标输出语言。
- 视频按时长计费：单段≤15s 视为简单任务直接执行；多段+拼接/多集/完整分镜/跨段一致性视为复杂，先确认参数或索要素材再生成，**不跳过素材准备直接调付费工具**。
- 不生成写实真人脸部驱动内容（知识库/平台限制，系统自动拦截）。

## 短视频方法参考

- 分镜先定结构：钩子 → 知识点/卖点 → 案例/实操 → 总结/CTA；第 1 帧强视觉刺激，0–3s 交代"谁+怎么了"，禁黑场开场。
- 台词每句≤10 字、全片克制；钩子前置。

## 工作流

1. 确认主题与视频目标（广告/宣传/短片），必要时先生成分镜脚本（`text-generate`）。
2. 写清楚 prompt，调用 `text-to-video`（异步用 `meitu_task_get` 跟进）。
3. 复核画面与成片结构。

## 输出规范

- 说明脚本结构、生成了何种动态画面；视频给出 URL/任务 ID。