# 好结论范例

## 好（结构完整、可跑）
"prototype 六结构键齐全，登录 feature 四层分层清晰（data=API 数据源、domain=用例、
presentation=页面、providers=状态管理），platforms=[android,ios,web]。"

## 空泛（需改写）
"待定，先大概搭个 Flutter 壳子。" → 缺六结构键、缺 feature 分层，无法编译验证。

## 替换对照
| 空泛 | 具体 |
|---|---|
| 待定 | main/app/core/features/shared_widgets/router 六键齐 |
| 随便写 | feature.layers 含 data/domain/presentation/providers |
| 后续完善 | platforms 收敛到 android/ios/web/desktop |