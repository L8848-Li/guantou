# 前端 UI 整体优化：多人并行合作拆解方案

> 日期：2026-08-11 · 范围：`frontend/src/` · 目标：统一视觉语言、提升组件复用、按模块拆分给多人并行开发

## 1. 现状分析

### 1.1 页面规模与模块划分

`frontend/src/pages/` 共 **38 个页面**，按业务域可划分为：

| 业务域 | 页面 | 数量 |
| --- | --- | --- |
| 首页/搜索 | `index.vue`、`search.vue` | 2 |
| 罐头 | `cans/index`、`create`、`drafts`、`library`、`details`、`comments` | 6 |
| 义项/写法/读音 | `flavors/*`(2)、`packages/*`(2)、`pronunciations/create` | 5 |
| 集盒 | `shelves/index`、`details` | 2 |
| 发现/方言圈/动态 | `discovery/index`、`circles/*`(2)、`posts/*`(2) | 5 |
| 用户/账户 | `users/me`、`details`、`onboarding`、`recommend-follow`、`settings/*`(6) | 10 |
| 私信 | `mails/*`(3) | 3 |
| 登录/错误 | `login/*`(4)、`error/not-found` | 5 |

`pages.json` 使用全自定义导航（`navigationStyle: custom`），无 tabBar，导航体验完全依赖 `PageShell` 顶栏。

### 1.2 组件复用现状

`frontend/src/components/` 已有 **15 个公共组件**：

- 页面骨架：`PageShell`（顶栏 + 主题 + 滚动容器，**22/38 页面已接入**）。
- 结构件：`SectionBlock`（自带 `EmptyState` 空态）、`EmptyState`、`ResultSection`。
- 业务卡片：`CanCard`、`CanList`、`CanDraftList`、`EntityCard`、`NameplateCard`。
- 业务容器：`NameplateComposer`、`SearchPanel`、`SocialCanFeeds`、`AudioCapture`、`MarkdownViewer`、`ThemeSwitcher`。

复用基础是好的：`PageShell` + `SectionBlock` + 卡片组件的三层结构已经成型，新页面有可照抄的范式（见 `docs/FRONTEND_GUIDE.md`）。

### 1.3 核心问题（本次优化要解决的）

1. **Design Token 只存在一半**。`PageShell` 内定义了 6 个 CSS 变量（`--page-color/--surface-color/--text-color/--muted-color/--border-color/--accent-color`）及暗色覆盖，但这套变量：
   - 没有全局化——`users/me.vue` 自己重复定义了一套相同变量；
   - 连公共组件都没接入——`SectionBlock` 仍硬编码 `#ffffff`、`#e1e6dc`、`#1f5c43`；
   - 页面层面 **26 个文件、约 327 处硬编码 hex 颜色**，暗色模式下大面积失效。
2. **16 个页面未接入 PageShell**（`search`、`users/me`、`users/details`、`settings/*`、`login/*`、`mails/details`、`mails/send`、`error/not-found`），顶栏、返回、主题行为各自实现，风格不一致。
3. **缺少表单/按钮/确认弹窗等基础原语**。各页面自写 `.primary-button`、`.field`、`.small-button`，样式重复且参数不一（对比 `shelves/details.vue` 与其它表单页）。
4. **旧 ColorUI（`src/colorui/`）与新体系并存**，部分页面仍依赖旧样式类，是风格割裂的历史来源。
5. 主题机制已具备（`services/theme.js` + `uni.$emit('theme-change')`），但收益被上述硬编码抵消。

## 2. 任务拆解（4 个模块）

> 依赖关系：**M1 是地基，先出 Token 与组件改造；M2/M3/M4 按页面目录划分、互不重叠，可三人并行**。每个模块一个 GitHub Issue（骨架可分多个 PR 交付，遵循 `docs/CONTRIBUTOR_ONBOARDING.md` 原则 3）。

### M1 设计系统与公共组件统一（地基模块，1 人主导）

**优化目标**：建立唯一 Token 来源，公共组件全部 Token 化，沉淀基础原语。

