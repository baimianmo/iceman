import os
import unittest


class TestAgentsExternalMapping(unittest.TestCase):
    def setUp(self):
        # 使用默认 deepseek mock，让自动生成技能走降级路径也可通过
        if "DEEPSEEK_API_KEY" in os.environ:
            del os.environ["DEEPSEEK_API_KEY"]
        os.environ["LLM_BACKEND"] = "deepseek"

    def test_summarize_mapping_triggers_autogen(self):
        from agents import main_agent
        r = main_agent.run_and_return("请帮我摘要这段内容：投资策略与风险提示。")
        self.assertTrue(isinstance(r.get("blessing"), str))
        self.assertTrue(len(r.get("blessing")) > 0)

    def test_translate_mapping_triggers_autogen(self):
        from agents import main_agent
        r = main_agent.run_and_return("请翻译：你好世界")
        self.assertTrue(isinstance(r.get("blessing"), str))
        self.assertTrue(len(r.get("blessing")) > 0)


if __name__ == "__main__":
    unittest.main()
