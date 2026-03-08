import json
import re
from llm_client import llm_client, LLMClient
from skills import skills

class BaseAgent:
    def __init__(self, name):
        self.name = name

    def log(self, message):
        print(f"[{self.name}] {message}")

class SubAgent(BaseAgent):
    def process(self, profile, extra_info):
        raise NotImplementedError

class BirthdayAgent(SubAgent):
    def __init__(self):
        super().__init__("BirthdayAgent")

    def process(self, profile, extra_info):
        self.log(f"接收到生日关怀任务: {profile.get('name', '客户')}")
        
        # 构建 Prompt
        system_prompt = """你是一个专业的私人银行客户关怀专家。
请根据客户画像和附加信息生成一段温馨、得体、高情商的生日祝福文案。
风格要求：尊贵、温暖、真诚，避免过于生硬的营销词汇。
字数控制在 100 字以内，适合印在贺卡上。"""
        
        user_prompt = f"客户画像: {json.dumps(profile, ensure_ascii=False)}\n附加信息: {extra_info}"
        
        # 调用 LLM 生成文案
        content = llm_client.chat_completion(system_prompt, user_prompt)
        self.log(f"生成的文案: {content}")
        return content

class HolidayAgent(SubAgent):
    def __init__(self):
        super().__init__("HolidayAgent")

    def process(self, profile, extra_info):
        self.log(f"接收到节日关怀任务: {profile.get('name', '客户')}")
        
        system_prompt = """你是一个专业的私人银行客户关怀专家。
请根据客户画像生成一段节日祝福。
风格要求：结合客户的兴趣爱好，体现定制化关怀，优雅大气。
字数控制在 100 字以内。"""
        
        user_prompt = f"客户画像: {json.dumps(profile, ensure_ascii=False)}\n节日信息: {extra_info}"
        
        content = llm_client.chat_completion(system_prompt, user_prompt)
        self.log(f"生成的文案: {content}")
        return content

class CelebrationAgent(SubAgent):
    def __init__(self):
        super().__init__("CelebrationAgent")

    def process(self, profile, extra_info):
        self.log(f"接收到喜事庆祝任务: {profile.get('name', '客户')}")
        
        system_prompt = """你是一个专业的私人银行客户关怀专家。
请根据客户画像生成一段庆祝文案（如升职、乔迁、获奖等）。
不得出现任何生日或节日相关词语，如“生日”“生辰”“生日快乐”“happy birthday”“新年快乐”等，除非用户明确提及。
风格要求：热烈而不失稳重，赞美客户的成就。
字数控制在 100 字以内，只输出正文，不要标题或标签。"""
        
        user_prompt = f"客户画像: {json.dumps(profile, ensure_ascii=False)}\n庆祝事件: {extra_info}"
        
        content = llm_client.chat_completion(system_prompt, user_prompt, temperature=0.4)
        if contains_birthday_terms(content):
            sys2 = system_prompt + " 严禁出现生日相关词语。请修正为纯庆祝文案。"
            content = llm_client.chat_completion(sys2, user_prompt, temperature=0.2)
        self.log(f"生成的文案: {content}")
        return content

