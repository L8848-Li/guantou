import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.materials.dialect_seed import seed_dialects

SEED_JSON = Path(seed_dialects.__file__).resolve().parent / "dialects.json"


def _record(key, code, name, parent=None, region_level="dialect", **extra):
    data = {
        "key": key,
        "code": code,
        "name": name,
        "parent": parent,
        "region_level": region_level,
    }
    data.update(extra)
    return data


class LoadRecordsTest(unittest.TestCase):
    def _write(self, suffix, content):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        )
        handle.write(content)
        handle.close()
        self.addCleanup(Path(handle.name).unlink)
        return handle.name

    def test_load_json_records(self):
        path = self._write(".json", json.dumps([_record("a", "甲", "甲方言")]))
        records = seed_dialects.load_records(path)
        self.assertEqual(records[0]["code"], "甲")

    def test_load_csv_records(self):
        path = self._write(
            ".csv", "key,code,name,parent,region_level\na,甲,甲方言,,dialect\n"
        )
        records = seed_dialects.load_records(path)
        self.assertEqual(records[0]["name"], "甲方言")
        self.assertEqual(records[0]["parent"], "")

    def test_unsupported_extension(self):
        path = self._write(".txt", "x")
        with self.assertRaises(seed_dialects.SeedError):
            seed_dialects.load_records(path)

    def test_invalid_json(self):
        path = self._write(".json", "{not json")
        with self.assertRaises(seed_dialects.SeedError):
            seed_dialects.load_records(path)

    def test_top_level_must_be_list(self):
        path = self._write(".json", json.dumps({"dialects": []}))
        with self.assertRaises(seed_dialects.SeedError):
            seed_dialects.load_records(path)


