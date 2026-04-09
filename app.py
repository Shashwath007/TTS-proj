import os
import uuid
import platform
import shutil
import pytesseract
from flask import Flask, request, jsonify, render_template, send_from_directory

# Auto-detect tesseract path
tesseract_path = shutil.which('tesseract')
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
elif platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
AUDIO_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'audio')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def latex_to_speakable(text):
    """Convert LaTeX math notation to human-readable spoken text."""
    replacements = [
        (r'\frac',        'fraction'),
        (r'\sqrt',        'square root of'),
        (r'\int',         'integral of'),
        (r'\sum',         'summation of'),
        (r'\prod',        'product of'),
        (r'\lim',         'limit of'),
        (r'\infty',       'infinity'),
        (r'\alpha',       'alpha'),
        (r'\beta',        'beta'),
        (r'\gamma',       'gamma'),
        (r'\delta',       'delta'),
        (r'\theta',       'theta'),
        (r'\lambda',      'lambda'),
        (r'\mu',          'mu'),
        (r'\sigma',       'sigma'),
        (r'\pi',          'pi'),
        (r'\omega',       'omega'),
        (r'\times',       'times'),
        (r'\div',         'divided by'),
        (r'\leq',         'less than or equal to'),
        (r'\geq',         'greater than or equal to'),
        (r'\neq',         'not equal to'),
        (r'\approx',      'approximately equal to'),
        (r'\rightarrow',  'approaches'),
        (r'\leftarrow',   'left arrow'),
        (r'\cdot',        'dot'),
        (r'\pm',          'plus or minus'),
        (r'\log',         'log'),
        (r'\ln',          'natural log'),
        (r'\sin',         'sine'),
        (r'\cos',         'cosine'),
        (r'\tan',         'tangent'),
        (r'\vec',         'vector'),
        (r'\hat',         'hat'),
        (r'^',            ' to the power of '),
        (r'_',            ' subscript '),
        (r'{',            ''),
        (r'}',            ''),
        (r'\\',           ' '),
    ]
    for latex, spoken in replacements:
        text = text.replace(latex, spoken)
    return text.strip()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    try:
        import cv2
        import numpy as np
        from gtts import gTTS
        from PIL import Image

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded.'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected.'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload JPG, PNG, or BMP only.'}), 400

        file_id = str(uuid.uuid4())
        ext = file.filename.rsplit('.', 1)[1].lower()
        img_path = os.path.join(UPLOAD_FOLDER, f'{file_id}.{ext}')
        mp3_filename = f'{file_id}.mp3'
        mp3_path = os.path.join(AUDIO_FOLDER, mp3_filename)

        file.save(img_path)

        mode = request.form.get('mode', 'text')

        if mode == 'math':
            # Use Tesseract with math-optimized settings
            img = cv2.imread(img_path)
            if img is None:
                return jsonify({'success': False, 'error': 'Could not read image file.'}), 400
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Higher resolution preprocessing for math
            scale = 2
            enlarged = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            blurred = cv2.medianBlur(enlarged, 3)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            pil_image = Image.fromarray(thresh)
            # PSM 6 = assume uniform block of text, good for equations
            custom_config = r'--oem 3 --psm 6'
            raw_text = pytesseract.image_to_string(pil_image, config=custom_config)
            text = latex_to_speakable(raw_text.strip())
            raw_latex = raw_text.strip()
        else:
            img = cv2.imread(img_path)
            if img is None:
                return jsonify({'success': False, 'error': 'Could not read image file.'}), 400

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.medianBlur(gray, 3)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            pil_image = Image.fromarray(thresh)
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(pil_image, config=custom_config)
            text = text.strip()
            raw_latex = None

        if not text:
            return jsonify({'success': False, 'error': 'No text detected in image. Try a clearer image.'}), 400

        os.remove(img_path)

        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(mp3_path)

        word_count = len(text.split())
        char_count = len(text)
        audio_url = f'/audio/{mp3_filename}'

        response_data = {
            'success': True,
            'text': text,
            'audio_url': audio_url,
            'word_count': word_count,
            'char_count': char_count,
            'mode': mode
        }

        if raw_latex:
            response_data['latex'] = raw_latex

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
