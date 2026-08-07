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

- 闽语分为闽南、闽东、莆仙、闽北、闽中诸片的框架，参考中国社会科学院语言
  研究所等编《中国语言地图集》的汉语方言分区。
- 兴化方言（莆仙闽语）分莆田、仙游两片，参考《莆田市志》方言篇：通行于原
  莆田县境内的称莆田话，通行于仙游县境内的称仙游话，合称莆仙方言（兴化
  方言）。游洋镇隶属仙游县，故“游洋”方言点挂在仙游之下。
- 其余（吴、粤、客家、湘、赣、晋、徽、官话）仅为骨架节点，不追求学术级
  完整的全国分区，首期够联调即可。若与后续学术口径冲突，以数据文件为准修订。

## 输入格式

JSON 数组或 CSV（列名同字段名），字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `code` | 是 | 稳定编码（对应 `Dialect.code`，全局唯一），作为父级引用标识 |
| `name` | 是 | 名称 |
| `parent` | 否 | 父级 `code`；空表示根节点 |
| `region_level` | 否 | `family/dialect/area/county/town/community`，缺省 `dialect` |
| `province/city/county/town/description` | 否 | 文本字段 |
| `metadata` | 否 | JSON 对象（仅 JSON 输入） |

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
- `failed`：脏数据逐条记录并跳过，不中断整体（缺名称/编码、层级取值非法、
  输入内编码重复、同父级重名、父级不存在、父级成环、编码被已有行占用）。
- 退出码：`0` 无失败；`1` 存在 failed；`2` 输入文件本身不可读/不可解析。

## 幂等与断点重跑

按「名称 + 父级」`get_or_create`，重复执行只会 `skipped`，不产生重复数据；
中断后直接重跑即可，无需状态文件。`--dry-run` 与真实执行共用同一校验与统计
代码路径，仅最后写入开关不同。

## 与 ADR-0001（PR #121）的关系

种子数据按现有 parent/child 树模型编写；方言树数据本身不因表示方式而废。
若「惰性展开关系树」方案合入，仅需调整导入目标表/字段，数据文件可复用。

## 测试

纯校验/排序/加载逻辑不依赖 Django：

```bash
python -m unittest discover tools/materials/tests
# 或
make materials-check
```
