---
version: alpha
name: GuanTou-XiangShengJiHe-design
description: 乡声集盒（GuanTou）uni-app 跨端设计系统。以品牌深绿 #1f5c43 为核心的自然、乡土气质；浅色/暗色双主题 + 首页沉浸式深绿场景三套颜色 Token；rpx 自适应无断点布局；宋体/楷体文化字形用于方言展示。唯一颜色来源为 frontend/src/styles/tokens.scss，禁止组件内新增 hex 字面量。

colors:
  # 与 tokens.scss 的 light/dark-color-tokens 一一对应；组件消费 CSS 变量，
  # 暗色自动翻转，frontmatter 同时编码两套供机器消费。
  light:
    page: "#f6f7f3"
    surface: "#ffffff"
    surface-subtle: "#f2f4ef"
    text: "#1d2a24"
    text-secondary: "#425148"
    muted: "#647068"
    border: "#e1e6dc"
    accent: "#1f5c43"
    accent-subtle: "#e8f1eb"
    on-accent: "#ffffff"
    danger: "#d54941"
    danger-subtle: "#fff1ed"
    on-danger: "#ffffff"
    warning: "#ed7b2f"
    success: "#2ba471"
  dark:
    page: "#121915"
    surface: "#1d2822"
    surface-subtle: "#26312b"
    text: "#edf4ef"
    text-secondary: "#c3d1c7"
    muted: "#a9b8ae"
    border: "#34443a"
    accent: "#69b58b"
    accent-subtle: "#24402f"
    on-accent: "#10201a"
    danger: "#fb8f86"
    danger-subtle: "#46282a"
    on-danger: "#2b1010"
    warning: "#f5a56c"
    success: "#5fce9f"
  # 固定深色，不随明暗主题翻转，仅 .immersive-shell 子树消费
  immersive:
    bg: "#0a1410"
    bg-soft: "#13261d"
    bg-strong: "#1f5c43"
    glow: "rgba(105, 181, 139, 0.28)"
    veil: "rgba(6, 13, 10, 0.44)"
    # 键名加引号：裸 on 会被 YAML 解析为布尔值，机器消费方需按字符串 "on" 读取
    "on": "#eef6f0"
    on-muted: "rgba(226, 238, 230, 0.64)"
    on-faint: "rgba(226, 238, 230, 0.36)"
    icon: "#f1f7f2"
    surface: "rgba(238, 246, 240, 0.09)"
    surface-strong: "rgba(238, 246, 240, 0.18)"
    border: "rgba(238, 246, 240, 0.16)"
    accent: "#8fd6ac"
    wave: "rgba(238, 246, 240, 0.3)"
    wave-active: "#9fe0bd"
    skeleton: "rgba(238, 246, 240, 0.08)"
    skeleton-highlight: "rgba(238, 246, 240, 0.18)"

typography:
  display-lg:
    fontFamily: "'STSong', 'SimSun', serif"
    fontSize: 76rpx
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: 0px
  display-dialect:
    fontFamily: "'STKaiti', 'KaiTi', serif"
    fontSize: 46rpx
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: 0px
  heading-md:
    fontFamily: "system-ui, -apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
    fontSize: 36rpx
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: 0px
  heading-sm:
    fontFamily: "system-ui, -apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
    fontSize: 32rpx
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0px
  body-md:
    fontFamily: "system-ui, -apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
    fontSize: 28rpx
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: 0px
  body-sm:
    fontFamily: "system-ui, -apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
    fontSize: 26rpx
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0px
  caption:
    fontFamily: "system-ui, -apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
    fontSize: 24rpx
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0px
  button-md:
    fontFamily: "system-ui, -apple-system, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
    fontSize: 28rpx
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: 0px

rounded:
  none: 0px
  sm: 8rpx
  md: 14rpx
  lg: 20rpx
  pill: 999rpx

spacing:
  xs: 8rpx
  sm: 16rpx
  md: 24rpx
  lg: 32rpx
  xl: 48rpx

