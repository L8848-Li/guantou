# 方言点种子数据（dialect_seed）

为 `Dialect` 表提供可重复执行的多层级方言树种子数据，支撑装罐页方言选择器、
罐头列表方言过滤与搜索联想联调。脚本只补数据，不改 `Dialect` 模型与
`DialectSerializer` 输出。

> 目录名用下划线 `dialect_seed` 而非连字符：脚本需要被
> `python -m tools.materials.dialect_seed.seed_dialects` 启动，且纯函数部分要
> 被 `tools/materials/tests/` 以包路径导入，连字符目录两者都不支持。

## 文件

- `dialects.json`：种子源数据，数组形式，父级在前可读性好但非必需。
- `seed_dialects.py`：幂等导入脚本，依赖 Django ORM，不进 Django app 运行路径。

## 数据来源与口径

- 种子树只保留闽语一支：闽 → 莆仙/闽东/闽南 → 各方言点，重点路径精确
  形成限定码 `闽.莆仙.仙游.游洋`。
- 莆仙片（兴化方言）含莆田、仙游两个方言点，参考《莆田市志》方言篇：
  通行于原莆田县境内的称莆田话，通行于仙游县境内的称仙游话。游洋镇隶属
  仙游县，故“游洋”方言点挂在仙游之下。
- 闽东/闽南（含潮汕跨省示例）作为可区分的地方话保留；不再预建吴、粤、
  客家等无实际方言点的大区骨架，也不为填满省/市/县/镇层级而建节点
  （ADR-0001：节点按有证据的实际需求创建，地区名只有代表可区分的地方话
  时才进入方言树）。

## 输入格式

JSON 数组或 CSV（列名同字段名），字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `key` | 是 | source key，文件内唯一，作为无歧义的父级引用标识 |
| `code` | 是 | 同级唯一短码，默认社区熟悉的中文简称（对应 `Dialect.code`）；不允许点号/斜杠/空白，长度 ≤ 32 |
| `name` | 是 | 名称 |
| `parent` | 否 | 同文件内某条记录的 `key`，或已落库节点的完整限定码（断点续跑/增量导入）；空表示根节点 |
| `region_level` | 否 | `family/dialect/area/county/town/community`，缺省 `dialect` |
| `province/city/county/town/description` | 否 | 文本字段 |
| `metadata` | 否 | JSON 对象（仅 JSON 输入） |

限定码（qualified code）从根到叶以点号拼接，如 `闽.莆仙.仙游.游洋`，
与 v1 契约（`docs/api/v1/openapi.yaml` 的 `DialectWrite`、ADR-0001）一致：
`code` 同级唯一，不同分支允许相同短码。

## 运行方式

在仓库根目录执行，使用后端虚拟环境（脚本自动引导 `DJANGO_SETTINGS_MODULE=config.settings`）：

```bash
# 只打印不落库
backend/guantou/.venv/bin/python -m tools.materials.dialect_seed.seed_dialects --dry-run

# 真实写入（默认输入即本目录 dialects.json，可用 --input 指定其他文件）
backend/guantou/.venv/bin/python -m tools.materials.dialect_seed.seed_dialects --input tools/materials/dialect_seed/dialects.json
```

环境变量：默认读写 `backend/guantou/db.sqlite3`；如需指向其他库，设置
`SQLITE_PATH`（见 `.env.example`）。

## 输出报告

stdout 输出 JSON：`{created: n, skipped: n, failed: [{name, reason}]}`。

- `created`：新建记录数；`skipped`：按「名称 + 父级」命中已有记录数。
- `failed`：脏数据逐条记录并跳过，不中断整体（缺名称/source key/编码、
  编码含非法字符、层级取值非法、source key 重复、同级编码重复、同父级重名、
  父级不存在、父级成环、编码被已有行占用）。
- 退出码：`0` 无失败；`1` 存在 failed；`2` 输入文件本身不可读/不可解析。

> 当前 `Dialect.code` 在库级仍是全局唯一约束（历史模型），比 v1 的「同级
> 唯一」更严；脚本按 v1 规则校验，写入时若触发库级全局冲突会如实记入
> failed，dry-run 与真实执行报告保持一致。模型约束对齐 v1 另行跟进。

## 幂等与断点重跑

按「名称 + 父级」`get_or_create`，重复执行只会 `skipped`，不产生重复数据；
中断后直接重跑即可，无需状态文件。增量导入时 `parent` 可写已落库节点的
完整限定码（如 `闽.莆仙.仙游`）。`--dry-run` 与真实执行共用同一校验与统计
代码路径，仅最后写入开关不同。

## 与 v1 契约的关系

PR #121 合入后，`docs/api/v1/openapi.yaml` 是权威契约：`code` 同级唯一、
中文短码、限定码从根到叶拼接；`GET /dialects/` 使用分页信封，省略
`parent_id` 返回根节点，传入 `parent_id` 返回直接子节点。本目录的数据与
校验规则按该契约编写；脚本只补数据，不改 `Dialect` 模型与
`DialectSerializer` 输出。

## 测试

纯校验/排序/加载逻辑不依赖 Django；另有一组基于临时 SQLite 的 ORM 测试
（验证 dry-run 与真实执行报告一致、限定码父级解析），Django 不可用时自动跳过：

```bash
python -m unittest discover tools/materials/tests
# 或
make materials-check
```
