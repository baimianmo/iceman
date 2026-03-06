import os
import json
import textwrap
from PIL import Image, ImageDraw, ImageFont
import profile_service

class SkillManager:
    def __init__(self):
        # 确保输出目录存在
        self.output_dir = "output_cards"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def query_profile(self, name=None):
        """
        查询客户画像
        :param name: 客户姓名
        :return: 客户画像详情 (JSON String)
        """
        print(f"[Skill] 正在查询私银客户 {name if name else ''}...")
        profile = profile_service.get_customer_profile(name)
        return json.dumps(profile, ensure_ascii=False, indent=2)

    def generate_card(self, content, theme="default"):
        """
        Skill: 使用 Pillow 生成图片贺卡
        """
        print(f"[Skill] 正在生成 {theme} 主题图片贺卡...")
        
        # 1. 设置画布
        width, height = 800, 600
        bg_color = (255, 250, 240)  # 象牙白
        if theme == "birthday":
            bg_color = (255, 240, 245) # 淡粉色
        elif theme == "holiday":
            bg_color = (240, 255, 240) # 蜜瓜绿
        elif theme == "celebration":
            bg_color = (255, 248, 220) # 玉米丝色
            
        image = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        
        # 2. 尝试加载中文字体，如果失败则使用默认
        # Mac OS 常见中文字体路径
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc"
        ]
        
        font = None
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, 32)
                    title_font = ImageFont.truetype(path, 48)
                    break
                except:
                    continue
        
        if not font:
            print("[Warning] 未找到系统自带中文字体，将使用默认字体(可能不支持中文显示)")
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()

        # 3. 绘制边框
        border_color = (200, 160, 100) # 金色
        draw.rectangle([20, 20, width-20, height-20], outline=border_color, width=5)
        
        # 4. 绘制标题
        title_map = {
            "birthday": "生日快乐",
            "holiday": "节日祝福",
            "celebration": "恭喜恭喜",
            "default": "温馨关怀"
        }
        title_text = title_map.get(theme, "温馨关怀")
        
        # 计算标题居中
        # Pillow 9.2.0+ 使用 left, top, right, bottom = font.getbbox(text)
        # 旧版本使用 w, h = draw.textsize(text, font)
        # 这里为了兼容性简化处理
        try:
            bbox = title_font.getbbox(title_text)
            text_width = bbox[2] - bbox[0]
        except AttributeError:
             # Fallback for older Pillow
             text_width = title_font.getlength(title_text)

        draw.text(((width - text_width) / 2, 60), title_text, font=title_font, fill=(100, 50, 0))

        # 5. 绘制正文 (自动换行)
        margin = 60
        para = textwrap.wrap(content, width=35) # 中文宽度大概是 35 个字符一行
        
        current_h = 150
        for line in para:
            draw.text((margin, current_h), line, font=font, fill=(50, 50, 50))
            current_h += 45  # 行高

        # 6. 绘制底部签名
        footer = "From: 您的专属私银顾问"
        draw.text((width - 300, height - 80), footer, font=font, fill=(100, 100, 100))

        # 7. 保存文件
        filename = f"{self.output_dir}/card_{theme}_{os.urandom(4).hex()}.png"
        image.save(filename)
        
        print(f"[Skill] 图片贺卡已保存至: {filename}")
        
        # 尝试打开图片 (仅 Mac)
        try:
            os.system(f"open {filename}")
        except:
            pass
            
        return filename

# 导出实例
skills = SkillManager()
