import json
from profile_service import get_customer_profile


class ProfileSkill:
    def query_profile(self, name=None):
        p = get_customer_profile(name)
        return json.dumps(p, ensure_ascii=False, indent=2)
