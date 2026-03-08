from .manager import SkillManager
from .builtin.profile import ProfileSkill
from .builtin.card import CardSkill
from .builtin.pdf import PdfSkill

skills = SkillManager()
skills.register("profile", ProfileSkill())
skills.register("card", CardSkill())
skills.register("pdf", PdfSkill())
