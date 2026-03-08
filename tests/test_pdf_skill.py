import os
import unittest


class TestPdfSkill(unittest.TestCase):
    def test_generate_pdf_from_card(self):
        from skills import skills
        img_path = skills.generate_card("测试PDF导出", "celebration")
        pdf_path = skills.call("pdf", "generate_pdf", img_path)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertTrue(pdf_path.lower().endswith(".pdf"))


if __name__ == "__main__":
    unittest.main()
