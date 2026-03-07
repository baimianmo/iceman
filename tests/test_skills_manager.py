import os
import json
import unittest
from pathlib import Path


class TestSkillsManager(unittest.TestCase):
    def setUp(self):
        # 保证使用默认 DeepSeek Mock，避免真实外呼
        if "DEEPSEEK_API_KEY" in os.environ:
            del os.environ["DEEPSEEK_API_KEY"]

    def test_profile_and_card(self):
        from skills import skills
        j = skills.query_profile("张先生")
        data = json.loads(j)
        self.assertIn("name", data)
        self.assertTrue(isinstance(data.get("hobbies", []), list))

        p = skills.generate_card("测试贺卡", "birthday")
        self.assertTrue(Path(p).exists(), f"card not exists at {p}")
        # 清理生成文件
        try:
            Path(p).unlink()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
