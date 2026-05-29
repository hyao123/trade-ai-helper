"""
utils/pdf_gen.py — 报价单 PDF 生成（支持多产品 SKU）

中文支持策略：
  优先使用 fpdf2 内置的 DejaVu Unicode 字体。
  若需要完整 CJK 支持，可在 /fonts/ 目录放置 NotoSansSC-Regular.ttf，
  程序会自动检测并优先使用。
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path

from fpdf import FPDF

from utils.logger import get_logger

logger = get_logger("pdf_gen")

# ---------------------------------------------------------------------------
# 字体配置
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).resolve().parent
_FONT_DIR = _BASE_DIR.parent / "fonts"
_CORE_FONT_NAMES = {"arial", "helvetica", "times", "courier", "symbol", "zapfdingbats"}


def _existing_path(path: Path | None) -> str | None:
    """Return a string path only when the font file exists."""
    return str(path) if path and path.exists() else None


def _register_font_family(
    pdf: FPDF,
    family: str,
    regular_path: Path,
    bold_path: Path | None = None,
    italic_path: Path | None = None,
    bold_italic_path: Path | None = None,
) -> bool:
    """Register regular/bold/italic aliases for a Unicode font family."""
    regular = _existing_path(regular_path)
    if not regular:
        return False

    try:
        pdf.add_font(family, "", regular)
        pdf.add_font(family, "B", _existing_path(bold_path) or regular)
        pdf.add_font(family, "I", _existing_path(italic_path) or regular)
        pdf.add_font(
            family,
            "BI",
            _existing_path(bold_italic_path) or _existing_path(bold_path) or regular,
        )
        return True
    except Exception as exc:
        logger.warning("Unable to register PDF font %s: %s", family, exc)
        return False


def _font_candidates() -> list[tuple[str, Path, Path | None, Path | None, Path | None]]:
    """Return bundled and common system Unicode font candidates."""
    return [
        (
            "NotoSans",
            _FONT_DIR / "NotoSansSC-Regular.ttf",
            _FONT_DIR / "NotoSansSC-Bold.ttf",
            None,
            None,
        ),
        (
            "DejaVu",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf"),
        ),
        (
            "DejaVu",
            Path("/usr/local/share/fonts/DejaVuSans.ttf"),
            Path("/usr/local/share/fonts/DejaVuSans-Bold.ttf"),
            Path("/usr/local/share/fonts/DejaVuSans-Oblique.ttf"),
            Path("/usr/local/share/fonts/DejaVuSans-BoldOblique.ttf"),
        ),
    ]


def _setup_font(pdf: FPDF) -> str:
    """
    注册字体并返回字体名称。
    优先级：项目 fonts/ 中的 NotoSansSC > 常见系统 DejaVu > Arial（ASCII兜底）
    """
    for family, regular, bold, italic, bold_italic in _font_candidates():
        if _register_font_family(pdf, family, regular, bold, italic, bold_italic):
            return family

    return "Arial"


def _uses_core_font(font_name: str) -> bool:
    """Return True when fpdf will use a Latin-1 core font."""
    return font_name.lower() in _CORE_FONT_NAMES


def _placeholder(font_name: str) -> str:
    """Return a missing-value placeholder supported by the active font."""
    return "-" if _uses_core_font(font_name) else "—"


def _pdf_text(font_name: str, value: object, fallback: str | None = None) -> str:
    """Normalize text so core-font fallback never raises Unicode encoding errors."""
    text = str(value) if value not in (None, "") else (fallback or _placeholder(font_name))
    if _uses_core_font(font_name):
        return text.encode("latin-1", errors="replace").decode("latin-1")
    return text


# ---------------------------------------------------------------------------
# PDF 类
# ---------------------------------------------------------------------------
class QuotePDF(FPDF):
    def __init__(self, font_name: str = "Arial", company: str = "", logo_path: str | None = None):
        super().__init__()
        self._font_name = font_name
        self._company   = company
        self._logo_path = logo_path

    def header(self):
        # 渐变色装饰条（用矩形模拟）
        self.set_fill_color(30, 58, 95)
        self.rect(0, 0, 210, 18, "F")
        # Logo (if available) - constrain to 45x14mm box to prevent overflow
        if self._logo_path and os.path.exists(self._logo_path):
            try:
                self.image(self._logo_path, x=5, y=2, w=45, h=14, keep_aspect_ratio=True)
            except Exception:
                pass  # Gracefully handle corrupted/unreadable image files
        self.set_text_color(255, 255, 255)
        self.set_font(self._font_name, "B", 14)
        self.set_y(3)
        self.cell(0, 12, "QUOTATION", 0, 0, "C")
        if self._company:
            self.set_font(self._font_name, "", 8)
            self.set_y(3)
            self.cell(0, 12, _pdf_text(self._font_name, self._company), 0, 0, "R")
        self.set_text_color(0, 0, 0)
        self.ln(18)

    def footer(self):
        self.set_y(-13)
        self.set_fill_color(243, 244, 246)
        self.rect(0, self.get_y(), 210, 13, "F")
        self.set_font(self._font_name, "I", 8)
        self.set_text_color(107, 114, 128)
        self.cell(0, 10, f"Page {self.page_no()}  |  Generated by TradeAI Pro", 0, 0, "C")
        self.set_text_color(0, 0, 0)


# ---------------------------------------------------------------------------
# 辅助：section 标题
# ---------------------------------------------------------------------------
def _section(pdf: FPDF, font_name: str, title: str) -> None:
    pdf.set_fill_color(239, 246, 255)
    pdf.set_font(font_name, "B", 11)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 8, _pdf_text(font_name, f"  {title}"), 0, 1, "L", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _truncate_by_width(pdf: FPDF, font_name: str, text: str, max_mm: float) -> str:
    """
    按渲染宽度截断字符串，避免 CJK/混合字符溢出。
    使用 fpdf2 的 get_string_width() 而非字符数，确保视觉宽度正确。
    """
    text = _pdf_text(font_name, text, fallback="")
    if not text:
        return text
    pdf.set_font(font_name, "", 9)
    if pdf.get_string_width(text) <= max_mm:
        return text
    # 逐字符缩减直到满足宽度
    ellipsis = "..." if _uses_core_font(font_name) else "…"
    for i in range(len(text) - 1, 0, -1):
        candidate = text[:i] + ellipsis
        if pdf.get_string_width(candidate) <= max_mm:
            return candidate
    return ellipsis


def _row(pdf: FPDF, font_name: str, label: str, value: str,
         label_w: int = 45, row_h: int = 7) -> None:
    pdf.set_font(font_name, "B", 9)
    pdf.set_text_color(107, 114, 128)
    pdf.cell(label_w, row_h, label, 0, 0, "L")
    pdf.set_font(font_name, "", 9)
    pdf.set_text_color(17, 24, 39)
    pdf.cell(0, row_h, _pdf_text(font_name, value), 0, 1, "L")
    pdf.set_text_color(0, 0, 0)


# ---------------------------------------------------------------------------
# 主入口：支持多产品 SKU
# ---------------------------------------------------------------------------
def generate_quote_pdf(
    skus: list[dict],
    payment: str = "T/T 30%",
    delivery: str = "15-20 days",
    validity: str = "30 days",
    shipping: str = "",
    company_name: str = "[Your Company]",
    contact_name: str = "[Your Name]",
    email: str = "[email@example.com]",
    phone: str = "[+86-xxx-xxxxxxx]",
    buyer_company: str = "",
    buyer_contact: str = "",
    buyer_email: str = "",
    logo_path: str | None = None,
) -> bytes:
    """
    生成多产品 PDF 报价单，返回字节流。

    skus: list of dict，每条包含 product / model / price / quantity / unit
    buyer_*: 可选的客户（收单方）信息
    logo_path: 可选的公司 Logo 图片路径
    """
    # Guard against invalid logo_path
    if logo_path and not os.path.exists(logo_path):
        logger.warning("Logo file not found: %s", logo_path)
        logo_path = None

    logger.info("Generating PDF: %d SKUs", len(skus))

    pdf = QuotePDF(company=company_name, logo_path=logo_path)
    font_name = _setup_font(pdf)
    pdf._font_name = font_name

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    # ── 报价日期 ──────────────────────────────────────
    pdf.set_font(font_name, "", 9)
    pdf.set_text_color(107, 114, 128)
    pdf.cell(0, 6, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d')}", 0, 1, "R")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # ── 产品明细表 ────────────────────────────────────
    _section(pdf, font_name, "Product Details")

    # 表头
    COL = [70, 35, 22, 22, 20, 21]  # 宽度列表
    HEADERS = ["Product Name", "Model/Spec", "Unit Price", "Qty", "Unit", "Amount"]
    pdf.set_fill_color(30, 58, 95)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_name, "B", 9)
    for w, h in zip(COL, HEADERS):
        pdf.cell(w, 8, h, 0, 0, "C", fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # 行数据
    grand_total = 0.0
    fill = False
    for sku in skus:
        name     = sku.get("product", "")
        model    = sku.get("model", "")
        price    = float(sku.get("price", 0))
        quantity = int(sku.get("quantity", 0))
        unit     = sku.get("unit", "PCS")
        amount   = price * quantity
        grand_total += amount

        # 截断过长文本防止溢出（按渲染宽度截断，兼容 CJK/混合字符）
        name  = _truncate_by_width(pdf, font_name, name,  max_mm=68)
        model = _truncate_by_width(pdf, font_name, model, max_mm=33)

        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_font(font_name, "", 9)
        row_data = [
            name, model,
            f"${price:.2f}", str(quantity), unit,
            f"${amount:,.2f}",
        ]
        for w, val in zip(COL, row_data):
            pdf.cell(w, 7, _pdf_text(font_name, val), 0, 0, "C" if w <= 35 else "L", fill=True)
        pdf.ln()
        fill = not fill

    # 合计行
    pdf.set_fill_color(30, 58, 95)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_name, "B", 10)
    total_label_w = sum(COL[:-1])
    pdf.cell(total_label_w, 9, "  GRAND TOTAL", 0, 0, "L", fill=True)
    pdf.cell(COL[-1], 9, f"${grand_total:,.2f}", 0, 1, "C", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # ── 交易条款 ──────────────────────────────────────
    _section(pdf, font_name, "Trade Terms")
    _row(pdf, font_name, "Payment Terms:", payment)
    _row(pdf, font_name, "Delivery Time:", delivery)
    _row(pdf, font_name, "Validity:",      validity)
    _row(pdf, font_name, "Shipping Port:", shipping)
    pdf.ln(4)

    # ── 客户信息（Buyer）──────────────────────────────
    if buyer_company or buyer_contact or buyer_email:
        _section(pdf, font_name, "Buyer Information")
        if buyer_company:
            _row(pdf, font_name, "Company:",  buyer_company)
        if buyer_contact:
            _row(pdf, font_name, "Contact:",  buyer_contact)
        if buyer_email:
            _row(pdf, font_name, "Email:",    buyer_email)
        pdf.ln(4)

    # ── 公司信息（Seller）────────────────────────────
    _section(pdf, font_name, "Seller Information")
    _row(pdf, font_name, "Company:",  company_name)
    _row(pdf, font_name, "Contact:",  contact_name)
    _row(pdf, font_name, "Email:",    email)
    _row(pdf, font_name, "Phone:",    phone)
    pdf.ln(6)

    # ── 免责声明 ──────────────────────────────────────
    pdf.set_font(font_name, "I", 8)
    pdf.set_text_color(156, 163, 175)
    pdf.multi_cell(
        0, 5,
        "This quotation is valid for the period stated above. Prices are subject to change "
        "without notice after the validity period. Thank you for your business!",
    )

    result = bytes(pdf.output())
    logger.info("PDF generated: %d bytes", len(result))
    return result
