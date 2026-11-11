---
name: meitu-local-tools
description: Use Meitu image, video, and account-visible custom workflow tools exposed by the bundled Local MCP after the user connects a Meitu account in TRAE. Use for supported media tasks or MeituHub workflows; do not ask the user for AK/SK.
---

# Meitu Local Tools

Use the tools exposed by the `meitu-local` MCP Server.

- If `meitu_auth_status` reports no access token, ask the user to connect their Meitu account through the TRAE Connector. Never request AK/SK or a token in chat.
- Use `meitu_registry_status` when expected tools are missing, then call `meitu_registry_refresh` if a refresh is needed.
- Tools named `meitu_workflow__<listing_code>` are custom workflows currently visible to the connected Meitu account. Select one only when its description and declared inputs match the request.
- A workflow tool refreshes its account-visible listing before submission. If it is no longer available, tell the user to verify that the workflow is published for the connected account.
- Choose the narrowest business tool that matches the request and pass only its declared input fields.
- A single `image-face-swap` call takes both required images and produces one directional result: `head_image_url` supplies the source face/head, while `sence_image_url` supplies the target pose, clothing, and background. For a short request such as "face swap" or "交换头像" with two newly attached images, use the first image as `head_image_url`, the second as `sence_image_url`, and make exactly one call.
- Only make two `image-face-swap` calls when the user explicitly asks for a bidirectional swap or two reciprocal output images. Run those calls sequentially; finish the first call and its confirmation before starting the second.
- Media inputs accept public HTTP/HTTPS URLs, local absolute paths, and `file://` URLs. Pass the exact path supplied by the user or TRAE attachment context; do not invent, rewrite, or replace it with a guessed path.
- Public HTTP/HTTPS URLs can be sent directly. Before a local file is uploaded, the MCP normally requests explicit user confirmation through TRAE. Submitting the form allows the current call. If the user actively selects `Always trust MeituHub on this device`, the MCP persists local-file trust and later calls may proceed without another prompt. Never select or claim persistent trust on the user's behalf.
- Use `meitu_local_file_trust_status` when the user asks whether persistent local-file trust is enabled. Use `meitu_local_file_trust_revoke` when the user asks to stop trusting the plugin; after revocation, the next local-file call must prompt again.
- If confirmation is declined, cancelled, or unavailable, explain the returned MCP error and do not retry with another path automatically.
- Never run multiple tool calls containing local media in parallel because each call may open an independent Elicitation request. If a local-media call is declined, cancelled, or times out, return the original MCP error and do not automatically retry it.
- Relative local paths are valid only when the deployment explicitly configures a workspace root. Prefer the actual absolute path provided by TRAE.
- Return generated media URLs, task IDs, and trace IDs when available. Never expose credentials or raw authorization headers.
- This Plugin uses the China partition. The official MeituHub website is `https://meituhub.cn/`, and its default pricing/recharge page is `https://meituhub.cn/zh-cn/pricing`. When the user asks to open or provide the MeituHub website, use the `.cn` address and do not infer `meituhub.com` or `/chat`.
- If a quota error returns `action.url` or `action_url`, preserve that exact backend URL as the destination of `[前往 MeituHub 充值](<exact backend URL>)`. Show a descriptive Markdown link, never the raw recharge URL as visible text. You may also provide `[MeituHub 套餐定价](https://meituhub.cn/zh-cn/pricing)` as the canonical fallback. This presentation rule remains active in every later turn of the same conversation, including a follow-up asking only for the recharge link. Let the user open the link; never open it automatically or initiate a purchase.
- Do not invoke recharge, purchase, or account-management operations.
