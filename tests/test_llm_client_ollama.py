import os
import unittest
from unittest.mock import patch, Mock


class TestLLMClientOllama(unittest.TestCase):
    def setUp(self):
        os.environ["LLM_BACKEND"] = "ollama"
        os.environ["OLLAMA_MODEL"] = "qwen3-vl:8b"
        os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

    def tearDown(self):
        for k in ["LLM_BACKEND", "OLLAMA_MODEL", "OLLAMA_BASE_URL"]:
            if k in os.environ:
                del os.environ[k]

    @patch("requests.post")
    def test_chat_endpoint_success(self, mock_post):
        from llm_client import LLMClient
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.json = Mock(return_value={"message": {"content": "hello from chat"}})
        mock_post.return_value = resp

        c = LLMClient()
        out = c.chat_completion("sys", "user")
        self.assertEqual(out, "hello from chat")

    @patch("requests.post")
    def test_fallback_to_generate_on_404(self, mock_post):
        from requests.exceptions import HTTPError
        from llm_client import LLMClient

        def side_effect(url, json=None, timeout=60, **kwargs):
            m = Mock()
            if url.endswith("/api/chat"):
                err_resp = Mock()
                err_resp.status_code = 404
                e = HTTPError("404", response=err_resp)
                def raise_err():
                    raise e
                m.raise_for_status = raise_err
                return m
            elif url.endswith("/api/generate"):
                m.raise_for_status = Mock()
                m.json = Mock(return_value={"response": "hello from generate"})
                return m
            return m

        mock_post.side_effect = side_effect
        c = LLMClient()
        out = c.chat_completion("sys", "user")
        self.assertEqual(out, "hello from generate")

    @patch("requests.post")
    def test_fallback_to_generate_on_405(self, mock_post):
        from requests.exceptions import HTTPError
        from llm_client import LLMClient

        def side_effect(url, json=None, timeout=60, **kwargs):
            m = Mock()
            if url.endswith("/api/chat"):
                err_resp = Mock()
                err_resp.status_code = 405
                e = HTTPError("405", response=err_resp)
                def raise_err():
                    raise e
                m.raise_for_status = raise_err
                return m
            elif url.endswith("/api/generate"):
                m.raise_for_status = Mock()
                m.json = Mock(return_value={"response": "hello from generate 405"})
                return m
            return m

        mock_post.side_effect = side_effect
        c = LLMClient()
        out = c.chat_completion("sys", "user")
        self.assertEqual(out, "hello from generate 405")

    @patch("subprocess.run")
    @patch("requests.post")
    def test_cli_fallback_when_http_fail(self, mock_post, mock_run):
        from requests.exceptions import HTTPError
        from llm_client import LLMClient

        def side_effect(url, json=None, timeout=60, **kwargs):
            m = Mock()
            # 模拟 read timeout 或其它异常
            e = Exception("read timeout")
            def raise_err():
                raise e
            m.raise_for_status = raise_err
            return m

        mock_post.side_effect = side_effect
        pr = Mock()
        pr.returncode = 0
        pr.stdout = b"hello from cli"
        mock_run.return_value = pr

        c = LLMClient()
        os.environ["OLLAMA_TIMEOUT"] = "1"
        os.environ["OLLAMA_RETRIES"] = "0"
        out = c.chat_completion("sys", "user")
        self.assertEqual(out, "hello from cli")

    @patch("subprocess.run")
    @patch("requests.post")
    def test_strict_local_raises_on_all_fail(self, mock_post, mock_run):
        from llm_client import LLMClient
        # 所有 HTTP 请求均失败
        def side_effect(url, json=None, timeout=60, **kwargs):
            m = Mock()
            def raise_err():
                raise Exception("read timeout")
            m.raise_for_status = raise_err
            return m
        mock_post.side_effect = side_effect
        # CLI 也失败
        pr = Mock()
        pr.returncode = 1
        pr.stdout = b""
        mock_run.return_value = pr

        os.environ["OLLAMA_TIMEOUT"] = "1"
        os.environ["OLLAMA_RETRIES"] = "0"
        os.environ["OLLAMA_STRICT_LOCAL"] = "true"
        c = LLMClient()
        with self.assertRaises(RuntimeError):
            c.chat_completion("sys", "user")

    @patch("subprocess.run")
    @patch("requests.post")
    def test_cli_timeout_env(self, mock_post, mock_run):
        from llm_client import LLMClient
        def side_effect(url, json=None, timeout=60, **kwargs):
            m = Mock()
            def raise_err():
                raise Exception("read timeout")
            m.raise_for_status = raise_err
            return m
        mock_post.side_effect = side_effect
        pr = Mock()
        pr.returncode = 0
        pr.stdout = b"ok"
        mock_run.return_value = pr
        os.environ["OLLAMA_TIMEOUT"] = "10"
        os.environ["OLLAMA_CLI_TIMEOUT"] = "200"
        c = LLMClient()
        c.chat_completion("sys", "user")
        called_timeout = mock_run.call_args[1].get("timeout")
        self.assertEqual(called_timeout, 200)


if __name__ == "__main__":
    unittest.main()
