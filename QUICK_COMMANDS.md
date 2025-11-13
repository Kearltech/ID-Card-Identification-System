# 📋 Quick Command Reference

## 🚀 Essential Commands

### 1. Activate Virtual Environment
```powershell
& "C:/Users/Hp/Desktop/mobile_dev/ML/PRINCE_SETSOFIA_KETENI_PUIT22210063/.venv/Scripts/Activate.ps1"
```

### 2. Navigate to Project
```powershell
cd C:\Users\Hp\Desktop\mobile_dev\ml\Id_card_image_extracted-main
```

### 3. Install Dependencies (If Needed)
```powershell
pip install -r requirements_py313.txt
```

### 4. Run the Application ⭐
```powershell
python -m streamlit run src/app_enhanced.py
```

**Then open**: http://localhost:8502

---

## 🛠️ Useful Commands

### Run on Different Port
```powershell
python -m streamlit run src/app_enhanced.py --server.port 8503
```

### Run Tests
```powershell
pip install -r requirements-dev.txt
pytest tests/test_suite.py -v
```

### Run Demo Script
```powershell
python example_complete.py path/to/id_card.jpg
```

### Check Installation
```powershell
pip list | findstr streamlit easyocr numpy
```

### Clear Pip Cache
```powershell
pip cache purge
```

### Reinstall All Dependencies
```powershell
pip install -r requirements_py313.txt --force-reinstall
```

---

## 📍 Important Paths

```
Project Root:
C:\Users\Hp\Desktop\mobile_dev\ml\Id_card_image_extracted-main

Virtual Environment:
C:\Users\Hp\Desktop\mobile_dev\ML\PRINCE_SETSOFIA_KETENI_PUIT22210063\.venv

Application Files:
- src/app_enhanced.py        (Main Streamlit app)
- src/advanced_ocr.py        (OCR engine)
- src/comparison_engine.py   (Field comparison)
- src/user_verification.py   (Form validation)

Configuration:
- .env.example              (Template)
- requirements_py313.txt    (Dependencies)

Documentation:
- SETUP_GUIDE.md
- INSTALLATION_REPORT.md
- ENHANCEMENT_GUIDE.md
- README_ENHANCED.md
- COMPLETION_CHECKLIST.md
- SUCCESS.md
- QUICK_COMMANDS.md (this file)
```

---

## 🌐 Application URLs

| URL | Purpose |
|-----|---------|
| http://localhost:8502 | Main app (default) |
| http://192.168.100.14:8502 | Network access |
| http://localhost:8503 | Alternative port |

---

## 📦 Requirements Files

```powershell
# Use this one (Python 3.13 optimized):
pip install -r requirements_py313.txt

# Alternative (simplified):
pip install -r requirements_simple.txt

# Original (may have issues with Python 3.13):
pip install -r requirements.txt

# Development tools (for testing):
pip install -r requirements-dev.txt
```

---

## ✅ Verify Installation

```powershell
# Check Python version
python --version
# Expected: Python 3.13.3

# Check Streamlit installed
python -c "import streamlit; print(streamlit.__version__)"
# Expected: 1.51.0 or higher

# Check key packages
python -c "import cv2, easyocr, torch; print('All OK!')"
# Expected: All OK!
```

---

## 🎯 Common Workflows

### Workflow 1: Start Fresh
```powershell
cd C:\Users\Hp\Desktop\mobile_dev\ml\Id_card_image_extracted-main
python -m streamlit run src/app_enhanced.py
# Open: http://localhost:8502
```

### Workflow 2: Run Tests
```powershell
cd C:\Users\Hp\Desktop\mobile_dev\ml\Id_card_image_extracted-main
pip install -r requirements-dev.txt
pytest tests/test_suite.py -v
```

### Workflow 3: Run Demo
```powershell
cd C:\Users\Hp\Desktop\mobile_dev\ml\Id_card_image_extracted-main
python example_complete.py C:\path\to\id_card.jpg
```

### Workflow 4: Use Different Port
```powershell
python -m streamlit run src/app_enhanced.py --server.port 8503
# Open: http://localhost:8503
```

---

## 🔧 Troubleshooting Commands

### If module not found:
```powershell
pip install -r requirements_py313.txt --force-reinstall
```

### If port in use:
```powershell
# Use different port
python -m streamlit run src/app_enhanced.py --server.port 8503

# Or check what's using port
netstat -ano | findstr :8502
```

### If Streamlit hangs:
```powershell
# Stop current process (Ctrl+C), then:
pip cache purge
python -m streamlit run src/app_enhanced.py --logger.level=debug
```

### Check dependencies:
```powershell
pip show streamlit easyocr opencv-python-headless
```

---

## 💾 Data Files

```
Database:
outputs/id_cards.db

Exports:
outputs/id_cards.csv

Portraits:
outputs/portraits/[timestamp]_portrait.jpg

Cache:
outputs/cache/

Logs:
outputs/logs/
```

---

## 📖 Documentation Commands

```powershell
# View setup guide
Get-Content SETUP_GUIDE.md

# View installation report
Get-Content INSTALLATION_REPORT.md

# View enhancement guide
Get-Content ENHANCEMENT_GUIDE.md

# View quick reference
Get-Content README_ENHANCED.md
```

---

## 🎓 Learning Resources

| Command | Purpose |
|---------|---------|
| `python example_complete.py --help` | Show demo options |
| `pytest tests/test_suite.py -v` | Run all tests |
| `pytest tests/test_suite.py::TestComparisonEngine -v` | Run specific test class |
| `pytest tests/test_suite.py --cov=src` | Show coverage report |

---

## 📊 Status Check Commands

```powershell
# Check if Streamlit is running
netstat -ano | findstr :8502

# Check Python version
python --version

# Check pip version
pip --version

# List all installed packages
pip list

# Check specific package
pip show streamlit
```

---

## 🚀 Quick Start (Copy & Paste)

```powershell
# Activate environment
& "C:/Users/Hp/Desktop/mobile_dev/ML/PRINCE_SETSOFIA_KETENI_PUIT22210063/.venv/Scripts/Activate.ps1"

# Go to project
cd C:\Users\Hp\Desktop\mobile_dev\ml\Id_card_image_extracted-main

# Install dependencies (if needed)
pip install -r requirements_py313.txt

# Start app
python -m streamlit run src/app_enhanced.py

# Open browser to: http://localhost:8502
```

---

## 🆘 Emergency Reset

```powershell
# Clear all cache
pip cache purge

# Reinstall everything
pip install -r requirements_py313.txt --force-reinstall --no-cache-dir

# Start fresh
python -m streamlit run src/app_enhanced.py --logger.level=debug
```

---

## ✨ Pro Tips

- Use `requirements_py313.txt` for best results with Python 3.13
- Use `python -m streamlit` instead of just `streamlit`
- Different port for multiple instances: `--server.port 8503`
- Debug mode: `--logger.level=debug`
- Headless mode: `--server.headless true`

---

**Quick Reference Created**: November 13, 2025  
**Python**: 3.13.3  
**Status**: ✅ Ready to use