components:
  # 组件契约以浅色主题为基准编码；暗色经同名语义 Token 自动翻转，
  # 沉浸式组件固定消费 immersive 组。
  button-primary:
    backgroundColor: "{colors.light.accent}"
    textColor: "{colors.light.on-accent}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
  button-primary-disabled:
    backgroundColor: "{colors.light.surface-subtle}"
    textColor: "{colors.light.muted}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
  button-ghost:
    backgroundColor: "{colors.light.surface}"
    textColor: "{colors.light.accent}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
  button-danger:
    backgroundColor: "{colors.light.danger}"
    textColor: "{colors.light.on-danger}"
    typography: "{typography.button-md}"
    rounded: "{rounded.pill}"
  text-input:
    backgroundColor: "{colors.light.surface}"
    textColor: "{colors.light.text}"
    typography: "{typography.body-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm}"
  card-can:
    backgroundColor: "{colors.light.surface}"
    textColor: "{colors.light.text}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  card-entity:
    backgroundColor: "{colors.light.surface}"
    textColor: "{colors.light.text}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  section-block:
    backgroundColor: "{colors.light.surface}"
    textColor: "{colors.light.text}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  chip-accent:
    backgroundColor: "{colors.light.accent-subtle}"
    textColor: "{colors.light.accent}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
  chip-danger:
    backgroundColor: "{colors.light.danger-subtle}"
    textColor: "{colors.light.danger}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
  dialog-confirm:
    backgroundColor: "{colors.light.surface}"
    textColor: "{colors.light.text}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
  immersive-can-card:
    backgroundColor: "{colors.immersive.bg}"
    textColor: "{colors.immersive.on}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
  immersive-action-icon:
    backgroundColor: "{colors.immersive.surface}"
    textColor: "{colors.immersive.on}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
  tabbar-home:
    backgroundColor: "{colors.immersive.bg}"
    textColor: "{colors.immersive.on}"
    typography: "{typography.caption}"
---

# DESIGN.md — 乡声集盒（GuanTou）设计契约

> 由 Design Review 插件 `design-system-capture` 流程从现有代码采集生成（write 模式）。
> 来源：`frontend/src/styles/tokens.scss`（权威）、组件源码（`components/`、`components/home/`）、M1 设计系统实施记录。置信度标注见各节。

## Overview

乡声集盒是一款方言文化记录与社交应用（H5 / 微信小程序 / App 三端，uni-app Vue3）。产品气质：**自然、乡土、沉静** —— 品牌深绿 `{colors.light.accent}`（#1f5c43）为中心，米白页面底 `{colors.light.page}`，宋体/楷体文化字形承载方言文本展示。

三条核心约束：

1. **Token 唯一来源**：全站颜色/间距/圆角/字号只来自 `tokens.scss`，页面与组件禁止新增 hex 字面量（`confirmed`，tokens.scss 文件头注释明文约束）。
2. **双主题 + 沉浸隔离**：浅色默认、暗色仅覆盖颜色类 Token；首页沉浸罐头流使用固定深色的 `--immersive-*` 系列，仅在 `.immersive-shell` 子树内消费，不随明暗主题翻转。
3. **rpx 自适应**：尺寸统一使用 rpx（750rpx = 屏宽），无媒体查询断点。

## Colors

颜色分三组，均以 CSS 变量形式定义于 `tokens.scss`：

**主题色（随明暗翻转，浅色为默认 / `confirmed`）：**

| 角色 | Token | 浅色 | 暗色 |
| --- | --- | --- | --- |
| 页面底 | `--page-color` / `{colors.light.page}` | #f6f7f3 | #121915 |
| 浮层/卡片 | `--surface-color` / `{colors.light.surface}` | #ffffff | #1d2822 |
| 弱底色 | `--surface-subtle-color` / `{colors.light.surface-subtle}` | #f2f4ef | #26312b |
| 正文 | `--text-color` / `{colors.light.text}` | #1d2a24 | #edf4ef |
| 次要正文 | `--text-secondary-color` / `{colors.light.text-secondary}` | #425148 | #c3d1c7 |
| 辅助文字 | `--muted-color` / `{colors.light.muted}` | #647068 | #a9b8ae |
| 描边 | `--border-color` / `{colors.light.border}` | #e1e6dc | #34443a |
| 品牌强调 | `--accent-color` / `{colors.light.accent}` | #1f5c43 | #69b58b |
| 强调浅底 | `--accent-subtle-color` / `{colors.light.accent-subtle}` | #e8f1eb | #24402f |
| 危险/警告/成功 | `--danger/--warning/--success-color` | #d54941 / #ed7b2f / #2ba471 | #fb8f86 / #f5a56c / #5fce9f |

