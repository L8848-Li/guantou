"""方言点种子数据导入脚本。

从结构化源文件（JSON/CSV）读取方言点层级数据，按「名称 + 父级」幂等写入
``Dialect`` 表，供装罐页方言选择器、罐头列表过滤与搜索联想联调使用。

数据约定（与 v1 契约 docs/api/v1/openapi.yaml 的 ``DialectWrite`` 对齐）：

- ``code`` 是同级唯一的短码，默认使用社区熟悉的中文简称，从根到叶拼接成
  限定码（qualified code），例如 ``闽.莆仙.仙游.游洋``。``code`` 不允许
  包含点号、斜杠和空白，长度不超过 32。
- ``key`` 是源文件内的 source key，作为无歧义的父级引用标识；``parent``
  既可以引用同文件内某条记录的 ``key``，也可以引用已落库节点的完整限定码
  （用于断点续跑/增量导入）。
- 唯一性按「父级 + code」校验，允许不同分支下出现相同短码。

用法（在仓库根目录执行，使用后端虚拟环境）::

    backend/guantou/.venv/bin/python -m tools.materials.dialect_seed.seed_dialects \
        --input tools/materials/dialect_seed/dialects.json [--dry-run]

脚本只依赖 Django ORM，通过 ``DJANGO_SETTINGS_MODULE`` 引导后端配置，
不进入 Django app 运行路径。纯数据校验/排序函数不依赖 Django，可直接单测。
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

# 与 guantou.models.Dialect.RegionLevel 保持一致；离线脚本不导入 Django 模型。
REGION_LEVELS = ("family", "dialect", "area", "county", "town", "community")

OPTIONAL_TEXT_FIELDS = ("province", "city", "county", "town", "description")

# 与 v1 契约 DialectWrite.code 的 pattern 一致：不含点号、斜杠和空白。
_CODE_PATTERN = re.compile(r"[./\s]")
_CODE_MAX_LENGTH = 32
_QUALIFIED_SEPARATOR = "."


class SeedError(ValueError):
    """输入文件级别的错误（无法逐条跳过）。"""


class _PlannedNode:
    """dry-run 模式下代替尚未落库节点的占位父级。"""

    def __init__(self, key, qualified_code):
        self.key = key
        self.qualified_code = qualified_code
        self.pk = None


def _clean(value):
    if isinstance(value, str):
        return value.strip()
    return ""


def load_records(path):
    """加载 JSON/CSV 源数据，返回原始记录列表。"""
    source = Path(path)
    if not source.is_file():
        raise SeedError(f"输入文件不存在: {source}")
    suffix = source.suffix.lower()
    if suffix not in (".json", ".csv"):
        raise SeedError(f"仅支持 .json/.csv 输入: {source}")
    try:
        with source.open("r", encoding="utf-8", newline="") as handle:
            if suffix == ".json":
                data = json.load(handle)
            else:
                data = list(csv.DictReader(handle))
    except UnicodeDecodeError as exc:
        raise SeedError(f"输入文件编码异常: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SeedError(f"JSON 解析失败: {exc}") from exc
    if not isinstance(data, list):
        raise SeedError("输入文件顶层必须是记录数组")
    return data


def _normalize(raw):
    """把一条原始记录规范化，返回 (record, reason)。reason 非空表示失败。"""
    if not isinstance(raw, dict):
        return None, "记录必须是对象/行"
    name = _clean(raw.get("name"))
    if not name:
        return None, "缺少名称"
    key = _clean(raw.get("key"))
    if not key:
        return {"name": name}, "缺少 source key"
    if _CODE_PATTERN.search(key):
        return {"name": name}, f"source key 含非法字符: {key}"
    code = _clean(raw.get("code"))
    if not code:
        return {"name": name}, "缺少编码"
    if _CODE_PATTERN.search(code):
        return {"name": name}, f"编码含非法字符（点号/斜杠/空白）: {code}"
    if len(code) > _CODE_MAX_LENGTH:
        return {"name": name}, f"编码超过 {_CODE_MAX_LENGTH} 字符: {code}"
    level = _clean(raw.get("region_level")) or "dialect"
    if level not in REGION_LEVELS:
        return {"name": name}, f"层级取值非法: {level}"
    record = {
        "key": key,
        "code": code,
        "name": name,
        "parent": _clean(raw.get("parent")) or None,
        "region_level": level,
    }
    for field in OPTIONAL_TEXT_FIELDS:
        record[field] = _clean(raw.get(field))
    metadata = raw.get("metadata")
    record["metadata"] = metadata if isinstance(metadata, dict) else {}
    return record, None


def _classify_pending(record, pending, known_qualified):
    """解释拓扑排序后仍无法就绪的记录：缺父级、成环或依赖失败记录。"""
    visited = set()
    current = record
    while True:
        visited.add(current["key"])
        parent = current["parent"]
        if parent is None or parent in known_qualified:
            return "依赖的记录未通过校验"
        parent_record = pending.get(parent)
        if parent_record is None:
            return f"父级不存在: {parent}"
        if parent in visited:
            return "父级引用成环"
        current = parent_record


def validate_records(records, known_parent_qualified=()):
    """校验并拓扑排序记录，返回 ``(有序记录, failed 列表)``。

    - 缺少名称/source key/编码、编码含非法字符、层级取值非法 → failed；
    - source key 在输入内重复 → failed；
    - 同一父级下编码重复、同父级重名 → failed（不同分支允许相同短码）；
    - 父级既不是输入内的 source key，也不在 ``known_parent_qualified``
      （已落库节点的限定码）→ failed；
    - 父级引用成环 → failed，相关记录都不进入有序结果。
    """
    failed = []
    valid = {}
    seen_code_pairs = set()
    seen_name_pairs = set()

    for raw in records:
        record, reason = _normalize(raw)
        if reason:
            failed.append(
                {"name": (record or {}).get("name", str(raw)[:40]), "reason": reason}
            )
            continue
        if record["key"] in valid:
            failed.append(
                {
                    "name": record["name"],
                    "reason": f"source key 在输入内重复: {record['key']}",
                }
            )
            continue
        code_pair = (record["parent"], record["code"])
        if code_pair in seen_code_pairs:
            failed.append(
                {"name": record["name"], "reason": f"同级编码重复: {record['code']}"}
            )
            continue
        seen_code_pairs.add(code_pair)
        name_pair = (record["parent"], record["name"])
        if name_pair in seen_name_pairs:
            failed.append({"name": record["name"], "reason": "同父级下名称重复"})
            continue
        seen_name_pairs.add(name_pair)
        valid[record["key"]] = record

    known_qualified = set(known_parent_qualified)
    ordered = []
    emitted = set()
    pending = dict(valid)
    while pending:
        ready = [
            key
            for key, record in pending.items()
            if record["parent"] is None
            or record["parent"] in known_qualified
            or record["parent"] in emitted
        ]
        if not ready:
            break
        for key in ready:
            ordered.append(pending.pop(key))
            emitted.add(key)

    for record in pending.values():
        failed.append(
            {
                "name": record["name"],
                "reason": _classify_pending(record, pending, known_qualified),
            }
        )
    return ordered, failed


def qualified_codes(ordered):
    """计算有序记录的限定码，返回 ``{key: 从根到叶以点号拼接的 code}``。

    父级若引用外部限定码（已落库节点），直接作为前缀拼接。
    """
    result = {}
    for record in ordered:
        parent = record["parent"]
        if parent is None:
            result[record["key"]] = record["code"]
        elif parent in result:
            result[record["key"]] = f"{result[parent]}.{record['code']}"
        else:
            result[record["key"]] = f"{parent}.{record['code']}"
    return result


def _resolve_qualified_code(dialect_model, qualified, planned_by_qualified):
    """按限定码解析父级：先查本次计划节点，再逐级在库中下钻。"""
    if qualified in planned_by_qualified:
        return planned_by_qualified[qualified]
    current = None
    for segment in qualified.split(_QUALIFIED_SEPARATOR):
        current = dialect_model.objects.filter(parent=current, code=segment).first()
        if current is None:
            return None
    return current


def existing_qualified_codes(dialect_model):
    """收集库中所有节点的限定码，供父级引用校验使用。"""
    nodes = {
        node["id"]: node
        for node in dialect_model.objects.values("id", "parent_id", "code")
    }
    qualified = set()
    for node in nodes.values():
        segments = []
        current = node
        while current is not None:
            segments.append(current["code"])
            current = nodes.get(current["parent_id"])
        qualified.add(_QUALIFIED_SEPARATOR.join(reversed(segments)))
    return qualified


def seed_records(ordered, dialect_model, dry_run=False):
    """把有序记录写入 ``Dialect`` 表，``dry_run`` 只统计不落库。

    dry-run 与真实执行共用同一校验与统计路径，仅最后写入开关不同。
    """
    from django.db import IntegrityError, transaction

    report = {"created": 0, "skipped": 0, "failed": []}
    resolved = {}
    planned_by_qualified = {}
    qualified_by_key = qualified_codes(ordered)

    for record in ordered:
        parent = None
        parent_ref = record["parent"]
        if parent_ref:
            parent = resolved.get(parent_ref)
            if parent is None:
                parent = _resolve_qualified_code(
                    dialect_model, parent_ref, planned_by_qualified
                )
            if parent is None:
                report["failed"].append(
                    {"name": record["name"], "reason": f"父级不存在: {parent_ref}"}
                )
                continue
            if isinstance(parent, _PlannedNode):
                # 父级只在计划中（dry-run 未落库），子级的「名称 + 父级」必然
                # 不存在；但 code 在库级仍受唯一约束，需要与真实写入路径一致
                # 的占用预检，否则 dry-run 会对真实执行必然失败的记录误报
                # created。
                if dialect_model.objects.filter(code=record["code"]).exists():
                    report["failed"].append(
                        {
                            "name": record["name"],
                            "reason": f"编码已被占用: {record['code']}",
                        }
                    )
                    continue
                report["created"] += 1
                planned = _PlannedNode(record["key"], qualified_by_key[record["key"]])
                resolved[record["key"]] = planned
                planned_by_qualified[planned.qualified_code] = planned
                continue

        defaults = {
            "code": record["code"],
            "region_level": record["region_level"],
            "province": record["province"],
            "city": record["city"],
            "county": record["county"],
            "town": record["town"],
            "description": record["description"],
            "metadata": record["metadata"],
        }
        if dry_run:
            existing = dialect_model.objects.filter(
                name=record["name"], parent=parent
            ).first()
            if existing is not None:
                report["skipped"] += 1
                resolved[record["key"]] = existing
                continue
            if dialect_model.objects.filter(code=record["code"]).exists():
                report["failed"].append(
                    {
                        "name": record["name"],
                        "reason": f"编码已被占用: {record['code']}",
                    }
                )
                continue
            report["created"] += 1
            planned = _PlannedNode(record["key"], qualified_by_key[record["key"]])
            resolved[record["key"]] = planned
            planned_by_qualified[planned.qualified_code] = planned
            continue

        try:
            with transaction.atomic():
                obj, created = dialect_model.objects.get_or_create(
                    name=record["name"], parent=parent, defaults=defaults
                )
        except IntegrityError:
            report["failed"].append(
                {"name": record["name"], "reason": f"编码已被占用: {record['code']}"}
            )
            continue
        report["created" if created else "skipped"] += 1
        resolved[record["key"]] = obj
    return report


def _find_repo_root():
    for candidate in [Path(__file__).resolve(), *Path(__file__).resolve().parents]:
        if (candidate / "backend" / "guantou" / "manage.py").is_file():
            return candidate
    raise RuntimeError("找不到仓库根目录（backend/guantou/manage.py），请在仓库内运行")


def setup_django():
    """引导 Django ORM，返回 Dialect 模型。"""
    backend_dir = str(_find_repo_root() / "backend" / "guantou")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from guantou.models import Dialect

    return Dialect


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="方言点种子数据导入（幂等，可断点重跑）"
    )
    parser.add_argument(
        "--input",
        default=str(Path(__file__).resolve().parent / "dialects.json"),
        help="方言点源数据文件（.json/.csv），默认使用随脚本提供的 dialects.json",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印不落库")
    args = parser.parse_args(argv)

    try:
        records = load_records(args.input)
    except SeedError as exc:
        print(f"输入读取失败: {exc}", file=sys.stderr)
        return 2

    dialect_model = setup_django()
    known_qualified = existing_qualified_codes(dialect_model)
    ordered, failed = validate_records(records, known_parent_qualified=known_qualified)
    report = seed_records(ordered, dialect_model, dry_run=args.dry_run)
    report["failed"] = failed + report["failed"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
