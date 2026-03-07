import os
import unittest


class TestAgentsIntent(unittest.TestCase):
    def setUp(self):
        # 强制走 DeepSeek Mock
        if "DEEPSEEK_API_KEY" in os.environ:
            del os.environ["DEEPSEEK_API_KEY"]
        os.environ["LLM_BACKEND"] = "deepseek"

    def tearDown(self):
        if "LLM_BACKEND" in os.environ:
            del os.environ["LLM_BACKEND"]

    def test_celebration_for_scholarship(self):
        from agents import main_agent
        r = main_agent.run_and_return("张学长获得国家青年基金项目")
        self.assertIn("生成文案", r["text"])
        self.assertTrue(bool(r["image_path"]))

    def test_celebration_for_new_car(self):
        from agents import main_agent
        r = main_agent.run_and_return("王先生新购豪车一辆")
        self.assertIn("生成文案", r["text"])
        self.assertTrue(bool(r["image_path"]))

    def test_no_birthday_word_in_award(self):
        from agents import main_agent
        r = main_agent.run_and_return("吴女士新获MBRT奖章")
        self.assertIn("生成文案", r["text"])
        self.assertNotIn("生日", r["blessing"])


if __name__ == "__main__":
    unittest.main()