涉及文件：

- 新增 `frontend/src/styles/tokens.scss`（或 CSS 变量文件）：把 `PageShell` 的 6 个变量升级为全局 Token，扩展语义色（danger/warning/success）、间距档位、圆角、字号阶梯；明暗双套。
- `App.vue` 全局注入 Token；`PageShell` 改为消费全局变量而非自定义。
- 公共组件 Token 化：`SectionBlock`、`EmptyState`、`CanCard`、`EntityCard`、`NameplateCard`、`ThemeSwitcher`。
- 新增基础原语：`BaseButton`（primary/ghost/danger 变体）、`BaseField`（输入框/文本域）、`ConfirmDialog`（统一 `uni.showModal` 封装，供删除类危险操作复用）。
- 产出《UI 规范速查》文档（放入 `docs/FRONTEND_GUIDE.md` 新章节）：颜色/间距/圆角/按钮/卡片使用约定。

**完成标准**：暗色模式下公共组件零硬编码颜色；其他模块可只靠 Token + 原语写页面。

### M2 核心浏览模块（百科线，1 人）

**优化目标**：浏览类页面统一卡片节奏、列表状态（loading/empty/error/data）与搜索体验。

涉及页面（12 个）：

- `pages/index.vue`（首页）、`pages/search.vue`（搜索，需接入 PageShell）
- `pages/cans/index`、`library`、`details`、`comments`
- `pages/flavors/index`、`details`
- `pages/packages/index`、`details`
- `pages/shelves/index`、`details`

工作内容：硬编码颜色替换为 Token；卡片间距/层级统一；列表空态统一走 `EmptyState`；详情页信息层级（标题 → 主体 → 关联列表 → 操作）按 FRONTEND_GUIDE 对齐。

### M3 创作与账户模块（1 人）

**优化目标**：表单体验统一（校验、提交中、成功跳转、失败反馈），账户区页面全部接入 PageShell。

涉及页面（19 个）：

- 创作：`cans/create`、`cans/drafts`、`pronunciations/create`、`posts/compose`、`mails/send`
- 账户：`users/me`、`users/details`、`users/onboarding`、`users/recommend-follow`、`users/settings/*`(6)
- 登录：`login/login`、`register`、`register/wechat`、`forget`

工作内容：接入 M1 的 `BaseButton`/`BaseField`；`users/me.vue` 删除私有变量改吃全局 Token；`settings/*` 与 `login/*` 接入 PageShell；表单错误提示统一从 `data.<field>` 取（见 FRONTEND_GUIDE 用户反馈约定）。

### M4 社交与发现模块（1 人）

**优化目标**：Feed 流、圈子、私信的信息密度与交互一致性。

涉及页面（7 个）+ 组件：

- `pages/discovery/index`、`circles/index`、`circles/details`、`posts/details`、`mails/index`、`mails/details`、`error/not-found`
- 组件消费方视角验收 `SocialCanFeeds`、`MarkdownViewer`（组件本体改动归 M1，M4 只提需求/验收）。

工作内容：Feed 卡片与详情页节奏统一；私信收发状态可视化；`error/not-found` 空态风格归一。

## 3. 多人协作机制

### 3.1 角色与分工

| 角色 | 职责 | 约束 |
| --- | --- | --- |
| M1 负责人（设计系统 Owner） | Token、公共组件、基础原语、UI 规范文档 | **唯一有权修改 `components/` 与全局样式的人** |
| M2/M3/M4 负责人 | 各自页面目录内的 UI 改造 | 不改 `components/`、不改其他模块目录；需要组件改动时向 M1 提需求 |
| 维护者/评审人 | 走查验收、合并把关 | 每个 PR 至少一人 review；M1 的 Token PR 需全员过目 |

### 3.2 设计一致性保障

