# 本地图片处理

> 归属：R10　消费：r14, r12, r08

## 定位

基于 Pillow 的本地图片操作：改尺寸、裁剪、压缩、补边、加水印。

## 我们怎么用

- 命令：`python agent.py imgops info / resize / crop / compress / pad / watermark`
- 确定性技能，规则与门禁已写进代码。

## 规则要点

- 永不覆盖源文件
- 输出格式白名单 png/jpeg/webp
- 像素数上限 40MP
- 缺 Pillow 时返回 blocked，不假装处理
