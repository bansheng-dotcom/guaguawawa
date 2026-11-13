# materials/ · 知识库提炼原材料

本目录是 `dating-coach` 各 reference 模块的**原始素材文本产物**（已转写/解码），
供追溯知识来源与复现提炼流程使用。原始二进制素材（视频 / 音频 / rar）未入库，
如需重新生成文本，见 `../scripts/`。

## 目录说明

| 子目录 | 来源 | 内容 | 数量 |
|--------|------|------|------|
| `decoded_eml/` | 寒江雪《超级约会学》2009 邮件合集（俩姓婚姻 rar 同源） | GB2312 MIME 解码后的纯中文帖文，原样保留 | 10 篇 |
| `transcribed_audio/` | 《零失误社交搭讪全指南》（9 节 m4a） | faster-whisper small 转写文本 | 9 课 |
| `transcribed_video/` | 《Leon 撩妹 3.0》（17 节 mp4/mov） | faster-whisper small 转写文本 | 17 课 |

## 复现方法

```bash
# 1) EML 解码（需 Python email 模块，见 scripts/decode_eml.py）
python scripts/decode_eml.py

# 2) 音视频转写（需 faster-whisper + 本地模型，见 scripts/transcribe.py）
#    首次运行会自动下载模型；也可指定本地模型路径 WPATH=...
python scripts/transcribe.py "<媒体文件夹>"
```

> 注：转写文本存在 ASR 识别误差（如「脱单」误为「脱民」），提炼知识库时以语义为准，已在各 reference 模块中人工校正。
