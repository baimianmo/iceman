# 如何添加本地 Skill

ICEMAN 支持用户通过添加本地 Python 代码的方式扩展系统能力。程序启动时会自动扫描并加载 `skills/external/` 目录下的所有技能。

## 1. 目录结构

请在 `skills/external/` 目录下创建一个新的文件夹，文件夹名称即为技能名称（建议使用小写字母和下划线）。

例如，我们要添加一个名为 `weather` 的技能，目录结构如下：

```
iceman/
├── skills/
│   ├── external/
│   │   ├── weather/           <-- 新建技能目录
│   │   │   ├── __init__.py    <-- 必须包含
│   │   │   └── skill.py       <-- 推荐命名，包含技能实现
│   │   ├── ...
```

## 2. 代码实现

### 2.1 编写技能类 (`skill.py`)

技能类可以是任意名称，但需要在 `__init__.py` 中进行注册。建议类名与目录名相关（如 `WeatherSkill`）。

技能类可以包含任意方法，这些方法后续可以通过 `skills.call("weather", "method_name", ...)` 被调用。

推荐添加 `description` 属性或类文档字符串（docstring），系统会自动读取并提供给 LLM 参考。

**示例 `skills/external/weather/skill.py`**:

```python
import random

class WeatherSkill:
    """
    查询天气信息的技能。
    支持方法：get_weather(city)
    """
    description = "查询指定城市的天气信息"  # 可选：显式定义描述

    def bind(self, manager):
        """
        可选：如果需要调用其他技能或使用 manager 功能，可实现此方法。
        manager 会在加载时自动调用。
        """
        self.manager = manager

    def get_weather(self, city="北京"):
        # 这里可以是真实的 API 调用
        conditions = ["晴", "多云", "小雨", "大风"]
        return f"{city}的天气是：{random.choice(conditions)}"
```

### 2.2 注册技能 (`__init__.py`)

在 `__init__.py` 中，你需要告诉系统如何加载这个技能。有两种方式：

**方式一：导出 `Skill` 类（推荐）**

系统会自动实例化该类并注册。

```python
from .skill import WeatherSkill as Skill
```

**方式二：导出 `register` 函数**

如果你需要更复杂的初始化逻辑，可以定义 `register` 函数。

```python
from .skill import WeatherSkill

def register(manager):
    manager.register("weather", WeatherSkill())
```

## 3. 验证与使用

### 3.1 验证加载

启动程序或运行测试脚本，系统会自动扫描 `skills/external/`。你可以通过以下代码验证：

```python
from skills import skills

# 打印所有已加载技能
print(skills.get_skill_descriptions())
```

### 3.2 在指令中使用

如果是通用型技能（如“翻译”、“查询”），你可以在 `agents.py` 的意图处理中增加映射，或者依赖 LLM 在识别到“其他”意图时，根据技能描述自动匹配（需配合 LLM 的 Function Calling 或意图路由优化）。

目前系统在识别到“其他”意图时，支持通过关键词自动映射到外部技能。例如，如果你添加了 `translate` 技能，并在指令中包含“翻译”，系统会自动尝试调用 `translate.run()`。

## 4. 高级配置 (skills.md)

虽然不是必须的，但你也可以在项目根目录的 `skills.md` 中添加技能的详细元数据（参数、返回值等），这有助于 LLM 更准确地理解如何调用你的技能。

**示例 `skills.md` 追加内容**:

```markdown
\`\`\`skill
{
  "name": "weather",
  "description": "查询城市天气",
  "entry": "skills.external.weather:Skill", 
  "auto_load": true
}
\`\`\`
```
*(注意：如果已经在 external 目录下通过 `__init__.py` 自动加载了，`skills.md` 中的 `entry` 可以省略，或者用于覆盖默认行为)*
