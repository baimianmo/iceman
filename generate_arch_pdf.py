import os
from PIL import Image, ImageDraw, ImageFont

# Canvas setup
WIDTH = 800
HEIGHT = 1000
BACKGROUND_COLOR = (255, 255, 255)
BOX_COLOR = (240, 248, 255)
BORDER_COLOR = (0, 0, 0)
TEXT_COLOR = (0, 0, 0)
ARROW_COLOR = (0, 0, 0)

try:
    # Try to load a nicer font if available, fallback to default
    FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    TITLE_FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
except IOError:
    FONT = ImageFont.load_default()
    TITLE_FONT = ImageFont.load_default()

def draw_box(draw, xy, text, title=False):
    x, y, w, h = xy
    draw.rectangle([x, y, x+w, y+h], fill=BOX_COLOR, outline=BORDER_COLOR, width=2)
    
    # Center text
    font = TITLE_FONT if title else FONT
    lines = text.split('\n')
    line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 4
    total_height = len(lines) * line_height
    
    start_y = y + (h - total_height) / 2
    for i, line in enumerate(lines):
        line_w = font.getbbox(line)[2]
        line_x = x + (w - line_w) / 2
        draw.text((line_x, start_y + i * line_height), line, fill=TEXT_COLOR, font=font)

def draw_arrow(draw, start, end):
    x1, y1 = start
    x2, y2 = end
    draw.line([x1, y1, x2, y2], fill=ARROW_COLOR, width=2)
    # Simple arrowhead
    # Not implementing full arrowhead logic for brevity, just a line is enough to show flow
    # But adding a small circle at the end to denote direction
    r = 3
    draw.ellipse([x2-r, y2-r, x2+r, y2+r], fill=ARROW_COLOR)

def main():
    img = Image.new('RGB', (WIDTH, HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((300, 30), "Iceman Architecture", fill=TEXT_COLOR, font=TITLE_FONT)

    # 1. Interface Layer
    draw_box(draw, (300, 100, 200, 60), "User / Feishu\n(Interface)")
    
    # 2. Main Agent
    draw_box(draw, (300, 250, 200, 60), "MainAgent\n(Router)")
    draw_arrow(draw, (400, 160), (400, 250))

    # 3. SubAgents
    # Layout: Birthday, Holiday, Celebration, External
    sub_y = 400
    sub_w = 140
    gap = 20
    start_x = (WIDTH - (4 * sub_w + 3 * gap)) / 2
    
    agents = ["Birthday\nAgent", "Holiday\nAgent", "Celebration\nAgent", "External\nSkills"]
    agent_centers = []
    
    for i, name in enumerate(agents):
        x = start_x + i * (sub_w + gap)
        draw_box(draw, (x, sub_y, sub_w, 60), name)
        # Connect Main to Sub
        draw_arrow(draw, (400, 310), (x + sub_w/2, sub_y))
        agent_centers.append((x + sub_w/2, sub_y + 60))

    # 4. LLM Client & Skill Manager (Shared Resources)
    llm_y = 600
    draw_box(draw, (200, llm_y, 180, 80), "LLM Client\n(DeepSeek/Ollama)")
    
    skill_y = 600
    draw_box(draw, (420, skill_y, 180, 80), "Skill Manager\n(Builtin/External)")

    # Connect Agents to LLM & Skills
    for center in agent_centers:
        # Draw lines to a common bus or direct
        draw_arrow(draw, center, (290, llm_y)) # To LLM
        draw_arrow(draw, center, (510, skill_y)) # To Skills

    # 5. Skills Detail
    detail_y = 800
    draw_box(draw, (420, detail_y, 180, 100), "Skills:\n- Profile\n- Card\n- PDF\n- AutoGen")
    draw_arrow(draw, (510, skill_y + 80), (510, detail_y))

    # Save
    output_path = "architecture.pdf"
    img.save(output_path, "PDF")
    print(f"Generated {output_path}")

if __name__ == "__main__":
    main()
