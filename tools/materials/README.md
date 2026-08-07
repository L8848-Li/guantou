# 方言材料处理工具

本目录只放离线材料处理脚本，不属于 Django 后端运行路径。

## 目录边界

- `common/`：跨方言可复用的小工具，例如文本清洗、字段标准化、CSV/XLSX/JSON 辅助。
- `puxian/`：莆仙话专属处理逻辑，例如莆仙话拼音、IPA、声母韵母声调拆分。
- `puxian/legacy/`：旧莆仙词典 Excel/音频批处理脚本，只作为历史材料处理参考。
- `dialect_seed/`：方言点（`Dialect`）种子数据与幂等导入脚本，见目录内 README。
- `tests/`：可稳定运行的纯函数测试。legacy 脚本没有 fixture 时不进入 CI。

## 运行测试

```bash
python -m unittest discover tools/materials/tests
```

## legacy 脚本规则

`legacy/` 中的脚本通常依赖固定文件名、固定 Excel 列号或人工后处理步骤。保留它们是为了后续清洗旧材料时可追溯，不表示它们可直接用于新材料。

如果要把某个 legacy 脚本升级为正式工具，应先完成：

- 把硬编码输入输出改成命令行参数。
- 写清输入列、输出文件和适用方言。
- 把方言专属规则放到对应地域模块。
- 给核心转换逻辑补测试。

可运行 legacy 脚本需要单独安装依赖：

```bash
python -m pip install -r tools/materials/requirements.txt
```
