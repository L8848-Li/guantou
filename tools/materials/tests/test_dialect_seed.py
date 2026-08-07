import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.materials.dialect_seed import seed_dialects


def _record(code, name, parent=None, region_level="dialect", **extra):
    data = {"code": code, "name": name, "parent": parent, "region_level": region_level}
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
        path = self._write(".json", json.dumps([_record("a", "甲")]))
        records = seed_dialects.load_records(path)
        self.assertEqual(records[0]["code"], "a")

    def test_load_csv_records(self):
        path = self._write(".csv", "code,name,parent,region_level\na,甲,,dialect\n")
        records = seed_dialects.load_records(path)
        self.assertEqual(records[0]["name"], "甲")
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
    def test_topological_ordering(self):
        records = [
            _record("child", "方言点", parent="area"),
            _record("area", "片区", parent="root"),
            _record("root", "方言", parent=None),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual([r["code"] for r in ordered], ["root", "area", "child"])
        self.assertEqual(failed, [])

    def test_missing_name_failed(self):
        ordered, failed = seed_dialects.validate_records([_record("a", "  ")])
        self.assertEqual(ordered, [])
        self.assertEqual(failed[0]["reason"], "缺少名称")

    def test_missing_code_failed(self):
        ordered, failed = seed_dialects.validate_records([_record("", "甲")])
        self.assertEqual(failed[0]["reason"], "缺少编码")

    def test_invalid_region_level_failed(self):
        ordered, failed = seed_dialects.validate_records(
            [_record("a", "甲", region_level="village")]
        )
        self.assertIn("层级取值非法", failed[0]["reason"])

    def test_missing_region_level_defaults_to_dialect(self):
        raw = _record("a", "甲")
        del raw["region_level"]
        ordered, failed = seed_dialects.validate_records([raw])
        self.assertEqual(ordered[0]["region_level"], "dialect")
        self.assertEqual(failed, [])

    def test_duplicate_code_failed(self):
        records = [_record("a", "甲"), _record("a", "乙")]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual([r["code"] for r in ordered], ["a"])
        self.assertEqual(failed[0]["reason"], "编码在输入内重复: a")

    def test_duplicate_name_under_same_parent_failed(self):
        records = [
            _record("root", "方言", parent=None),
            _record("a", "甲", parent="root"),
            _record("b", "甲", parent="root"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(len(ordered), 2)
        self.assertEqual(failed[0]["reason"], "同父级下名称重复")

    def test_same_name_under_different_parents_allowed(self):
        records = [
            _record("p1", "片一"),
            _record("p2", "片二"),
            _record("a", "甲", parent="p1"),
            _record("b", "甲", parent="p2"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(len(ordered), 4)
        self.assertEqual(failed, [])

    def test_missing_parent_failed(self):
        ordered, failed = seed_dialects.validate_records(
            [_record("a", "甲", parent="ghost")]
        )
        self.assertEqual(ordered, [])
        self.assertEqual(failed[0]["reason"], "父级不存在: ghost")

    def test_cycle_failed(self):
        records = [
            _record("a", "甲", parent="b"),
            _record("b", "乙", parent="a"),
            _record("ok", "正常", parent=None),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual([r["code"] for r in ordered], ["ok"])
        self.assertEqual({f["reason"] for f in failed}, {"父级引用成环"})

    def test_known_parent_codes_resolves_external_parent(self):
        records = [_record("a", "甲", parent="existing-in-db")]
        ordered, failed = seed_dialects.validate_records(
            records, known_parent_codes=["existing-in-db"]
        )
        self.assertEqual([r["code"] for r in ordered], ["a"])
        self.assertEqual(failed, [])

    def test_child_of_invalid_record_fails(self):
        records = [
            _record("bad", "", region_level="village"),
            _record("kid", "子", parent="bad"),
        ]
        ordered, failed = seed_dialects.validate_records(records)
        self.assertEqual(ordered, [])
        self.assertEqual(len(failed), 2)


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
            _record("new-parent", "本次新建父级"),
            _record("taken-code", "冲突子级", parent="new-parent"),
        ]

    def test_dry_run_flags_code_conflict_under_planned_parent(self):
        # 数据库中无关节点已占用子级 code，父级为本次计划新建
        self.dialect_model.objects.create(name="无关节点", code="taken-code")
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
        self.dialect_model.objects.create(name="无关节点", code="taken-code")
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
            [("冲突子级", "编码已被占用: taken-code")],
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


if __name__ == "__main__":
    unittest.main()
