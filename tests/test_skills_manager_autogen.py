import os
import unittest


class TestSkillsManagerAutogen(unittest.TestCase):
    def setUp(self):
        # 确保走 DeepSeek Mock 或本地可用，均可通过
        if "DEEPSEEK_API_KEY" in os.environ:
            del os.environ["DEEPSEEK_API_KEY"]
        os.environ["LLM_BACKEND"] = os.getenv("LLM_BACKEND", "deepseek")

    def tearDown(self):
        pass

    def test_autogen_missing_skill(self):
        # 使用一个随机且基本不存在的技能名，触发自动生成
        from skills import skills
        out = skills.call("autofoo", "run", text="测试自动生成技能")
        self.assertTrue(isinstance(out, str))
        self.assertTrue(len(out) > 0)


if __name__ == "__main__":
    unittest.main()
