import os
from PIL import Image

class PdfSkill:
    def generate_pdf(self, image_path, output_path=None):
        img = Image.open(image_path).convert("RGB")
        if not output_path:
            base, _ = os.path.splitext(image_path)
            output_path = base + ".pdf"
        img.save(output_path, "PDF")
        return output_path
