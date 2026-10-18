# Invoice Sorter 🧾

**A local, privacy-first invoice and receipt organizer for freelancers — powered by open-source AI.**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Hacktoberfest](https://img.shields.io/badge/Hacktoberfest-2026-orange.svg)](https://hacktoberfest.com/)

---

## 🎯 Why This Exists

Freelancers deal with dozens of invoices and receipts every month. Existing solutions either:
- **Send your client data to the cloud** (privacy nightmare)
- **Cost monthly subscriptions** (eats into thin margins)
- **Don't work offline** (useless on flights or secure environments)

**Invoice Sorter runs 100% locally on your laptop** using [Ollama](https://ollama.com/) and open-weight models like Llama 3.2. Your financial documents never leave your machine.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔒 **100% Local** | No cloud APIs, no data leaves your machine |
| 🤖 **Open-Source AI** | Uses Ollama with Llama 3.2 (or any model you choose) |
| 📄 **Multi-Format** | Processes PDFs, PNG, JPG, TIFF, BMP |
| 🏷️ **Smart Extraction** | Vendor, amount, date, invoice number, category |
| 📁 **Auto-Organization** | Sort by category, date, vendor, or document type |
| 📊 **Export** | JSON, CSV, Excel for accounting software |
| 💰 **Free Forever** | No subscriptions, no API keys, no limits |

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+**
2. **Ollama** - [Install from ollama.com](https://ollama.com/)
3. **Tesseract OCR** - For image processing
   - Windows: `winget install UB-Mannheim.TesseractOCR`
   - Mac: `brew install tesseract`
   - Linux: `sudo apt install tesseract-ocr`

### Installation

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/invoice-sorter
cd invoice-sorter
pip install -e .

# Pull the AI model (one-time, ~2GB)
ollama pull llama3.2:3b
```

### Usage

```bash
# Process a folder of invoices/receipts
invoice-sorter process ./my-receipts ./organized-output

# Use a different model
invoice-sorter process ./receipts ./output --model llama3.1:8b

# Organize by date instead of category
invoice-sorter process ./receipts ./output --organize-by date

# Export only JSON
invoice-sorter process ./receipts ./output --export json

# Check Ollama connection and models
invoice-sorter check-ollama

# List supported categories
invoice-sorter categories
```

---

## 📂 Output Structure

```
organized-output/
├── sorted/
│   ├── software/
│   │   ├── invoice_001.pdf
│   │   └── receipt_045.png
│   ├── travel/
│   │   └── uber_receipt.jpg
│   └── meals/
│       └── lunch_client.pdf
├── invoices.json      # Full extracted data
├── invoices.csv       # Spreadsheet-ready
├── invoices.xlsx      # Formatted Excel
└── summary.json       # Processing statistics
```

---

## 🛠️ How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Input     │────▶│  Extract    │────▶│   Local     │────▶│  Structured │
│  Documents  │     │   Text      │     │   LLM       │     │   Output    │
│ (PDF/IMG)   │     │ (pdfplumber │     │  (Ollama)   │     │ (JSON/CSV)  │
└─────────────┘     │  /tesseract)│     └─────────────┘     └─────────────┘
                    └─────────────┘
```

1. **Text Extraction**: `pdfplumber` for PDFs, `tesseract` for images
2. **Classification**: Rule-based detection of invoice vs receipt
3. **AI Extraction**: Local LLM extracts structured fields
4. **Organization**: Files copied into categorized folders
5. **Export**: Multiple formats for your workflow

---

## 🔧 Configuration

### Supported Models

Any Ollama-compatible model works. Recommended:

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `llama3.2:3b` | 2 GB | ⚡⚡⚡ | Good |
| `llama3.1:8b` | 4.7 GB | ⚡⚡ | Better |
| `qwen2.5:7b` | 4.4 GB | ⚡⚡ | Good (multilingual) |
| `phi3:3.8b` | 2.2 GB | ⚡⚡⚡ | Decent |

```bash
# Try a different model
ollama pull llama3.1:8b
invoice-sorter process ./in ./out --model llama3.1:8b
```

### Environment Variables

```bash
export OLLAMA_HOST=http://localhost:11434  # Default
export TESSERACT_CMD=/usr/bin/tesseract    # If not in PATH
```

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy src/

# Linting
ruff check src/
```

---

## 📝 Hacktoberfest 2026 Submission

This project was built for **Hacktoberfest 2026 Week 2: Side Hustle Challenge**.

### Why Open Innovation Matters Here

| Closed Approach | Our Open Approach |
|-----------------|-------------------|
| $20-50/month per user | **$0 forever** |
| Client data on vendor servers | **Never leaves your laptop** |
| Vendor controls roadmap | **You choose the model** |
| API rate limits | **Unlimited local inference** |
| Vendor lock-in | **Swap models anytime** |
| No offline use | **Works on airplanes** |

**Real impact**: A freelancer processing 50 receipts/month saves $240-600/year while keeping client financial data completely private. The open-weight model approach makes this business model viable — no API costs means the tool can be free forever.

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a PR

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Ollama](https://ollama.com/) — Making local LLMs accessible
- [Llama 3.2](https://ai.meta.com/blog/llama-3-2/) — Meta's open-weight models
- [pdfplumber](https://github.com/jsvine/pdfplumber) — PDF text extraction
- [Tesseract](https://github.com/tesseract-ocr/tesseract) — OCR engine
- [Hacktoberfest 2026](https://hacktoberfest.com/) — For the motivation to build this

---

## 💬 Feedback & Issues

Found a bug? Have a feature request? [Open an issue](https://github.com/YOUR_USERNAME/invoice-sorter/issues)!

**Built with ❤️ for freelancers everywhere.**