class ValidateRecordsTest(unittest.TestCase):
    def test_topological_ordering_with_shuffled_input(self):
        # 乱序父子输入：子级先于父级出现，仍能排出父先子后的顺序
        records = [
            _record("youyang", "游洋", "游洋", parent="xianyou"),
            _record("xianyou", "仙游", "仙游", parent="puxian"),
            _record("puxian", "莆仙", "莆仙片", parent="min"),
            _record("min", "闽", "闽语"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual([r["key"] for r in ordered], ["min", "puxian", "xianyou", "youyang"])
        self.assertEqual(failed, [])

    def test_chinese_sibling_codes_qualified_path(self):
        # 中文短码 + 从根到叶的限定码拼接
        records = [
            _record("min", "闽", "闽语"),
            _record("puxian", "莆仙", "莆仙片", parent="min"),
            _record("xianyou", "仙游", "仙游", parent="puxian"),
            _record("youyang", "游洋", "游洋", parent="xianyou"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(failed, [])
        qualified = seed_dialects.qualified_codes(ordered)
        self.assertEqual(qualified["youyang"], "闽.莆仙.仙游.游洋")

    def test_missing_name_failed(self):
        ordered, failed = seed_dialects.validate_records([_record("a", "甲", "  ")])
        self.assertEqual(ordered, [])
        self.assertEqual(failed[0]["reason"], "缺少名称")

    def test_missing_key_failed(self):
        ordered, failed = seed_dialects.validate_records([_record("", "甲", "甲方言")])
        self.assertEqual(failed[0]["reason"], "缺少 source key")

    def test_missing_code_failed(self):
        ordered, failed = seed_dialects.validate_records([_record("a", "", "甲方言")])
        self.assertEqual(failed[0]["reason"], "缺少编码")

    def test_code_with_illegal_characters_failed(self):
        for bad_code in ("仙.游", "仙/游", "仙 游"):
            ordered, failed = seed_dialects.validate_records(
                [_record("a", bad_code, "甲方言")]
            )
            self.assertEqual(ordered, [])
            self.assertIn("非法字符", failed[0]["reason"], bad_code)

    def test_code_too_long_failed(self):
        ordered, failed = seed_dialects.validate_records(
            [_record("a", "长" * 33, "甲方言")]
        )
        self.assertIn("超过 32 字符", failed[0]["reason"])

    def test_invalid_region_level_failed(self):
        ordered, failed = seed_dialects.validate_records(
            [_record("a", "甲", "甲方言", region_level="village")]
        )
        self.assertIn("层级取值非法", failed[0]["reason"])

    def test_missing_region_level_defaults_to_dialect(self):
        raw = _record("a", "甲", "甲方言")
        del raw["region_level"]
        ordered, failed = seed_dialects.validate_records([raw])
        self.assertEqual(ordered[0]["region_level"], "dialect")
        self.assertEqual(failed, [])

    def test_duplicate_key_failed(self):
        records = [
            _record("a", "甲", "甲方言"),
            _record("a", "乙", "乙方言"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual([r["key"] for r in ordered], ["a"])
        self.assertIn("source key 在输入内重复", failed[0]["reason"])

    def test_duplicate_code_under_same_parent_failed(self):
        records = [
            _record("root", "根", "方言根"),
            _record("a", "甲", "甲方言", parent="root"),
            _record("b", "甲", "甲地另一条", parent="root"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(len(ordered), 2)
        self.assertEqual(failed[0]["reason"], "同级编码重复: 甲")

    def test_same_code_under_different_branches_allowed(self):
        # code 同级唯一：不同分支下允许相同短码
        records = [
            _record("p1", "片一", "片一"),
            _record("p2", "片二", "片二"),
            _record("a", "城关", "城关（片一）", parent="p1"),
            _record("b", "城关", "城关（片二）", parent="p2"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(len(ordered), 4)
        self.assertEqual(failed, [])

    def test_duplicate_name_under_same_parent_failed(self):
        records = [
            _record("root", "根", "方言根"),
            _record("a", "甲", "同名方言", parent="root"),
            _record("b", "乙", "同名方言", parent="root"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(len(ordered), 2)
        self.assertEqual(failed[0]["reason"], "同父级下名称重复")

    def test_missing_parent_failed(self):
        ordered, failed = seed_dialects.validate_records(
            [_record("a", "甲", "甲方言", parent="ghost")]
        )
        self.assertEqual(ordered, [])
        self.assertEqual(failed[0]["reason"], "父级不存在: ghost")

    def test_cycle_failed(self):
        records = [
            _record("a", "甲", "甲方言", parent="b"),
            _record("b", "乙", "乙方言", parent="a"),
            _record("ok", "正", "正常", parent=None),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual([r["key"] for r in ordered], ["ok"])
        self.assertEqual({f["reason"] for f in failed}, {"父级引用成环"})

    def test_known_qualified_parent_resolves_external_parent(self):
        # 父级引用已落库节点的完整限定码（断点续跑/增量导入）
        records = [_record("a", "游洋", "游洋", parent="闽.莆仙.仙游")]
        ordered, failed = seed_dialects.validate_records(
            records, known_parent_qualified=["闽.莆仙.仙游"]
        )
        self.assertEqual([r["key"] for r in ordered], ["a"])
        self.assertEqual(failed, [])
        qualified = seed_dialects.qualified_codes(ordered)
        self.assertEqual(qualified["a"], "闽.莆仙.仙游.游洋")

    def test_child_of_invalid_record_fails(self):
        records = [
            _record("bad", "坏", "", region_level="village"),
            _record("kid", "子", "子级", parent="bad"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(ordered, [])
        self.assertEqual(len(failed), 2)


class SeedFileTest(unittest.TestCase):
    """针对随脚本提供的 dialects.json 的整体校验。"""

    def test_seed_file_valid_and_contains_key_qualified_code(self):
        records = seed_dialects.load_records(SEED_JSON)
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(failed, [])
        self.assertGreater(len(ordered), 0)
        qualified = seed_dialects.qualified_codes(ordered)
        # 重点路径精确形成 v1 契约示例中的限定码
        self.assertIn("闽.莆仙.仙游.游洋", set(qualified.values()))


class SeedRecordsOrmTest(unittest.TestCase):
    """基于真实 SQLite 表的写入测试，验证 dry-run 与真实执行报告一致。

    需要后端 Django 环境（backend venv）；Django 不可用时整类自动跳过。
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls._previous_sqlite_path = os.environ.get("SQLITE_PATH")
        os.environ["SQLITE_PATH"] = os.path.join(
            cls._tmpdir.name, "dialect_seed_test.sqlite3"
        )
        try:
            cls.dialect_model = seed_dialects.setup_django()
        except Exception as exc:
            cls._restore_sqlite_path()
            cls._tmpdir.cleanup()
            raise unittest.SkipTest(f"Django 环境不可用: {exc}")
        from django.core.management import call_command

        # 在临时库上执行完整迁移，保证级联删除等关联查询的表都存在。
        call_command("migrate", run_syncdb=True, verbosity=0)

    @classmethod
    def _restore_sqlite_path(cls):
        if cls._previous_sqlite_path is None:
            os.environ.pop("SQLITE_PATH", None)
        else:
            os.environ["SQLITE_PATH"] = cls._previous_sqlite_path

    @classmethod
    def tearDownClass(cls):
        cls._restore_sqlite_path()
        cls._tmpdir.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.dialect_model.objects.all().delete()

    def _planned_parent_with_child(self):
        return [
            _record("new-parent", "新父", "本次新建父级"),
            _record("conflict", "冲突", "冲突子级", parent="new-parent"),
        ]

    def test_dry_run_flags_code_conflict_under_planned_parent(self):
        # 数据库中无关节点已占用子级 code，父级为本次计划新建
        self.dialect_model.objects.create(name="无关节点", code="冲突")
        ordered, failed = seed_dialects.validate_records(
            self._planned_parent_with_child()
        )
        self.assertEqual(failed, [])

        report = seed_dialects.seed_records(
            ordered, self.dialect_model, dry_run=True
        )

        self.assertEqual(report["created"], 1)  # 只有父级计入 created
        self.assertEqual(report["skipped"], 0)
        self.assertEqual(len(report["failed"]), 1)
        self.assertEqual(report["failed"][0]["name"], "冲突子级")
        self.assertIn("编码已被占用", report["failed"][0]["reason"])
        # dry-run 不应落库
        self.assertEqual(self.dialect_model.objects.count(), 1)

    def test_dry_run_matches_real_run_on_code_conflict(self):
        self.dialect_model.objects.create(name="无关节点", code="冲突")
        ordered, _ = seed_dialects.validate_records(self._planned_parent_with_child())

        dry_report = seed_dialects.seed_records(
            ordered, self.dialect_model, dry_run=True
        )
        real_report = seed_dialects.seed_records(
            ordered, self.dialect_model, dry_run=False
        )

        self.assertEqual(dry_report, real_report)
        self.assertEqual(
            [(item["name"], item["reason"]) for item in real_report["failed"]],
            [("冲突子级", "编码已被占用: 冲突")],
        )

    def test_planned_parent_child_created_when_code_free(self):
        ordered, _ = seed_dialects.validate_records(self._planned_parent_with_child())

        dry_report = seed_dialects.seed_records(
            ordered, self.dialect_model, dry_run=True
        )
        self.assertEqual(dry_report, {"created": 2, "skipped": 0, "failed": []})
        self.assertEqual(self.dialect_model.objects.count(), 0)

        real_report = seed_dialects.seed_records(
            ordered, self.dialect_model, dry_run=False
        )
        self.assertEqual(real_report, dry_report)
        self.assertEqual(self.dialect_model.objects.count(), 2)

    def test_parent_reference_by_existing_qualified_code(self):
        # 断点续跑：父级已落库，子级用完整限定码引用
        root = self.dialect_model.objects.create(name="闽语", code="闽")
        puxian = self.dialect_model.objects.create(
            name="莆仙片", code="莆仙", parent=root
        )
        xianyou = self.dialect_model.objects.create(
            name="仙游", code="仙游", parent=puxian
        )
        known = seed_dialects.existing_qualified_codes(self.dialect_model)
        self.assertIn("闽.莆仙.仙游", known)

        records = [_record("youyang", "游洋", "游洋", parent="闽.莆仙.仙游")]
        ordered, failed = seed_dialects.validate_records(
            records, known_parent_qualified=known
        )
        self.assertEqual(failed, [])

        report = seed_dialects.seed_records(ordered, self.dialect_model)
        self.assertEqual(report, {"created": 1, "skipped": 0, "failed": []})
        youyang = self.dialect_model.objects.get(code="游洋")
        self.assertEqual(youyang.parent_id, xianyou.id)


if __name__ == "__main__":
    unittest.main()