1. **Token 先行**：M1 第一个 PR 只交付 Token 文件 + PageShell 接入（小而快），其余模块即可引用；避免其他人等全量改造。
2. **禁硬编码规则**：新代码禁止新增 hex 颜色字面量，可用 `yarn lint`（自定义规则或 grep 检查 `#[0-9a-fA-F]{6}`）在 CI/PR 模板里把关。
3. **原语优先**：按钮、输入框、确认弹窗一律用 M1 原语；页面样式只允许写布局（flex/grid/间距），不写颜色圆角。
4. **规范文档即合同**：UI 规范章节合入 `docs/FRONTEND_GUIDE.md`，PR 描述中声明"已对照规范自查"。
5. **主题双查**：任何 UI PR 必须附浅色 + 暗色两张截图（H5 即可）。

### 3.3 依赖与合并策略

**阶段划分**：

```text
阶段 0（并行启动）：
  M1 → Token + PageShell 接入（PR#1，阻塞项，最先合并）
  M2/M3/M4 → 各自页面状态逻辑梳理、PageShell 接入（不涉及颜色的改动，先跑起来）

阶段 1（M1 PR#1 合并后）：
  M1 → 公共组件 Token 化 + 原语组件（PR#2）
  M2/M3/M4 → 页面颜色/间距 Token 替换（各自独立 PR）

阶段 2（收尾）：
  M1 → 清理 colorui 残留依赖（需各模块确认页面已无旧样式类）
  全员 → 交叉走查
```

**Git 协作建议**（遵循仓库 Fork + PR 规范）：

- 分支命名：`feat/ui-tokens`、`feat/ui-browse`、`feat/ui-create-account`、`feat/ui-social`。
- 提交格式：`refactor(frontend): ...` / `feat(frontend): ...`，scope 可用模块名如 `refactor(ui-tokens)`。
- **按目录划界防冲突**：每个 PR 只触碰自己模块的 `pages/<目录>` 文件；触碰公共文件的 PR 只允许出自 M1。
- **高频 rebase**：各模块每天 rebase 一次 main（或 upstream），冲突当天解决，不留大合并。
- **小 PR 快合**：单 PR 不超过 ~10 个页面文件；大模块拆多个 PR（例如 M3 拆"创作表单""账户设置""登录"三个 PR），符合 onboarding 文档"小 PR 更有价值"的原则。
- `services/`、`utils/` 层本阶段原则上不动；确需改动（如新增删除接口）单独提 PR 并说明。

## 4. 验收标准与走查流程

### 4.1 机器检查（每个 PR 必须）

```bash
cd frontend
yarn lint
yarn test:unit
yarn build            # H5
yarn build:mp-weixin  # 小程序
```

另附硬编码检查：`grep -rnE "#[0-9a-fA-F]{6}" src/pages src/components` 结果不新增（对比 main）。

### 4.2 人工走查清单（模块完成后）

- [ ] 浅色 / 暗色两种主题下逐页截图对比，无白块、无不可读文字。
- [ ] H5 与微信小程序双端各走一遍核心路径（首页 → 搜索 → 罐头详情 → 装罐 → 集盒）。
- [ ] 四类状态齐备：每个列表/详情页可人工构造 loading、空态、错误、正常四种场景。
- [ ] 文案符合业务词约定（罐头/铭牌/义项/写法/集盒），无旧词典 `word/pronunciation` 措辞残留。
- [ ] 交互反馈：按钮提交中有禁用态；危险操作有二次确认；成功/失败均有可见反馈。

### 4.3 验收流程

1. 模块负责人自查后发 PR，附：改动页面清单、浅色/暗色截图、手测路径（按 `CONTRIBUTOR_ONBOARDING.md` PR 模板的 Summary/Scope/Test Plan/Notes 四段）。
2. 交叉 review：M2/M3/M4 互审对方 PR（保证至少一双"模块外眼睛"），M1 的 PR 由其余三人共同 review。
3. 全部模块合并后，维护者组织一次**整体走查会**：按 4.2 清单逐页过一遍，记录遗留项开新 Issue（不与本轮混合）。
4. 走查通过后，更新 `docs/FRONTEND_GUIDE.md` 的 UI 规范章节为长期约束，防止后续贡献再次引入硬编码。
