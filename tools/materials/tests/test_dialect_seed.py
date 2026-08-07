import json
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


if __name__ == "__main__":
    unittest.main()
