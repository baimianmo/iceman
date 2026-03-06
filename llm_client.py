import os
import json
from openai import OpenAI

class LLMClient:
    """
    LLM 客户端，支持 DeepSeek (及其他兼容 OpenAI 接口的模型)。
    """
    def __init__(self):
        # 优先从环境变量获取 API Key，如果没有则使用默认值（仅供测试，建议使用环境变量）
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or "sk-your-api-key-here"
        self.base_url = "https://api.deepseek.com" # DeepSeek 官方 API 地址
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.model = "deepseek-chat"

    def chat_completion(self, system_prompt, user_prompt, temperature=0.7):
        """
        调用 LLM 进行对话
        """
        if self.api_key == "sk-your-api-key-here" and not os.getenv("DEEPSEEK_API_KEY"):
            print("【警告】未检测到 DEEPSEEK_API_KEY 环境变量，将返回模拟数据。")
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
            print(f"【LLM 调用失败】: {e}")
            return self._mock_response(system_prompt, user_prompt)

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