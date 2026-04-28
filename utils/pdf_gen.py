from fpdf import FPDF
import datetime

class QuotePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'QUOTATION', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def generate_quote_pdf(
    product_name, model, price, quantity, unit,
    payment, delivery, validity, shipping,
    company_name="[Your Company]",
    contact_name="[Your Name]",
    email="[email@example.com]",
    phone="[+86-xxx-xxxxxxx]"
):
    """生成PDF报价单"""
    
    pdf = QuotePDF()
    pdf.add_page()
    
    total = price * quantity
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Quote Details', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 10)
    
    items = [
        ('Product Name:', product_name),
        ('Model/Spec:', model or 'N/A'),
        ('Unit Price:', f'${price:.2f} USD'),
        ('Quantity:', f'{quantity} {unit}'),
        ('Total Value:', f'${total:.2f} USD'),
    ]
    
    for label, value in items:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(50, 8, label, 0, 0, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, value, 0, 1, 'L')
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Trade Terms', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 10)
    terms = [
        ('Payment Terms:', payment),
        ('Delivery Time:', delivery),
        ('Valid Until:', validity),
        ('Shipping Port:', shipping),
    ]
    
    for label, value in terms:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(50, 8, label, 0, 0, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, value, 0, 1, 'L')
    
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Company Info', 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 10)
    info = [
        ('Company:', company_name),
        ('Contact:', contact_name),
        ('Email:', email),
        ('Phone:', phone),
        ('Date:', datetime.datetime.now().strftime('%Y-%m-%d')),
    ]
    
    for label, value in info:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(30, 7, label, 0, 0, 'L')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 7, value, 0, 1, 'L')
    
    pdf.ln(15)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(0, 6, 'Thank you for your inquiry! Please feel free to contact us if you have any questions.')
    
    return pdf.output(dest='S').encode('latin-1')


def generate_invoice_pdf(items, total, company_info):
    """生成PDF发票"""
    pdf = QuotePDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'INVOICE', 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 10)
    for label, value in company_info.items():
        pdf.cell(50, 8, f'{label}: {value}', 0, 1, 'L')
    
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(80, 8, 'Description', 1, 0, 'C')
    pdf.cell(30, 8, 'Quantity', 1, 0, 'C')
    pdf.cell(30, 8, 'Amount', 1, 1, 'C')
    
    pdf.set_font('Arial', '', 10)
    for item, qty, amount in items:
        pdf.cell(80, 8, item, 1, 0, 'L')
        pdf.cell(30, 8, str(qty), 1, 0, 'C')
        pdf.cell(30, 8, f'${amount}', 1, 1, 'C')
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(110, 8, 'Total:', 1, 0, 'R')
    pdf.cell(30, 8, f'${total}', 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')