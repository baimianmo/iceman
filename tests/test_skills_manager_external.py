import os
import unittest
from unittest.mock import patch, Mock


class TestSkillsManagerExternal(unittest.TestCase):
    def setUp(self):
        # 清理影响
        for k in ["SKILLS_MANIFESTS", "SKILLS_INDEX_URL", "SKILL_SUMMARIZE_MANIFEST_URL"]:
            if k in os.environ:
                del os.environ[k]

    @patch("requests.post")
    @patch("requests.get")
    def test_http_skill_via_env_mapping(self, mock_get, mock_post):
        # 构造 http 技能的 manifest
        manifest = {
            "name": "summarize",
            "type": "http",
            "method": "POST",
            "endpoint": {"run": "https://api.example.com/summarize"},
            "headers": {"Authorization": "Bearer ${API_TOKEN}"},
            "timeout": 5,
        }
        # 第一次 GET 请求为 manifest
        mock_get.side_effect = [
            Mock(**{"json.return_value": manifest, "raise_for_status.return_value": None}),
        ]
        mock_post.return_value = Mock(**{"json.return_value": {"text": "ok"}, "raise_for_status.return_value": None})

        os.environ["SKILLS_MANIFESTS"] = '{"summarize":"https://example.com/manifest/summarize.json"}'
        os.environ["API_TOKEN"] = "token"
        from skills import skills

        # 触发按需安装并走 http 调用
        out = skills.call("summarize", "run", text="hello")
        self.assertEqual(out.get("text"), "ok")

    @patch("requests.post")
    @patch("requests.get")
    def test_http_skill_via_index(self, mock_get, mock_post):
        manifest = {
            "name": "qa",
            "type": "http",
            "method": "POST",
            "endpoint": {"ask": "https://api.example.com/qa"},
        }
        mock_get.side_effect = [
            Mock(**{"json.return_value": manifest, "raise_for_status.return_value": None}),
        ]
        mock_post.return_value = Mock(**{"json.return_value": {"answer": "42"}, "raise_for_status.return_value": None})
        os.environ["SKILLS_INDEX_URL"] = "https://example.com/manifest"
        from skills import skills
        out = skills.call("qa", "ask", question="life?")
        self.assertEqual(out.get("answer"), "42")


if __name__ == "__main__":
    unittest.main()
