"""方言点种子数据导入脚本。

从结构化源文件（JSON/CSV）读取方言点层级数据，按「名称 + 父级」幂等写入
``Dialect`` 表，供装罐页方言选择器、罐头列表过滤与搜索联想联调使用。

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
import sys
from pathlib import Path

# 与 guantou.models.Dialect.RegionLevel 保持一致；离线脚本不导入 Django 模型。
REGION_LEVELS = ("family", "dialect", "area", "county", "town", "community")

OPTIONAL_TEXT_FIELDS = ("province", "city", "county", "town", "description")


class SeedError(ValueError):
    """输入文件级别的错误（无法逐条跳过）。"""


class _PlannedNode:
    """dry-run 模式下代替尚未落库节点的占位父级。"""

    def __init__(self, code):
        self.code = code
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
    code = _clean(raw.get("code"))
    if not name:
        return None, "缺少名称"
    if not code:
        return {"name": name}, "缺少编码"
    level = _clean(raw.get("region_level")) or "dialect"
    if level not in REGION_LEVELS:
        return {"name": name}, f"层级取值非法: {level}"
    record = {
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


def _classify_pending(record, pending, known):
    """解释拓扑排序后仍无法就绪的记录：缺父级、成环或依赖失败记录。"""
    visited = set()
    current = record
    while True:
        visited.add(current["code"])
        parent = current["parent"]
        if parent is None or parent in known:
            return "依赖的记录未通过校验"
        parent_record = pending.get(parent)
        if parent_record is None:
            return f"父级不存在: {parent}"
        if parent in visited:
            return "父级引用成环"
        current = parent_record


def validate_records(records, known_parent_codes=()):
    """校验并拓扑排序记录，返回 ``(有序记录, failed 列表)``。

    - 缺少名称/编码、层级取值非法、编码重复、同父级重名 → failed；
    - 父级既不在输入内也不在 ``known_parent_codes``（已落库编码）→ failed；
    - 父级引用成环 → failed，相关记录都不进入有序结果。
    """
    failed = []
    valid = {}
    seen_pairs = set()

    for raw in records:
        record, reason = _normalize(raw)
        if reason:
            failed.append(
                {"name": (record or {}).get("name", str(raw)[:40]), "reason": reason}
            )
            continue
        if record["code"] in valid:
            failed.append(
                {
                    "name": record["name"],
                    "reason": f"编码在输入内重复: {record['code']}",
                }
            )
            continue
        pair = (record["name"], record["parent"])
        if pair in seen_pairs:
            failed.append({"name": record["name"], "reason": "同父级下名称重复"})
            continue
        seen_pairs.add(pair)
        valid[record["code"]] = record

    known = set(known_parent_codes)
    ordered = []
    emitted = set()
    pending = dict(valid)
    while pending:
        ready = [
            code
            for code, record in pending.items()
            if record["parent"] is None
            or record["parent"] in known
            or record["parent"] in emitted
        ]
        if not ready:
            break
        for code in ready:
            ordered.append(pending.pop(code))
            emitted.add(code)

    for record in pending.values():
        failed.append(
            {
                "name": record["name"],
                "reason": _classify_pending(record, pending, known),
            }
        )
    return ordered, failed


def seed_records(ordered, dialect_model, dry_run=False):
    """把有序记录写入 ``Dialect`` 表，``dry_run`` 只统计不落库。

    dry-run 与真实执行共用同一校验与统计路径，仅最后写入开关不同。
    """
    from django.db import IntegrityError, transaction

    report = {"created": 0, "skipped": 0, "failed": []}
    resolved = {}

    for record in ordered:
        parent = None
        parent_code = record["parent"]
        if parent_code:
            parent = resolved.get(parent_code)
            if parent is None:
                parent = dialect_model.objects.filter(code=parent_code).first()
            if parent is None:
                report["failed"].append(
                    {"name": record["name"], "reason": f"父级不存在: {parent_code}"}
                )
                continue
            if isinstance(parent, _PlannedNode):
                # 父级只在计划中（dry-run 未落库），子级的「名称 + 父级」必然
                # 不存在；但 code 是全局唯一，仍需与真实写入路径一致的占用预检，
                # 否则 dry-run 会对真实执行必然失败的记录误报 created。
                if dialect_model.objects.filter(code=record["code"]).exists():
                    report["failed"].append(
                        {
                            "name": record["name"],
                            "reason": f"编码已被占用: {record['code']}",
                        }
                    )
                    continue
                report["created"] += 1
                resolved[record["code"]] = _PlannedNode(record["code"])
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
                resolved[record["code"]] = existing
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
            resolved[record["code"]] = _PlannedNode(record["code"])
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
        resolved[record["code"]] = obj
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
    known_codes = set(dialect_model.objects.values_list("code", flat=True))
    ordered, failed = validate_records(records, known_parent_codes=known_codes)
    report = seed_records(ordered, dialect_model, dry_run=args.dry_run)
    report["failed"] = failed + report["failed"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
