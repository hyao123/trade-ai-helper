"""
pdf_gen.py — 报价单 PDF 生成

中文支持策略：
  优先使用 fpdf2 内置的 DejaVu Unicode 字体（覆盖大部分中文字符）。
  若需要完整 CJK 支持，可在 /fonts/ 目录放置 NotoSansSC-Regular.ttf，
  程序会自动检测并优先使用。
"""

import datetime
import os
from fpdf import FPDF

# ---------------------------------------------------------------------------
# 字体配置
# ---------------------------------------------------------------------------
_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR   = os.path.join(_BASE_DIR, "..", "fonts")
_NOTO_PATH  = os.path.join(_FONT_DIR, "NotoSansSC-Regular.ttf")

def _setup_font(pdf: FPDF) -> str:
    """
    注册字体并返回字体名称。
    优先顺序：NotoSansSC（完整CJK）> DejaVu（内置Unicode）> Arial（ASCII降级）
    """
    if os.path.exists(_NOTO_PATH):
        pdf.add_font("NotoSans", "", _NOTO_PATH, uni=True)
        return "NotoSans"
    # fpdf2 内置 DejaVu，支持大部分 Unicode 及常用中文
    try:
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        return "DejaVu"
    except Exception:
        return "Arial"


# ---------------------------------------------------------------------------
# PDF 类
# ---------------------------------------------------------------------------
class QuotePDF(FPDF):
    def __init__(self, font_name: str = "Arial"):
        super().__init__()
        self._font_name = font_name

    def header(self):
        self.set_font(self._font_name, "B", 16)
        self.cell(0, 10, "QUOTATION", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(self._font_name, "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")


# ---------------------------------------------------------------------------
# 公共辅助：渲染 label + value 行（支持中文）
# ---------------------------------------------------------------------------
def _row(pdf: FPDF, font_name: str, label: str, value: str,
         label_w: int = 50, row_h: int = 8):
    pdf.set_font(font_name, "B", 10)
    pdf.cell(label_w, row_h, label, 0, 0, "L")
    pdf.set_font(font_name, "", 10)
    pdf.cell(0, row_h, str(value) if value else "N/A", 0, 1, "L")


# ---------------------------------------------------------------------------
# 报价单生成
# ---------------------------------------------------------------------------
def generate_quote_pdf(
    product_name: str,
    model: str,
    price: float,
    quantity: int,
    unit: str,
    payment: str,
    delivery: str,
    validity: str,
    shipping: str,
    company_name: str = "[Your Company]",
    contact_name: str = "[Your Name]",
    email: str = "[email@example.com]",
    phone: str = "[+86-xxx-xxxxxxx]",
) -> bytes:
    """生成 PDF 报价单，返回字节流"""

    pdf = QuotePDF()
    font_name = _setup_font(pdf)
    pdf._font_name = font_name  # 供 header/footer 使用

    pdf.add_page()
    total = price * quantity

    # --- 产品详情 ---
    pdf.set_font(font_name, "B", 12)
    pdf.cell(0, 10, "Quote Details", 0, 1, "L")
    pdf.ln(2)

    _row(pdf, font_name, "Product Name:", product_name)
    _row(pdf, font_name, "Model/Spec:",   model or "N/A")
    _row(pdf, font_name, "Unit Price:",   f"${price:.2f} USD")
    _row(pdf, font_name, "Quantity:",     f"{quantity} {unit}")
    _row(pdf, font_name, "Total Value:",  f"${total:.2f} USD")

    pdf.ln(5)

    # --- 交易条款 ---
    pdf.set_font(font_name, "B", 12)
    pdf.cell(0, 10, "Trade Terms", 0, 1, "L")
    pdf.ln(2)

    _row(pdf, font_name, "Payment Terms:", payment)
    _row(pdf, font_name, "Delivery Time:", delivery)
    _row(pdf, font_name, "Valid Until:",   validity)
    _row(pdf, font_name, "Shipping Port:", shipping)

    pdf.ln(10)

    # --- 公司信息 ---
    pdf.set_font(font_name, "B", 12)
    pdf.cell(0, 10, "Company Info", 0, 1, "L")
    pdf.ln(2)

    _row(pdf, font_name, "Company:", company_name, label_w=30, row_h=7)
    _row(pdf, font_name, "Contact:", contact_name, label_w=30, row_h=7)
    _row(pdf, font_name, "Email:",   email,         label_w=30, row_h=7)
    _row(pdf, font_name, "Phone:",   phone,         label_w=30, row_h=7)
    _row(pdf, font_name, "Date:",    datetime.datetime.now().strftime("%Y-%m-%d"), label_w=30, row_h=7)

    pdf.ln(15)
    pdf.set_font(font_name, "I", 9)
    pdf.multi_cell(
        0, 6,
        "Thank you for your inquiry! "
        "Please feel free to contact us if you have any questions."
    )

    return bytes(pdf.output())
