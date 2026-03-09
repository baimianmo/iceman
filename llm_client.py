import os
import json
import requests
import subprocess
from openai import OpenAI

class LLMClient:
    """
    LLM 客户端，支持 DeepSeek、ZhipuAI GLM (默认 glm-4-flash) 与本地 Ollama（qwen3-vl:8b 等）。
    """
    def __init__(self):
        # 后端选择：deepseek / ollama / glm
        self.backend = os.getenv("LLM_BACKEND", "deepseek").lower()
        
        # DeepSeek 配置
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or "sk-your-api-key-here"
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        # GLM (ZhipuAI) 配置
        self.glm_api_key = os.getenv("GLM_API_KEY") or ""
        self.glm_base_url = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        self.glm_model = os.getenv("GLM_MODEL", "glm-4-flash")
        
        # Ollama 配置
        self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen3-vl:8b")
        self.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        self.ollama_retries = int(os.getenv("OLLAMA_RETRIES", "1"))
        self.ollama_strict_local = os.getenv("OLLAMA_STRICT_LOCAL", "false").lower() in ("1", "true", "yes", "on")
        self.ollama_cli_timeout = int(os.getenv("OLLAMA_CLI_TIMEOUT", str(max(self.ollama_timeout * 2, 120))))

        self.client = None
        if self.backend == "deepseek":
            self.client = OpenAI(api_key=self.deepseek_api_key, base_url=self.deepseek_base_url)
            self.model = self.deepseek_model
        elif self.backend == "glm":
            if not self.glm_api_key:
                print("【警告】未检测到 GLM_API_KEY，将无法正常调用 GLM 模型。")
            self.client = OpenAI(api_key=self.glm_api_key, base_url=self.glm_base_url)
            self.model = self.glm_model

    def chat_completion(self, system_prompt, user_prompt, temperature=0.7):
        """
        调用 LLM 进行对话
        """
        if self.backend == "ollama":
            try:
                url = f"{self.ollama_base}/api/chat"
                payload = {
                    "model": self.ollama_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": temperature}
                }
                # 可选重试
                attempts = 1 + max(self.ollama_retries, 0)
                last_err = None
                for _ in range(attempts):
                    try:
                        resp = requests.post(url, json=payload, timeout=self.ollama_timeout)
                        resp.raise_for_status()
                        data = resp.json()
                        content = (data.get("message") or {}).get("content")
                        if not content and isinstance(data, dict):
                            choices = data.get("choices")
                            if choices and isinstance(choices, list):
                                content = choices[0]["message"]["content"]
                        return content or ""
                    except Exception as e_try:
                        last_err = e_try
                raise last_err
            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status in (404, 405):
                    try:
                        url = f"{self.ollama_base}/api/generate"
                        payload = {
                            "model": self.ollama_model,
                            "prompt": f"{system_prompt}\n\n{user_prompt}",
                            "stream": False,
                            "options": {"temperature": temperature}
                        }
                        r2 = requests.post(url, json=payload, timeout=self.ollama_timeout)
                        r2.raise_for_status()
                        d2 = r2.json()
                        content = d2.get("response") or d2.get("message", {}).get("content") or ""
                        return content
                    except Exception as e2:
                        print(f"【LLM 调用失败(ollama generate)】: {e2}")
                        c = self._ollama_cli(system_prompt, user_prompt, temperature)
                        if c:
                            return c
                        if self.ollama_strict_local:
                            raise RuntimeError("Ollama strict local mode: HTTP generate and CLI failed")
                        return self._mock_response(system_prompt, user_prompt)
                print(f"【LLM 调用失败(ollama)】: {e}")
                c = self._ollama_cli(system_prompt, user_prompt, temperature)
                if c:
                    return c
                if self.ollama_strict_local:
                    raise RuntimeError("Ollama strict local mode: HTTP chat and CLI failed")
                return self._mock_response(system_prompt, user_prompt)
            except Exception as e:
                print(f"【LLM 调用失败(ollama)】: {e}")
                c = self._ollama_cli(system_prompt, user_prompt, temperature)
                if c:
                    return c
                if self.ollama_strict_local:
                    raise RuntimeError("Ollama strict local mode: all fallbacks failed")
                return self._mock_response(system_prompt, user_prompt)

        # deepseek / glm
        if self.backend == "deepseek":
            if self.deepseek_api_key == "sk-your-api-key-here":
                print("【警告】未检测到 DEEPSEEK_API_KEY 环境变量，将返回模拟数据。")
                return self._mock_response(system_prompt, user_prompt)
        elif self.backend == "glm":
            if not self.glm_api_key:
                print("【警告】未检测到 GLM_API_KEY 环境变量，将返回模拟数据。")
                return self._mock_response(system_prompt, user_prompt)

        try:
            response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    stream=False
                )
            return response.choices[0].message.content
        except Exception as e:
            print(f"【LLM 调用失败({self.backend})】: {e}")
            return self._mock_response(system_prompt, user_prompt)

    def _ollama_cli(self, system_prompt, user_prompt, temperature):
        try:
            p = subprocess.run(
                ["ollama", "run", self.ollama_model],
                input=(f"{system_prompt}\n\n{user_prompt}").encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.ollama_cli_timeout
            )
            if p.returncode == 0:
                out = p.stdout.decode("utf-8", errors="ignore").strip()
                return out
        except Exception as e:
            print(f"【LLM 调用失败(ollama cli)】: {e}")
        return ""
    def _mock_response(self, system_prompt, user_prompt):
        """
        当没有 API Key 时的降级 Mock 方案 (保留之前的逻辑)
        """
        print("[LLMClient] 正在使用 Mock 模式 (请设置 API Key 以启用真实智能)...")
        if "意图识别" in system_prompt:
            if "生日" in user_prompt:
                return '{"intent": "birthday", "customer": "张三", "extra_info": "喜欢篮球"}'
            elif "节日" in user_prompt or "春节" in user_prompt:
                return '{"intent": "holiday", "customer": "李四", "extra_info": "春节"}'
            elif "庆祝" in user_prompt or "升职" in user_prompt:
                return '{"intent": "celebration", "customer": "王五", "extra_info": "升职"}'
            else:
                return '{"intent": "unknown", "customer": "Unknown", "extra_info": ""}'
        
        # 简单的文案生成 Mock
        return f"这是 Mock 模式生成的文案。您请求了：{user_prompt[:20]}..."

llm_client = LLMClient()