class MainAgent(BaseAgent):
    def __init__(self, agents, skills):
        # 如果传入的是列表，转换为字典
        if isinstance(agents, list):
            self.agents = {agent.name: agent for agent in agents}
        else:
            self.agents = agents
            
        self.skills = skills
        self.llm_client = LLMClient()

    def run(self, user_instruction):
        """CLI 模式运行"""
        result = self._process(user_instruction)
        if result:
            print("\n" + "#" * 20 + " 任务完成 " + "#" * 20)
            print(f"文案内容:\n{result['content']}")
            print(f"贺卡路径: {result['card_path']}")
            print("#" * 50)

    def run_and_return(self, user_instruction):
        """
        API 模式入口：执行指令并返回结构化数据
        :return: {
            "text": str,  # 最终回复给用户的文本 (包含画像信息和祝福语)
            "image_path": str, # 图片路径 (可选)
            "profile": dict,   # 客户画像数据 (可选)
            "blessing": str    # 纯祝福语 (可选)
        }
        """
        # 1. 意图识别
        intent = self._identify_intent(user_instruction)
        print(f"[MainAgent] 识别意图: {intent}")
        
        # 2. 提取关键信息 (姓名)
        # 简单规则提取，实际可用 LLM 提取
        name = None
        if "给" in user_instruction:
            try:
                # 假设格式: 给xxx发...
                parts = user_instruction.split("给")
                if len(parts) > 1:
                    # 取 "给" 后面到第一个标点或空格之间的内容
                    temp = parts[1].strip()
                    for split_char in ["发", "生", "祝", " "]:
                        if split_char in temp:
                            temp = temp.split(split_char)[0]
                    name = temp
            except:
                pass
        # 补充规则：匹配 “张先生/李女士” 这类称呼
        if not name:
            honorifics = "先生|女士|学长|老师|博士|教授|院士|部长|校长|团长|书记|主任|院长|局长|处长|科长|经理|总|董事长|馆长|所长|队长|班长|厂长|董事|监事|主任委员|委员长"
            m = re.search(rf'([\u4e00-\u9fa5]{{1,4}})({honorifics})', user_instruction)
            if m:
                name = m.group(0)
        
        # 3. 执行 Skill (查询画像)
        profile_data = None
        profile_text = ""
        if name:
            profile_json = self.skills.query_profile(name)
            try:
                profile_data = json.loads(profile_json)
                profile_text = f"【客户画像】\n姓名: {profile_data.get('name')}\n性别: {profile_data.get('gender')}\n等级: {profile_data.get('level')}\n资产: {profile_data.get('assets')}\n偏好: {profile_data.get('risk_preference')}\n爱好: {','.join(profile_data.get('hobbies', []))}\n"
            except:
                profile_text = profile_json

        # 4. 调度子 Agent (生成文案)
        blessing_text = ""
        agent_name = "default"
        # 子 Agent 接口为 process(profile: dict, extra_info: str)
        profile_for_agent = profile_data or {}
        extra_info = user_instruction
        if "生日" in intent:
            agent_name = "birthday"
            blessing_text = self.agents["birthday"].process(profile_for_agent, extra_info)
        elif "节日" in intent:
            agent_name = "holiday"
            blessing_text = self.agents["holiday"].process(profile_for_agent, extra_info)
        elif "庆祝" in intent:
            agent_name = "celebration"
            blessing_text = self.agents["celebration"].process(profile_for_agent, extra_info)
        else:
            # 其他场景：优先尝试外部技能映射（不预取，按需安装）
            external_map = {
                "翻译": "translate",
                "摘要": "summarize",
                "总结": "summarize",
                "语法纠错": "proofread",
            }
            mapped = None
            for kw, sk in external_map.items():
                if kw in user_instruction:
                    mapped = sk
                    break
            if mapped:
                try:
                    agent_name = "external"
                    blessing_text = self.skills.call(mapped, "run", text=user_instruction)
                except Exception:
                    blessing_text = ""
            # 如果外部映射未命中或失败，则兜底使用庆祝 Agent（稳妥输出）
            if not blessing_text:
                agent_name = "celebration"
                blessing_text = self.agents["celebration"].process(profile_for_agent, extra_info)
            
        # 5. 执行 Skill (生成贺卡)
        card_path = None
        if blessing_text:
            # 提取纯文本用于生成图片 (去掉可能的 "文案:" 前缀)
            clean_content = blessing_text.replace("文案:", "").strip()
            # 限制长度以免图片太挤
            if len(clean_content) > 50:
                clean_content = clean_content[:50] + "..."
                
            theme = agent_name if agent_name != "default" else "default"
            print(f"[MainAgent] 调度 Skill: 生成贺卡")
            card_path = self.skills.generate_card(clean_content, theme)

        pdf_path = None
        if card_path and any(k in user_instruction.lower() for k in ["pdf", "导出pdf", "输出pdf"]):
            try:
                pdf_path = self.skills.call("pdf", "generate_pdf", card_path)
            except Exception:
                pdf_path = None

        # 6. 构造返回
        # 如果有画像，text 优先展示画像，然后是祝福语
        final_text = ""
        if profile_text:
            final_text += profile_text + "\n"
        if blessing_text:
            final_text += f"【生成文案】\n{blessing_text}"

        return {
            "text": final_text, 
            "image_path": card_path,
            "pdf_path": pdf_path,
            "profile": profile_data,
            "blessing": blessing_text
        }

    def _identify_intent(self, user_instruction):
        """识别用户意图 (简单规则匹配，实际可用 LLM)"""
        # 复用之前的逻辑
        # 动态获取技能描述，供 LLM 参考
        skills_desc = self.skills.get_skill_descriptions()
        
        prompt = f"""
        请分析以下用户指令的意图，返回最匹配的一个类别：
        指令：{user_instruction}
        类别选项：[生日关怀, 节日关怀, 喜事庆祝, 客户画像查询, 其他]
        当前可用技能：
{skills_desc}
        如果指令明显对应某个技能（如“翻译”->translate），请优先返回“其他”。
        只返回类别名称，不要其他废话。
        """
        # 这里为了简单，我们用规则匹配代替调用 LLM，因为 LLM 比较慢
        # 如果需要更精准，可以取消下面注释调用 llm_client
        # return self.llm_client.get_completion(prompt).strip()
        
        if "生日" in user_instruction:
            return "生日关怀"
        elif "节日" in user_instruction or "中秋" in user_instruction or "春节" in user_instruction:
            return "节日关怀"
        elif ("庆祝" in user_instruction or "喜" in user_instruction or "考上" in user_instruction
              or "获奖" in user_instruction or "荣获" in user_instruction or "获得" in user_instruction
              or "立项" in user_instruction or "中标" in user_instruction or "入选" in user_instruction
              or "晋升" in user_instruction or "升职" in user_instruction or "录取" in user_instruction
              or "通过" in user_instruction
              or "购车" in user_instruction or "新车" in user_instruction or "买车" in user_instruction
              or "提车" in user_instruction or "豪车" in user_instruction or "交车" in user_instruction
              or "奖章" in user_instruction or "勋章" in user_instruction or "授勋" in user_instruction
              or "表彰" in user_instruction or "嘉奖" in user_instruction):
            return "喜事庆祝"
        elif "画像" in user_instruction or "查询" in user_instruction:
            return "客户画像查询"
        else:
            return "其他"

    def _process(self, user_instruction):
        """核心处理逻辑"""
        # (已弃用，建议统一使用 run_and_return)
        return self.run_and_return(user_instruction)

# 实例化
# 使用统一的意图键名，便于在主流程中按 'birthday'/'holiday'/'celebration' 调用
agents = {
    "birthday": BirthdayAgent(),
    "holiday": HolidayAgent(),
    "celebration": CelebrationAgent()
}
skills_instance = skills  # 复用导入的 skills 单例
main_agent = MainAgent(agents, skills_instance)

def contains_birthday_terms(text: str) -> bool:
    if not text:
        return False
    terms = ["生日", "生辰", "生日快乐", "happy birthday", "HBD"]
    for t in terms:
        if t.lower() in text.lower():
            return True
    return False
