import os
import textwrap
from PIL import Image, ImageDraw, ImageFont


class CardSkill:
    def __init__(self):
        self.output_dir = "output_cards"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def generate_card(self, content, theme="default"):
        width, height = 800, 600
        bg_color = (255, 250, 240)
        if theme == "birthday":
            bg_color = (255, 240, 245)
        elif theme == "holiday":
            bg_color = (240, 255, 240)
        elif theme == "celebration":
            bg_color = (255, 248, 220)
        image = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
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
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()
        border_color = (200, 160, 100)
        draw.rectangle([20, 20, width - 20, height - 20], outline=border_color, width=5)
        title_map = {"birthday": "生日快乐", "holiday": "节日祝福", "celebration": "恭喜恭喜", "default": "温馨关怀"}
        title_text = title_map.get(theme, "温馨关怀")
        try:
            bbox = title_font.getbbox(title_text)
            text_width = bbox[2] - bbox[0]
        except AttributeError:
            text_width = title_font.getlength(title_text)
        draw.text(((width - text_width) / 2, 60), title_text, font=title_font, fill=(100, 50, 0))
        margin = 60
        para = textwrap.wrap(content, width=35)
        current_h = 150
        for line in para:
            draw.text((margin, current_h), line, font=font, fill=(50, 50, 50))
            current_h += 45
        footer = "From: 您的专属私银顾问"
        draw.text((width - 300, height - 80), footer, font=font, fill=(100, 100, 100))
        filename = f"{self.output_dir}/card_{theme}_{os.urandom(4).hex()}.png"
        image.save(filename)
        try:
            os.system(f"open {filename}")
        except:
            pass
        return filename

