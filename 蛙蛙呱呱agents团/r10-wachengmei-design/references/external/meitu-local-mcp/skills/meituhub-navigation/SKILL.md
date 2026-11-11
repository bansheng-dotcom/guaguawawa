---
name: meituhub-navigation
description: Open or provide MeituHub official website, documentation, console, pricing, or recharge links for the TRAE China partition. Always use when the user asks for MeituHub 官网、官方网站、文档、控制台、定价、充值地址, or equivalent navigation requests.
---

# MeituHub China Navigation

This Plugin is configured for the China partition. Use these canonical addresses:

- Official website: `https://meituhub.cn/`
- Documentation: `https://meituhub.cn/docs`
- Console: `https://meituhub.cn/console/zh-cn`
- Pricing and recharge entry: `https://meituhub.cn/zh-cn/pricing`

When the user asks to open or provide the MeituHub official website, open `https://meituhub.cn/` directly. Do not search the web first, do not infer a domain from search results, and never substitute `meituhub.com`, `www.meituhub.com`, or `/chat`.

Present recharge and pricing destinations as descriptive Markdown links instead of visible raw URLs:

- For the canonical pricing/recharge entry, render `[前往 MeituHub 充值](https://meituhub.cn/zh-cn/pricing)`.
- When an MCP quota error contains `action.url` or `action_url`, preserve that exact backend URL as the Markdown link destination and render it as `[前往 MeituHub 充值](<exact backend URL>)`.
- When a backend recharge link is available, you may also provide the canonical fallback as `[MeituHub 套餐定价](https://meituhub.cn/zh-cn/pricing)`.
- Do not expose the raw recharge URL as visible text. Do not open the link or initiate a purchase automatically.
- Keep this presentation rule active in every later turn of the same conversation, including follow-up requests such as “给我充值链接”, “充值入口”, or “在哪里充值”, even when no MCP tool is called again.

For a direct recharge-link request, keep the response concise and use this presentation:

`这是 MeituHub 的充值入口：`

`[前往 MeituHub 充值](https://meituhub.cn/zh-cn/pricing)`