主行动按钮、链接、选中态使用 `{colors.light.accent}`；危险实心按钮文字用 `{colors.light.on-danger}`；徽章用 `{colors.light.accent-subtle}` 浅底。

**沉浸式色（固定深色，仅 `.immersive-shell` 子树 / `confirmed`）：** 三档深绿渐变底（`--immersive-bg-color` #0a1410 / `--immersive-bg-soft-color` / `--immersive-bg-strong-color` 复用品牌深绿）、深底文字三档（`--on-immersive-color` / muted / faint）、玻璃表面与描边（`--immersive-surface-*`、`--immersive-border-color`）、深底强调 `{colors.immersive.accent}`（#8fd6ac）与波形色。

**TDesign 品牌映射（`confirmed`）：** `--td-brand-color-1..10` 以 #1f5c43 为 6 档构建深绿梯度，`--td-primary/error/warning/success-color-6` 指向项目语义 Token，保证 `t-*` 组件与全站一致。

暗色切换机制：H5 由 `services/theme.js` 写 `html[data-theme='dark']`，组件级用 `.theme-dark` 类；支持 `system/light/dark` 三种偏好，持久化于 `ui_theme`。

## Typography

字号阶梯为静态 Token（不随主题翻转）：`--font-size-xs..xl` = 24/26/28/32/36rpx，对应 `{typography.caption}` ~ `{typography.heading-md}`，正文基准 `{typography.body-md}`（28rpx）。

字形分三类（`likely`，由各页面重复用法归纳）：

- **宋体** `'STSong', 'SimSun', serif`：品牌名、登录页标题等文化展示（`{typography.display-lg}` 一族）。
- **楷体** `'STKaiti', 'KaiTi', serif`：方言词条、铭牌大字展示（`{typography.display-dialect}`）。
- **系统无衬线**：所有正文、控件、说明文字。

字形家族目前未收敛为 Token，属于 `needs-design-decision`（见 Known Gaps）。

## Layout

间距为 8rpx 基数五档：`--space-1..5` = 8/16/24/32/48rpx，对应 `{spacing.xs}` ~ `{spacing.xl}`。卡片内边距普遍使用 `{spacing.md}`（24rpx），区块之间使用 `{spacing.md}` ~ `{spacing.lg}`。布局依赖 flex/grid + rpx 自适应，不使用容器宽度断点。

## Elevation & Depth

产品以**描边 + 底色分层**为主，几乎不使用阴影：卡片用 `{colors.light.border}` 1rpx 描边叠加 `{colors.light.surface}` 与页面底 `{colors.light.page}` 的明度差。沉浸场景用玻璃表面（半透明白 9%~18%）与氛围光 `box-shadow: 0 0 12rpx var(--immersive-glow-color)` 表达深度。遮罩统一走 `--uni-bg-color-mask`（rgba(0,0,0,0.4)）。

## Shapes

圆角四档（`confirmed`）：`{rounded.sm}` 8rpx（输入框内件、小标签）、`{rounded.md}` 14rpx（输入框）、`{rounded.lg}` 20rpx（卡片、弹层）、`{rounded.pill}` 999rpx（按钮、胶囊徽章、头像）。按钮统一胶囊形（BaseButton 设置 `--td-button-border-radius: var(--radius-pill)`）。

## Components

| 组件 | 前端实现 | 契约 Token | 说明 |
| --- | --- | --- | --- |
| 按钮 | `BaseButton.vue`（封装 `t-button`） | `{components.button-primary}` / `-ghost` / `-danger` / `-disabled` | variants: primary/ghost/danger/danger-ghost/light；sizes: extra-small~large；shape 默认 round；disabled/loading 由 TDesign 状态承接 |
| 输入 | `BaseField.vue`（封装 `t-input`） | `{components.text-input}` | focus 态由 TDesign `--td-*` 品牌色承接 |
| 确认弹层 | `ConfirmDialog.js` | `{components.dialog-confirm}` | 危险确认色使用 danger 语义 |
| 罐头卡片 | `CanCard.vue` | `{components.card-can}` | 列表态；首页沉浸态为 `{components.immersive-can-card}`（`CanStageCard.vue`） |
| 实体卡片 | `EntityCard.vue` / `NameplateCard.vue` | `{components.card-entity}` | 词条/铭牌展示，含楷体大字 |
| 区块容器 | `SectionBlock.vue` | `{components.section-block}` | 页面分区白卡 |
| 徽章/标签 | 各组件内 | `{components.chip-accent}` / `{components.chip-danger}` | 浅底 + 语义色文字胶囊 |
| 首页沉浸组件族 | `components/home/`（HomeTopBar/CanStageCard/NameplateVoteRow/HomeActionRail/HomeTabBar/HomeFeed/AudioWave） | `{components.immersive-can-card}` / `{components.immersive-action-icon}` / `{components.tabbar-home}` | 只消费 `--immersive-*` / `--on-immersive-*` |
| 主题切换 | `ThemeSwitcher.vue` | — | system/light/dark 三态 |
| 第三方业务组件 | `@tdesign/uniapp`（picker/popup/toast 等） | — | 手动导入（小程序端 easycom 对 npm 包失效） |

