import os
import uuid
import platform
import shutil
import sqlite3
import hashlib
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for

# Auto-detect tesseract path
import pytesseract
tesseract_path = shutil.which('tesseract')
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
elif platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
AUDIO_FOLDER  = os.path.join(os.path.dirname(__file__), 'static', 'audio')
DB_PATH       = os.path.join(os.path.dirname(__file__), 'users.db')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER,  exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f'{salt}:{hashed}'


def verify_password(stored, provided):
    try:
        salt, hashed = stored.split(':')
        return hashlib.sha256((salt + provided).encode()).hexdigest() == hashed
    except Exception:
        return False


def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                is_admin      INTEGER DEFAULT 0,
                created_at    TEXT    NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                mode       TEXT    NOT NULL,
                word_count INTEGER,
                char_count INTEGER,
                created_at TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

        # Create admin user if not exists
        ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'Shashwath007')
        ADMIN_EMAIL    = os.environ.get('ADMIN_EMAIL',    'shashwath@voicedoc.com')
        ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@1234')

        existing = conn.execute('SELECT id FROM users WHERE username = ?', (ADMIN_USERNAME,)).fetchone()
        if not existing:
            conn.execute(
                'INSERT INTO users (username, email, password_hash, is_admin, created_at) VALUES (?, ?, ?, 1, ?)',
                (ADMIN_USERNAME, ADMIN_EMAIL, hash_password(ADMIN_PASSWORD), datetime.utcnow().isoformat())
            )
            conn.commit()


init_db()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def latex_to_speakable(text):
    replacements = [
        (r'\frac', 'fraction'), (r'\sqrt', 'square root of'),
        (r'\int', 'integral of'), (r'\sum', 'summation of'),
        (r'\prod', 'product of'), (r'\lim', 'limit of'),
        (r'\infty', 'infinity'), (r'\alpha', 'alpha'),
        (r'\beta', 'beta'), (r'\gamma', 'gamma'),
        (r'\delta', 'delta'), (r'\theta', 'theta'),
        (r'\lambda', 'lambda'), (r'\mu', 'mu'),
        (r'\sigma', 'sigma'), (r'\pi', 'pi'),
        (r'\omega', 'omega'), (r'\times', 'times'),
        (r'\div', 'divided by'), (r'\leq', 'less than or equal to'),
        (r'\geq', 'greater than or equal to'), (r'\neq', 'not equal to'),
        (r'\approx', 'approximately equal to'), (r'\rightarrow', 'approaches'),
        (r'\cdot', 'dot'), (r'\pm', 'plus or minus'),
        (r'\log', 'log'), (r'\ln', 'natural log'),
        (r'\sin', 'sine'), (r'\cos', 'cosine'), (r'\tan', 'tangent'),
        (r'^', ' to the power of '), (r'_', ' subscript '),
        (r'{', ''), (r'}', ''), (r'\\', ' '),
    ]
    for latex, spoken in replacements:
        text = text.replace(latex, spoken)
    return text.strip()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        data     = request.get_json()
        email    = data.get('email', '').strip().lower()
        password = data.get('password', '')
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required.'}), 400
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user or not verify_password(user['password_hash'], password):
            return jsonify({'success': False, 'error': 'Invalid email or password.'}), 401
        session['user_id']  = user['id']
        session['username'] = user['username']
        session['email']    = user['email']
        return jsonify({'success': True, 'redirect': url_for('index')})
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        data     = request.get_json()
        username = data.get('username', '').strip()
        email    = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm  = data.get('confirm_password', '')
        if not username or not email or not password:
            return jsonify({'success': False, 'error': 'All fields are required.'}), 400
        if len(username) < 3:
            return jsonify({'success': False, 'error': 'Username must be at least 3 characters.'}), 400
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters.'}), 400
        if password != confirm:
            return jsonify({'success': False, 'error': 'Passwords do not match.'}), 400
        if '@' not in email:
            return jsonify({'success': False, 'error': 'Invalid email address.'}), 400
        try:
            with get_db() as conn:
                conn.execute(
                    'INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                    (username, email, hash_password(password), datetime.utcnow().isoformat())
                )
                conn.commit()
                user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['email']    = user['email']
            return jsonify({'success': True, 'redirect': url_for('index')})
        except sqlite3.IntegrityError as e:
            if 'username' in str(e):
                return jsonify({'success': False, 'error': 'Username already taken.'}), 400
            if 'email' in str(e):
                return jsonify({'success': False, 'error': 'Email already registered.'}), 400
            return jsonify({'success': False, 'error': 'Registration failed.'}), 400
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session.get('username'))


@app.route('/convert', methods=['POST'])
@login_required
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

        file_id      = str(uuid.uuid4())
        ext          = file.filename.rsplit('.', 1)[1].lower()
        img_path     = os.path.join(UPLOAD_FOLDER, f'{file_id}.{ext}')
        mp3_filename = f'{file_id}.mp3'
        mp3_path     = os.path.join(AUDIO_FOLDER, mp3_filename)
        file.save(img_path)

        mode = request.form.get('mode', 'text')

        if mode == 'math':
            img = cv2.imread(img_path)
            if img is None:
                return jsonify({'success': False, 'error': 'Could not read image file.'}), 400
            gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            enlarged  = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            blurred   = cv2.medianBlur(enlarged, 3)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            pil_image = Image.fromarray(thresh)
            raw_text  = pytesseract.image_to_string(pil_image, config=r'--oem 3 --psm 6')
            text      = latex_to_speakable(raw_text.strip())
            raw_latex = raw_text.strip()
        else:
            img = cv2.imread(img_path)
            if img is None:
                return jsonify({'success': False, 'error': 'Could not read image file.'}), 400
            gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred   = cv2.medianBlur(gray, 3)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            pil_image = Image.fromarray(thresh)
            text      = pytesseract.image_to_string(pil_image, config=r'--oem 3 --psm 6').strip()
            raw_latex = None

        if not text:
            return jsonify({'success': False, 'error': 'No text detected in image. Try a clearer image.'}), 400

        os.remove(img_path)
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(mp3_path)

        word_count = len(text.split())
        char_count = len(text)

        with get_db() as conn:
            conn.execute(
                'INSERT INTO conversions (user_id, mode, word_count, char_count, created_at) VALUES (?, ?, ?, ?, ?)',
                (session['user_id'], mode, word_count, char_count, datetime.utcnow().isoformat())
            )
            conn.commit()

        response_data = {
            'success': True, 'text': text,
            'audio_url': f'/audio/{mp3_filename}',
            'word_count': word_count, 'char_count': char_count, 'mode': mode
        }
        if raw_latex:
            response_data['latex'] = raw_latex
        return jsonify(response_data)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/audio/<filename>')
@login_required
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
