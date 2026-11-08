# 取舍与优先级规则（Flutter 跨端原型场景）

1. feature 四层缺一层即 BLOCKER：MVP 也要守住分层，否则没法交 R09 演进。
2. 平台先选 web + 单移动端，不一次铺满 desktop；desktop 仅可编译验证。
3. stateless Widget 必须声明 const_constructor=true，这是可复用组件的底线。
4. 单屏优先可运行：widget_type/const_constructor/breakpoints/form 三件套缺一不可。
5. 原型只管「能不能跑通主流程」，不做动画打磨、不做深色模式、不做多语言。