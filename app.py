from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import hashlib
import string
import random
from datetime import datetime
import validators

app = Flask(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect('url_shortener.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT NOT NULL,
            short_code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            clicks INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Generate short code
def generate_short_code():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(6))

# Check if short code exists
def short_code_exists(short_code):
    conn = sqlite3.connect('url_shortener.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM urls WHERE short_code = ?', (short_code,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()
    original_url = data.get('url')
    custom_alias = data.get('alias')
    
    # Validate URL
    if not original_url or not validators.url(original_url):
        return jsonify({'error': 'Invalid URL'}), 400
    
    # Generate or use custom short code
    if custom_alias:
        if not all(c.isalnum() or c in ['-', '_'] for c in custom_alias):
            return jsonify({'error': 'Custom alias can only contain letters, numbers, hyphens, and underscores'}), 400
        if short_code_exists(custom_alias):
            return jsonify({'error': 'Custom alias already in use'}), 400
        short_code = custom_alias
    else:
        short_code = generate_short_code()
        while short_code_exists(short_code):
            short_code = generate_short_code()
    
    # Save to database
    conn = sqlite3.connect('url_shortener.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO urls (original_url, short_code) VALUES (?, ?)',
        (original_url, short_code)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'original_url': original_url,
        'short_url': f'{request.host_url}{short_code}'
    })

@app.route('/<short_code>')
def redirect_to_url(short_code):
    conn = sqlite3.connect('url_shortener.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT original_url FROM urls WHERE short_code = ?',
        (short_code,)
    )
    result = cursor.fetchone()
    
    if result:
        original_url = result[0]
        # Update click count
        cursor.execute(
            'UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?',
            (short_code,)
        )
        conn.commit()
        conn.close()
        return redirect(original_url)
    else:
        conn.close()
        return jsonify({'error': 'Short URL not found'}), 404

@app.route('/history')
def get_history():
    conn = sqlite3.connect('url_shortener.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT original_url, short_code, created_at, clicks FROM urls ORDER BY created_at DESC'
    )
    urls = cursor.fetchall()
    conn.close()
    
    history = []
    for url in urls:
        history.append({
            'original_url': url[0],
            'short_url': f'{request.host_url}{url[1]}',
            'created_at': datetime.strptime(url[2], '%Y-%m-%d %H:%M:%S').isoformat(),
            'clicks': url[3]
        })
    
    return jsonify(history)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
