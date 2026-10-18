#!/usr/bin/env python3
"""Generate sample invoice/receipt images for testing."""

from PIL import Image, ImageDraw, ImageFont
import os

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "data", "samples")
os.makedirs(SAMPLES_DIR, exist_ok=True)

def create_sample_image(filename, text_lines, width=800, height=600):
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    y = 50
    for i, line in enumerate(text_lines):
        f = font if i < 3 else font_small
        draw.text((50, y), line, fill='black', font=f)
        y += 40
    
    img.save(os.path.join(SAMPLES_DIR, filename))
    print(f"Created {filename}")

# Sample Invoice
create_sample_image("invoice_001.png", [
    "INVOICE",
    "TechSoft Solutions Inc.",
    "123 Developer Ave, San Francisco, CA 94102",
    "",
    "Bill To:",
    "Freelancer Design Studio",
    "456 Creative Blvd, Austin, TX 78701",
    "",
    "Invoice #: INV-2024-0142",
    "Date: 2024-01-15",
    "Due Date: 2024-02-14",
    "",
    "Description: Annual SaaS Subscription - Pro Plan",
    "Amount: $299.00",
    "",
    "Total: $299.00",
    "Thank you for your business!",
])

# Sample Receipt
create_sample_image("receipt_001.png", [
    "RECEIPT",
    "Amazon Web Services",
    "410 Terry Ave N, Seattle, WA 98109",
    "",
    "Transaction ID: AWS-2024-03-15-008921",
    "Date: 2024-03-15 14:32:18",
    "",
    "EC2 t3.medium (US-East-1)",
    "  730 hours @ $0.0416/hr  $30.37",
    "Data Transfer",
    "  50 GB @ $0.09/GB      $4.50",
    "",
    "Subtotal: $34.87",
    "Tax: $0.00",
    "Total: $34.87",
    "",
    "Card ending in 4242",
    "Auth: 123456",
])

# Sample Restaurant Receipt
create_sample_image("receipt_002.png", [
    "THE CODING CAFE",
    "789 Startup Street, Seattle, WA",
    "Tel: (555) 123-4567",
    "",
    "Date: 2024-02-20 12:45 PM",
    "Receipt #: 002341",
    "",
    "1x Latte                $5.50",
    "1x Avocado Toast       $12.00",
    "1x Chicken Salad       $14.50",
    "",
    "Subtotal: $32.00",
    "Tax (10.1%): $3.23",
    "Tip: $6.00",
    "Total: $41.23",
    "",
    "Visa **** 4242",
    "Approval: 789012",
])

# Sample Office Supply Receipt
create_sample_image("receipt_003.png", [
    "OFFICE DEPOT",
    "Store #1234",
    "321 Business Park Dr",
    "",
    "03/10/2024  10:15 AM",
    "Transaction: 5678901234",
    "",
    "HP LaserJet Paper 500ct  $12.99",
    "Post-it Notes 12pk       $8.99",
    "Sharpie Markers 4pk      $6.49",
    "",
    "Subtotal: $28.47",
    "Tax: $2.56",
    "Total: $31.03",
    "",
    "Mastercard **** 1234",
])

print("\nAll samples created in", SAMPLES_DIR)