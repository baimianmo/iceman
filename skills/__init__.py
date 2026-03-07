from .manager import SkillManager
from .builtin.profile import ProfileSkill
from .builtin.card import CardSkill

skills = SkillManager()
skills.register("profile", ProfileSkill())
skills.register("card", CardSkill())

