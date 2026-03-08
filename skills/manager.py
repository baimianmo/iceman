import os
import json
import importlib
import importlib.util
import requests
import re
from urllib.parse import urlencode


class SkillManager:
    def __init__(self):
        self._skills = {}
        self._registry = {}
        self._base_dir = os.path.dirname(__file__)
        self._ext_dir = os.path.join(self._base_dir, "external")
        if not os.path.exists(self._ext_dir):
            os.makedirs(self._ext_dir, exist_ok=True)
        self._load_registry_from_markdown()
        self._load_external()

    def register(self, name, impl):
        self._skills[name] = impl
        if hasattr(impl, "bind"):
            impl.bind(self)

    def get(self, name):
        return self._skills.get(name)

    def call(self, skill, func, *args, **kwargs):
        s = self.get(skill)
        # 按需加载：若未加载但在注册表中，尝试即时加载
        if not s and skill in self._registry:
            meta = self._registry.get(skill, {})
            # 若注册表未提供 manifest_url，则尝试用环境变量解析（支持覆盖/补充）
            manifest_url = meta.get("manifest_url") or self._resolve_manifest_url(skill)
            entry = meta.get("entry")
            stype = meta.get("type") or "python"
            if manifest_url:
                try:
                    self.install_from_manifest(manifest_url)
                except Exception as e:
                    print(f"[SkillManager] lazy install failed: {manifest_url}: {e}")
                # 安装后更新元数据
                meta = self._registry.get(skill, meta)
                stype = meta.get("type") or stype
            if entry and not self.get(skill):
                try:
                    mod_path, cls_name = entry.split(":")
                    mod = importlib.import_module(mod_path)
                    cls = getattr(mod, cls_name)
                    inst = cls()
                    self.register(skill, inst)
                except Exception as e:
                    print(f"[SkillManager] lazy load entry failed: {entry}: {e}")
            s = self.get(skill)
            # http 类型直接走 http 分支
            if not s and (stype == "http" or (meta.get("type") == "http")):
                return self._call_http(meta, func, *args, **kwargs)
        # 若注册表也无记录，启用环境变量解析器按需安装
        if not s and skill not in self._registry:
            manifest_url = self._resolve_manifest_url(skill)
            if manifest_url:
                try:
                    self.install_from_manifest(manifest_url)
                except Exception as e:
                    print(f"[SkillManager] env-resolve install failed: {manifest_url}: {e}")
                # 可能是 http 技能，无需加载 python 包，直接从注册表走 http
                meta = self._registry.get(skill)
                if meta and (meta.get("type") == "http") and not self.get(skill):
                    return self._call_http(meta, func, *args, **kwargs)
                # 再次尝试加载 python entry
                meta = self._registry.get(skill, {})
                entry = meta.get("entry")
                if entry and not self.get(skill):
                    try:
                        mod_path, cls_name = entry.split(":")
                        mod = importlib.import_module(mod_path)
                        cls = getattr(mod, cls_name)
                        inst = cls()
                        self.register(skill, inst)
                    except Exception as e:
                        print(f"[SkillManager] env-resolve load entry failed: {entry}: {e}")
                s = self.get(skill)
            # 若仍未找到，自动生成 Python 技能骨架并加载
            if not s:
                try:
                    self._autogen_python_skill(skill, func)
                    # 载入自动生成的包（包名 autogen_<skill>），register() 会以原名注册
                    self._load_external_package(f"autogen_{skill}")
                    s = self.get(skill)
                except Exception as e:
                    print(f"[SkillManager] autogen skill failed: {skill}.{func}: {e}")
        if not s:
            raise RuntimeError(f"skill not found: {skill}")
        fn = getattr(s, func, None)
        if not fn:
            raise RuntimeError(f"skill method not found: {skill}.{func}")
        return fn(*args, **kwargs)

    def query_profile(self, name=None):
        return self.call("profile", "query_profile", name)

    def generate_card(self, content, theme="default"):
        return self.call("card", "generate_card", content, theme)

    def install_from_manifest(self, manifest_url):
        r = requests.get(manifest_url, timeout=20)
        r.raise_for_status()
        manifest = r.json()
        name = manifest["name"]
        # http 类型无需下载代码，直接注册到 _registry 以走 HTTP 分支
        if manifest.get("type") == "http":
            self._registry[name] = manifest
            return
        module_url = manifest.get("module_url")
        if not module_url:
            # 若未提供 module_url，则仅缓存注册信息，等待 entry 加载
            self._registry[name] = manifest
            return
        module_file = manifest.get("module_file", "skill.py")
        target_dir = os.path.join(self._ext_dir, name)
        os.makedirs(target_dir, exist_ok=True)
        mr = requests.get(module_url, timeout=30)
        mr.raise_for_status()
        with open(os.path.join(target_dir, module_file), "wb") as f:
            f.write(mr.content)
        init_path = os.path.join(target_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w", encoding="utf-8") as f:
                f.write("")
        # 缓存注册信息（便于 call 分支读取 type/entry）
        self._registry[name] = manifest
        self._load_external_package(name)

    def _load_external(self):
        if not os.path.isdir(self._ext_dir):
            return
        for d in os.listdir(self._ext_dir):
            p = os.path.join(self._ext_dir, d)
            if os.path.isdir(p):
                self._load_external_package(d)

    def _load_external_package(self, pkg_name):
        import sys
        mod_name = f"skills.external.{pkg_name}"
        try:
            if mod_name in sys.modules:
                mod = importlib.reload(sys.modules[mod_name])
            else:
                mod = importlib.import_module(mod_name)
            if hasattr(mod, "register"):
                mod.register(self)
            elif hasattr(mod, "Skill"):
                inst = getattr(mod, "Skill")()
                self.register(pkg_name, inst)
        except Exception as e:
            print(f"[SkillManager] load external skill failed: {pkg_name}: {e}")

    def _load_registry_from_markdown(self):
        """
        从项目根目录的 skills.md 读取以 ```skill ... ``` 包裹的 JSON 描述，
        自动安装/加载技能。字段支持：
          - name: 技能名（注册键）
          - entry: python 模块路径与类名，例如 'skills.builtin.card:CardSkill'
          - manifest_url: 外部技能清单地址（JSON），包含 name/module_url 等字段
          - type: 技能类型（python/http），http 技能直接走 HTTP 调用
          - auto_load: 是否立即加载（默认 true）
        """
        root_dir = os.path.abspath(os.path.join(self._base_dir, os.pardir))
        md_path = os.path.join(root_dir, "skills.md")
        if not os.path.exists(md_path):
            return
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return
        # 提取 ```skill ... ``` 代码块
        blocks = re.findall(r"```skill\s+([\s\S]*?)```", content, re.MULTILINE)
        for blk in blocks:
            blk = blk.strip()
            try:
                meta = json.loads(blk)
            except Exception as e:
                print(f"[SkillManager] invalid skill block (not JSON): {e}")
                continue
            name = meta.get("name")
            if not name:
                continue
            # 缓存注册信息，支持按需加载
            self._registry[name] = meta
            auto_load = meta.get("auto_load", True)
            manifest_url = meta.get("manifest_url")
            entry = meta.get("entry")
            if manifest_url:
                try:
                    self.install_from_manifest(manifest_url)
                except Exception as e:
                    print(f"[SkillManager] install manifest failed: {manifest_url}: {e}")
            if auto_load and entry:
                try:
                    mod_path, cls_name = entry.split(":")
                    mod = importlib.import_module(mod_path)
                    cls = getattr(mod, cls_name)
                    inst = cls()
                    self.register(name, inst)
                except Exception as e:
                    print(f"[SkillManager] load entry failed: {entry}: {e}")

    def _expand_env(self, val):
        if isinstance(val, str):
            def rep(m):
                k = m.group(1)
                return os.getenv(k, "")
            return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", rep, val)
        if isinstance(val, dict):
            return {k: self._expand_env(v) for k, v in val.items()}
        if isinstance(val, list):
            return [self._expand_env(v) for v in val]
        return val

    def _call_http(self, meta, func, *args, **kwargs):
        ep = meta.get("endpoint")
        method = (meta.get("method") or "GET").upper()
        if isinstance(ep, dict):
            ep = ep.get(func)
        if not ep:
            raise RuntimeError("http skill missing endpoint")
        headers = self._expand_env(meta.get("headers") or {})
        timeout = meta.get("timeout") or 15
        payload = {}
        if args and isinstance(args[0], dict) and not kwargs:
            payload = args[0]
        else:
            payload = kwargs
        if method == "GET":
            r = requests.get(ep, params=payload, headers=headers, timeout=timeout)
        elif method == "POST":
            ct = (headers.get("Content-Type") or "").lower()
            if "application/x-www-form-urlencoded" in ct:
                r = requests.post(ep, data=payload, headers=headers, timeout=timeout)
            else:
                r = requests.post(ep, json=payload, headers=headers, timeout=timeout)
        else:
            r = requests.request(method, ep, json=payload, headers=headers, timeout=timeout)
        try:
            return r.json()
        except Exception:
            return r.text

    def _resolve_manifest_url(self, skill_name: str):
        """
        从环境变量解析技能的 manifest URL：
          1) SKILL_<NAME>_MANIFEST_URL（优先，NAME 为大写）
          2) SKILLS_MANIFESTS（JSON，{ name: url }）
          3) SKILLS_INDEX_URL 基于约定的 <index>/<name>.json，可逗号分隔多个索引
        """
        # 1) per-skill env
        env_key = f"SKILL_{skill_name.upper()}_MANIFEST_URL"
        val = os.getenv(env_key)
        if val:
            return val
        # 2) mapping json
        mapping = os.getenv("SKILLS_MANIFESTS")
        if mapping:
            try:
                d = json.loads(mapping)
                if isinstance(d, dict) and skill_name in d:
                    return d[skill_name]
            except Exception:
                pass
        # 3) index url
        idx = os.getenv("SKILLS_INDEX_URL")
        if idx:
            # 支持以逗号分隔多个索引地址，依次尝试，返回第一个拼接结果
            for raw in idx.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                base = raw.rstrip("/")
                return f"{base}/{skill_name}.json"
        return None

    def _autogen_python_skill(self, skill_name: str, method_name: str):
        """
        自动生成一个最小可用的 Python 技能到 skills/external/autogen_<skill_name>/ 下，
        并在 register(manager) 中以 <skill_name> 注册。
        """
        pkg = f"autogen_{skill_name}"
        target_dir = os.path.join(self._ext_dir, pkg)
        os.makedirs(target_dir, exist_ok=True)
        init_path = os.path.join(target_dir, "__init__.py")
        code_path = os.path.join(target_dir, "skill.py")
        # 始终写入 __init__.py 以导出 register/SkiIl
        with open(init_path, "w", encoding="utf-8") as f:
            f.write("from .skill import register, Skill\n")
        # 生成代码：优先尝试使用 llm_client；失败则提供简易降级实现
        template = '''from llm_client import LLMClient

class Skill:
    """
    Auto-generated skill: __SKILL__
    包含一个方法 `__METHOD__`，用于在缺省时通过大模型完成通用任务；
    若大模型不可用，将使用简单规则进行降级（如截断/回显）。
    """
    def __init__(self):
        self.llm = LLMClient()

    def __METHOD__(self, *args, **kwargs):
        # 将输入拼成可读提示
        parts = []
        if args:
            parts.append("ARGS=" + ", ".join([str(a) for a in args]))
        if kwargs:
            parts.append("KWARGS=" + ", ".join([f"{k}={v}" for k, v in kwargs.items()]))
        user_prompt = "\\n".join(parts) if parts else "无参数"
        system_prompt = "你是一个工具函数，实现 __SKILL__.__METHOD__ 的逻辑。根据输入返回符合直觉的简明结果。只输出结果本身。"
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
    manager.register("__SKILL__", Skill())
'''
        code = template.replace("__SKILL__", skill_name).replace("__METHOD__", method_name)
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(code)
