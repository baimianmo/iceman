from llm_client import LLMClient

class Skill:
    """
    Auto-generated skill: summarize
    包含一个方法 `run`，用于在缺省时通过大模型完成通用任务；
    若大模型不可用，将使用简单规则进行降级（如截断/回显）。
    """
    def __init__(self):
        self.llm = LLMClient()

    def run(self, *args, **kwargs):
        # 将输入拼成可读提示
        parts = []
        if args:
            parts.append("ARGS=" + ", ".join([str(a) for a in args]))
        if kwargs:
            parts.append("KWARGS=" + ", ".join([f"{k}={v}" for k, v in kwargs.items()]))
        user_prompt = "\n".join(parts) if parts else "无参数"
        system_prompt = "你是一个工具函数，实现 summarize.run 的逻辑。根据输入返回符合直觉的简明结果。只输出结果本身。"
        try:
            out = self.llm.chat_completion(system_prompt, user_prompt, temperature=0.3)
            if isinstance(out, str) and out.strip():
                return out.strip()
        except Exception:
            pass
        # 降级：若无大模型可用，则返回拼接的简要文本
        if kwargs.get("text"):
            t = str(kwargs.get("text"))
            return (t[:120] + "...") if len(t) > 120 else t
        return "OK"

def register(manager):
    manager.register("summarize", Skill())