交互状态要求：按钮需覆盖 default / disabled / loading（TDesign 内建）；focus-visible 在 H5 端保持可见；空态统一走 `EmptyState.vue`，加载态走 `BaseLoading.vue`。

## Do's and Don'ts

Do:

- 颜色一律 `var(--*)` / Token 取值，新增颜色先入 `tokens.scss`。
- 按钮/输入/弹层优先复用 `BaseButton` / `BaseField` / `ConfirmDialog` 原语。
- 沉浸场景新代码只用 `--immersive-*` / `--on-immersive-*`。
- 图标与动画：新建/迁移 UI 禁止新增 `cu-*` 类（AGENTS.md 约束，遗留用法见 Known Gaps）；动画允许组件作用域 `@keyframes`（如 `immersive-shimmer`、`action-rail-enter`），须支持 `prefers-reduced-motion` 降级；图标优先 TDesign 图标或文字图形。
- TDesign 组件必须经品牌映射消费（勿覆盖回默认蓝）。

Don't:

- 禁止在页面/组件新增 hex 颜色字面量（含行内样式）。
- 禁止在 `.immersive-shell` 之外消费沉浸式 Token。
- 禁止让字号/间距/圆角随主题翻转（只有颜色类 Token 可覆盖）。
- 禁止绕过原语直接使用原生 button/input 写死样式。
- 禁止引入新 npm UI 组件前验证小程序端兼容性（easycom 已知失效）。

## Responsive Behavior

- 单位统一 rpx（750rpx = 屏宽），无媒体查询断点，无桌面布局。
- 布局靠 flex/grid 弹性收缩；长文本允许换行不截断为原则，列表滚动区固定一屏。
- 首页为一屏一罐的垂直 swiper（数据滑动窗口 ±2），触控目标不小于 88rpx。
- H5 验证统一使用 iPhone 手机尺寸视口（项目测试规范）。

## Known Gaps

- `needs-design-decision`：**字形 Token 化** —— 宋体/楷体家族在多个页面重复硬编码（`pages/nameplates/*`、`pages/cans/details.vue`、`login.vue`、`AppShell.vue` 等），建议新增 `--font-family-display-song/kai` Token。
- `design-debt`：**存量硬编码色** —— `SearchPanel.vue`（#f6f7f3/#1d2a24/#1f5c43 等 10+ 处）、`CanDraftList.vue`（含 `confirmColor: '#9b3a2d'`，该色不在 Token 体系内）仍使用 hex 字面量，其中多数值与浅色 Token 重合，应替换为 `var(--*)`。
- `design-debt`：**ColorUI 遗留样式** —— `colorui/main.css` 等含大量硬编码色与 `upx` 单位；新建/迁移 UI 已禁止新增 `cu-*` 类（见 AGENTS.md），存量 13 个页面仍依赖 `cu-*` 类（含 `cuIcon-*` 图标），计划于 M3/M4 页面迁移完成后清理。
- `conflict`：**uni.scss 默认值** —— `$uni-color-primary: #007aff` 与品牌深绿冲突；仅为三方插件兼容保留，业务代码不得引用。
- `tentative`：**字号上限** —— `--font-size-xl`(36rpx) 不足以覆盖展示型大字（44~76rpx 目前页面内硬编码），展示型字号策略待定。
- `u-parse.css` 为第三方 Markdown 渲染遗留样式，独立于主样式体系，不在本契约管辖内。
