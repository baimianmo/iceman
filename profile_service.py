import random
from faker import Faker

class ProfileService:
    def __init__(self):
        self.fake = Faker('zh_CN')
        # 预生成一些固定客户以便演示
        self.profiles = {}
        self.generate_demo_profiles()

    def generate_demo_profiles(self):
        """生成演示用的私银客户数据"""
        demo_names = ["张三", "李四", "王五", "赵六", "钱七"]
        
        # 私银客户特征
        membership_levels = ["Gold", "Platinum", "Diamond", "Black"]
        occupations = ["企业董事长", "投资合伙人", "知名律师", "外科主任医师", "房地产大亨"]
        interests_pool = ["高尔夫", "马术", "收藏(古董)", "红酒品鉴", "帆船", "滑雪", "慈善", "歌剧"]
        
        for name in demo_names:
            self.profiles[name] = {
                "name": name,
                "age": random.randint(35, 65),
                "gender": random.choice(["男", "女"]),
                "occupation": random.choice(occupations),
                "company": self.fake.company(),
                "assets_level": f"AUM {random.randint(10, 500)}M",  # 资产管理规模
                "membership_level": random.choice(membership_levels),
                "interests": random.sample(interests_pool, 3),
                "relationship_status": random.choice(["已婚", "离异", "单身"]),
                "children": [f"{random.choice(['儿子', '女儿'])}({random.randint(5, 25)}岁)" for _ in range(random.randint(0, 3))],
                "preferred_contact": random.choice(["微信", "电话", "邮件"]),
                "risk_preference": random.choice(["保守型", "稳健型", "进取型"]),
                "last_interaction": self.fake.date_this_year().strftime("%Y-%m-%d")
            }

    def get_profile(self, name=None):
        """
        获取客户画像
        如果指定了 name，则尝试生成匹配该 name 的画像（模拟数据库查询）
        """
        profile = {
            "name": name if name else self.fake.name(),
            "gender": "男" if name and ("先生" in name or "哥" in name) else ("女" if name and ("女士" in name or "姐" in name) else random.choice(["男", "女"])),
            "age": random.randint(25, 65),
            "level": random.choice(["白金卡", "钻石卡", "黑金卡"]),
            "assets": f"{random.randint(50, 2000)}万",
            "risk_preference": random.choice(["保守型", "稳健型", "进取型"]),
            "hobbies": random.sample(["高尔夫", "品茶", "红酒", "滑雪", "马术", "摄影", "书法"], 3),
            "birthday": self.fake.date_of_birth(minimum_age=25, maximum_age=65).strftime("%m-%d"),
            "manager": self.fake.name()
        }
        
        # 如果名字里有特定的称呼，去掉称呼作为名字的一部分，但保留性别特征
        if name:
            clean_name = name.replace("先生", "").replace("女士", "").replace("小姐", "")
            profile["name"] = clean_name
            
        return profile

# 单例模式供外部调用
_service = ProfileService()

def get_customer_profile(name):
    return _service.get_profile(name)