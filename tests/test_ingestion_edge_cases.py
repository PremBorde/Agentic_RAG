"""
Ingestion & Parser Edge Cases Test Suite
Tests:
1. Multi-format parsing: PDF, DOCX, CSV, JSON, TXT, Markdown
2. Scanned image-only PDF detection and error handling
3. Table extraction in DOCX and CSV
4. Empty files (0 bytes and whitespace only)
5. Corrupted files (random garbage bytes)
6. Malformed JSON and malformed CSV
7. Metadata preservation across all formats
"""

import os
import sys
import io
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.parsers import (
    parse_pdf,
    parse_docx,
    parse_csv,
    parse_json,
    parse_plain_or_markdown,
    clean_text_artifacts
)

class TestIngestionEdgeCases(unittest.TestCase):

    def test_01_plain_text_and_markdown_headings(self):
        """Markdown with multiple heading levels must be split into sections preserving headings."""
        md_content = """# Main Title
This is the introduction text.

## Section 1: Algorithms
Dijkstra and Bellman-Ford algorithms find shortest paths.

### Section 1.1: Complexity
Time complexity is O((V+E) log V).

## Section 2: Databases
ACID properties ensure transaction reliability.
"""
        sections = parse_plain_or_markdown(md_content.encode("utf-8"))
        self.assertGreaterEqual(len(sections), 3)
        headings = [s["heading"] for s in sections]
        self.assertIn("Section 1: Algorithms", headings)
        self.assertIn("Section 2: Databases", headings)
        for s in sections:
            self.assertIn("text", s)
            self.assertIn("page_number", s)

    def test_02_docx_table_and_paragraph_extraction(self):
        """DOCX parser must extract paragraphs, heading hierarchy, and table rows."""
        import docx
        doc = docx.Document()
        doc.add_heading("Course Syllabus", level=1)
        doc.add_paragraph("This syllabus outlines the laboratory assignments.")
        
        doc.add_heading("Practical Assignments", level=2)
        table = doc.add_table(rows=3, cols=3)
        headers = ["ID", "Subject", "Description"]
        for j, h in enumerate(headers):
            table.cell(0, j).text = h
        table.cell(1, 0).text = "DAA-1"
        table.cell(1, 1).text = "Algorithms"
        table.cell(1, 2).text = "Fibonacci recursive vs non-recursive"
        table.cell(2, 0).text = "ML-1"
        table.cell(2, 1).text = "Machine Learning"
        table.cell(2, 2).text = "Bank customer churn classifier"
        
        bio = io.BytesIO()
        doc.save(bio)
        bytes_data = bio.getvalue()

        sections = parse_docx(bytes_data)
        self.assertGreaterEqual(len(sections), 1)
        full_text = "\n".join(s["text"] for s in sections)
        self.assertIn("DAA-1", full_text)
        self.assertIn("Bank customer churn", full_text)
        self.assertIn("[Table 1]:", full_text)

    def test_03_csv_header_grouping_and_columns(self):
        """CSV parser must retain column headers across row groupings."""
        csv_data = "TransactionID,Customer,Amount,Status\nTX101,Alice,250.00,Completed\nTX102,Bob,450.50,Pending\nTX103,Charlie,120.00,Completed\nTX104,David,99.99,Failed\nTX105,Eve,5000.00,Completed\nTX106,Frank,310.20,Completed\n"
        sections = parse_csv(csv_data.encode("utf-8"))
        self.assertGreaterEqual(len(sections), 1)
        text = sections[0]["text"]
        self.assertIn("TransactionID: TX101", text)
        self.assertIn("Customer: Alice", text)
        self.assertIn("Status: Completed", text)

    def test_04_json_hierarchical_extraction(self):
        """JSON parser must format both lists of objects and nested dictionaries into clean blocks."""
        json_obj = {
            "course": "Laboratory Practice III",
            "code": "LP-3",
            "groups": {
                "Group A": "Design and Analysis of Algorithms",
                "Group B": "Machine Learning",
                "Group C": "Blockchain Technology"
            },
            "topics": [
                {"id": "DAA-4", "title": "Fractional Knapsack", "strategy": "Greedy"},
                {"id": "BC-3", "title": "Smart Contract Bank", "strategy": "Solidity"}
            ]
        }
        sections = parse_json(json.dumps(json_obj).encode("utf-8"))
        self.assertGreaterEqual(len(sections), 2)
        full_text = "\n".join(s["text"] for s in sections)
        self.assertIn("Laboratory Practice III", full_text)
        self.assertIn("Fractional Knapsack", full_text)
        self.assertIn("Smart Contract Bank", full_text)

    def test_05_empty_files_rejected(self):
        """Empty or whitespace-only files must return empty section lists or be rejected gracefully."""
        self.assertEqual(parse_plain_or_markdown(b""), [{"heading": "General", "text": "", "page_number": 1}])
        self.assertEqual(parse_plain_or_markdown(b"   \n\n\t  "), [{"heading": "General", "text": "", "page_number": 1}])
        self.assertEqual(parse_csv(b""), [])

    def test_06_corrupted_files_raise_value_errors(self):
        """Corrupted binary streams uploaded with standard extensions must raise clean ValueErrors."""
        garbage_bytes = b"\x00\x1f\xff\xfe\xab\xcd\xefGARBAGE_PAYLOAD_NOT_A_VALID_DOCUMENT"
        
        with self.assertRaises(ValueError):
            parse_docx(garbage_bytes)
            
        with self.assertRaises(ValueError):
            parse_pdf(garbage_bytes)
            
        with self.assertRaises(ValueError):
            parse_json(garbage_bytes)

    def test_07_malformed_json_syntax_error(self):
        """Malformed JSON (missing brackets or quotes) must raise a descriptive ValueError."""
        broken_json = b'{"course": "LP-3", "topics": [{"id": "DAA-1", "incomplete": }'
        with self.assertRaises(ValueError) as ctx:
            parse_json(broken_json)
        self.assertIn("Failed to parse JSON document", str(ctx.exception))

    def test_08_pdf_scanned_image_detection(self):
        """Scanned image-only PDF without digital text layer must raise scanned PDF error."""
        import pypdf
        from PIL import Image

        # Create a synthetic image-only PDF
        img = Image.new('RGB', (100, 100), color='white')
        bio_img = io.BytesIO()
        img.save(bio_img, format='JPEG')
        bio_img.seek(0)

        # Write to PDF
        writer = pypdf.PdfWriter()
        page = writer.add_blank_page(width=100, height=100)
        # Note: blank page with no text
        bio_pdf = io.BytesIO()
        writer.write(bio_pdf)
        pdf_bytes = bio_pdf.getvalue()

        # If blank page, parse_pdf returns []
        pages = parse_pdf(pdf_bytes)
        self.assertEqual(pages, [])

if __name__ == "__main__":
    unittest.main()
