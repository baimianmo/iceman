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
            manifest_url = meta.get("manifest_url")
            entry = meta.get("entry")
            stype = meta.get("type") or "python"
            if manifest_url:
                try:
                    self.install_from_manifest(manifest_url)
                except Exception as e:
                    print(f"[SkillManager] lazy install failed: {manifest_url}: {e}")
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
            if not s and stype == "http":
                return self._call_http(meta, func, *args, **kwargs)
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
        module_url = manifest["module_url"]
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
        self._load_external_package(name)

    def _load_external(self):
        if not os.path.isdir(self._ext_dir):
            return
        for d in os.listdir(self._ext_dir):
            p = os.path.join(self._ext_dir, d)
            if os.path.isdir(p):
                self._load_external_package(d)

    def _load_external_package(self, pkg_name):
        mod_name = f"skills.external.{pkg_name}"
        try:
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
