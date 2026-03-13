# VoiceDoc MVP 🎙️

> Upload a printed document image → Extract text via OCR → Listen to it as speech

---

## One-Command Setup

```bash
pip install -r requirements.txt
python app.py
```

Open: [http://localhost:5000](http://localhost:5000)

---

## Tesseract OCR — Required Install

VoiceDoc uses [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — you must install it separately from Python:

**Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install tesseract-ocr -y
```

**macOS (Homebrew):**
```bash
brew install tesseract
```

**Windows:**
Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki  
After installing, add Tesseract to your system PATH, or add this to `app.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

---

## What You'll See at localhost:5000

- A dark, glassmorphism UI with a drag-and-drop upload area
- Animated 3-step progress (Preprocessing → OCR → Audio)
- Extracted text box with copy button
- Custom audio player with seek, speed, volume controls
- Download buttons for MP3 and TXT
- Light/dark mode toggle (saved across sessions)

---

## Top 5 Errors & Exact Fixes

**Error 1: `TesseractNotFoundError`**
```
pytesseract.pytesseract.TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```
Fix: Install Tesseract (see above). Verify with `tesseract --version`.

**Error 2: `ModuleNotFoundError: No module named 'cv2'`**
```
ModuleNotFoundError: No module named 'cv2'
```
Fix: `pip install opencv-python`

**Error 3: `ModuleNotFoundError: No module named 'gtts'`**
```
ModuleNotFoundError: No module named 'gtts'
```
Fix: `pip install gtts`

**Error 4: Port already in use**
```
OSError: [Errno 98] Address already in use
```
Fix: Kill whatever is using port 5000: `kill $(lsof -t -i:5000)` or run on a different port: `python app.py --port 5001` (edit app.py last line).

**Error 5: No text detected in image**
```
{"success": false, "error": "No text detected in image. Try a clearer image."}
```
Fix: Use a high-resolution, well-lit image of printed (not handwritten) text. Avoid blurry or skewed photos.

---

## Tech Stack

| Component | Library |
|-----------|---------|
| Backend   | Flask   |
| Image preprocessing | OpenCV (cv2) |
| OCR engine | Tesseract + pytesseract |
| Text-to-speech | gTTS (Google TTS) |
| Frontend | Vanilla HTML/CSS/JS |
| Fonts | Google Fonts (Syne, DM Mono, DM Sans) |
