import os
import re
import time
import base64
import urllib.parse
import threading
import subprocess
import requests
import math
import telebot
from functools import wraps
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, render_template_string, request, Response, redirect, url_for, session

# ==========================================
# CONFIGURACIÓN Y VARIABLES SEGURAS
# ==========================================
TOKEN = os.environ.get('TOKEN')
SHEET_URL = os.environ.get('SHEET_URL')
WEB_URL = os.environ.get('WEB_URL', 'http://localhost:8080')
ADMIN_PASS = os.environ.get('ADMIN_PASS', '1234')

if not TOKEN or not SHEET_URL:
    raise ValueError("⚠️ Faltan variables de entorno (TOKEN o SHEET_URL).")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'zenith_clave_secreta_segura')

# ==========================================
# PROTECCIÓN DEL PANEL ADMINISTRADOR
# ==========================================
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ==========================================
# INTERFAZ WEB (TU DISEÑO ORIGINAL INTACTO)
# ==========================================
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso Restringido | Vault</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { background: #f8fafc; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #0f172a; }
        .login-card { background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; width: 100%; max-width: 380px; text-align: center; }
        .logo-icon { width: 48px; height: 48px; background: #eff6ff; color: #2563eb; border-radius: 12px; display: flex; justify-content: center; align-items: center; margin: 0 auto 1.5rem auto; border: 1px solid #bfdbfe; }
        h2 { margin-bottom: 0.5rem; font-weight: 600; font-size: 1.25rem; }
        p { color: #64748b; font-size: 0.9rem; margin-bottom: 2rem; }
        input[type="password"] { width: 100%; padding: 0.8rem; margin-bottom: 1rem; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font-size: 1rem; outline: none; transition: border-color 0.2s; }
        input[type="password"]:focus { border-color: #2563eb; }
        button { width: 100%; padding: 0.8rem; background: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 500; font-size: 1rem; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #1d4ed8; }
        .error { color: #dc2626; font-size: 0.85rem; margin-top: 1rem; background: #fef2f2; padding: 0.5rem; border-radius: 6px; border: 1px solid #fca5a5; display: {% if error %}block{% else %}none{% endif %}; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
        </div>
        <h2>Modo Administrador</h2>
        <p>Ingresa la credencial maestra de la bóveda.</p>
        <form method="POST">
            <input type="password" name="password" placeholder="Contraseña..." required autofocus>
            <button type="submit">Acceder</button>
        </form>
        <div class="error">Contraseña incorrecta. Inténtalo de nuevo.</div>
    </div>
</body>
</html>
"""

HTML_ADMIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin | Vault</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: #f8fafc; padding: 2rem; color: #0f172a; margin: 0; }
        .nav-admin { max-width: 900px; margin: 0 auto 1rem auto; display: flex; justify-content: flex-end; }
        .btn-logout { background: #f1f5f9; color: #0f172a; border: 1px solid #e2e8f0; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 0.85rem; font-weight: 500; }
        .btn-logout:hover { background: #e2e8f0; }
        
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        h1 { margin-bottom: 1.5rem; font-size: 1.5rem; color: #0f172a; }
        
        /* ESTILOS NUEVOS PARA LA TARJETA DE CONFIGURACIÓN */
        .config-card { background: #eff6ff; border: 1px solid #bfdbfe; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center; }
        .config-title { font-weight: 600; color: #1e3a8a; margin-bottom: 0.25rem; font-size: 1rem; }
        .config-desc { color: #3b82f6; font-size: 0.85rem; margin: 0; }
        
        h2 { font-size: 1.2rem; color: #0f172a; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }
        th { font-weight: 600; color: #64748b; font-size: 0.9rem; }
        img { border-radius: 6px; width: 120px; aspect-ratio: 16/9; object-fit: cover; border: 1px solid #e2e8f0; }
        .form-row { display: flex; gap: 8px; align-items: center; }
        input[type="number"] { width: 60px; padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; text-align: center; font-family: inherit; }
        input[type="number"]:focus { outline: none; border-color: #2563eb; }
        button { background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; font-family: inherit; transition: background 0.2s; }
        button:hover { background: #1d4ed8; }
        .msg { background: #f0fdf4; color: #166534; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border: 1px solid #bbf7d0; display: {% if success %}block{% else %}none{% endif %}; }
    </style>
</head>
<body>
    <div class="nav-admin">
        <a href="/" class="btn-logout" style="margin-right: auto; background: #eff6ff; color: #2563eb; border-color: #bfdbfe;">Volver al Catálogo</a>
        <a href="/logout" class="btn-logout">Cerrar Sesión</a>
    </div>
    <div class="container">
        <h1>Panel de Control</h1>
        <div class="msg">✅ Acción realizada correctamente. Recarga la galería para ver los cambios.</div>
        
        <div class="config-card">
            <div>
                <div class="config-title">Paginación del Catálogo</div>
                <p class="config-desc">Define cuántos videos se mostrarán por cada página web.</p>
            </div>
            <form action="/admin/config" method="POST" class="form-row">
                <input type="number" name="per_page" value="{{ per_page }}" min="1" max="100" style="width: 80px;">
                <button type="submit">Guardar</button>
            </form>
        </div>

        <h2>Gestor de Portadas</h2>
        <table>
            <tr>
                <th>Miniatura Actual</th>
                <th>Título del Archivo</th>
                <th>Re-Capturar (Min : Seg)</th>
            </tr>
            {% for video in videos %}
            <tr>
                <td><img src="{{ video.Portada_Base64 }}"></td>
                <td style="max-width: 250px; word-wrap: break-word; font-size: 0.95rem; font-weight: 500;">{{ video.Titulo }}</td>
                <td>
                    <form action="/admin/update" method="POST" class="form-row">
                        <input type="hidden" name="id" value="{{ video.ID_Video }}">
                        <input type="hidden" name="url" value="{{ video.Enlace_Mediafire }}">
                        <input type="number" name="min" value="0" min="0" title="Minutos"> : 
                        <input type="number" name="seg" value="0" min="0" max="59" title="Segundos">
                        <button type="submit">Capturar</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

HTML_GALLERY = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catálogo | Vault</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --muted: #64748b; --border: #e2e8f0; --primary: #2563eb; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: var(--bg); color: var(--text); padding-bottom: 3rem; -webkit-font-smoothing: antialiased; }
        
        header { background: var(--card); border-bottom: 1px solid var(--border); padding: 1.2rem 2rem; position: sticky; top: 0; z-index: 50; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.2rem; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 8px; }
        .badge { background: #eff6ff; color: var(--primary); padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; border: 1px solid #bfdbfe; }
        
        .container { max-width: 1200px; margin: 2.5rem auto; padding: 0 1.5rem; }
        .section-title { font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem; color: var(--text); }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: all 0.3s ease; text-decoration: none; color: inherit; display: flex; flex-direction: column; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
        .card:hover { transform: translateY(-4px); box-shadow: 0 12px 20px -8px rgba(0,0,0,0.15); border-color: #cbd5e1; }
        
        .thumbnail { width: 100%; aspect-ratio: 16/9; background-color: #f1f5f9; background-size: cover; background-position: center; border-bottom: 1px solid var(--border); position: relative; }
        .play-overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.1); display: flex; justify-content: center; align-items: center; opacity: 0; transition: opacity 0.2s; }
        .card:hover .play-overlay { opacity: 1; }
        .play-icon { width: 48px; height: 48px; background: rgba(255,255,255,0.9); border-radius: 50%; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        
        .info { padding: 1.2rem; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .title { font-size: 1rem; font-weight: 600; line-height: 1.4; margin-bottom: 0.5rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .date { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; gap: 4px; }
        
        .empty-state { grid-column: 1 / -1; text-align: center; padding: 4rem 2rem; background: var(--card); border: 1px dashed #cbd5e1; border-radius: 12px; color: var(--muted); }
        
        .pagination { display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 3rem; }
        .btn-page { padding: 0.5rem 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 6px; text-decoration: none; color: var(--text); font-weight: 500; transition: all 0.2s; font-size: 0.9rem; }
        .btn-page:hover { background: #f1f5f9; }
        .page-info { font-size: 0.9rem; color: var(--muted); }
    </style>
</head>
<body>
    <header>
        <div class="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="2" y1="7" x2="7" y2="7"></line><line x1="2" y1="17" x2="7" y2="17"></line><line x1="17" y1="17" x2="22" y2="17"></line><line x1="17" y1="7" x2="22" y2="7"></line></svg>
            Lumina Vault
        </div>
        <div class="badge">Conexión Segura</div>
    </header>
    <div class="container">
        <h1 class="section-title">Tu Bóveda Multimedia</h1>
        <div class="grid">
            {% if videos|length == 0 %}
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5" style="margin-bottom: 1rem;"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line></svg>
                    <h3>No hay videos registrados</h3>
                    <p style="margin-top: 0.5rem; font-size: 0.9rem;">Los enlaces que envíes desde Telegram aparecerán aquí.</p>
                </div>
            {% else %}
                {% for video in videos %}
                <a href="/ver/{{ video.ID_Video }}" class="card">
                    <div class="thumbnail" style="background-image: url('{{ video.Portada_Base64 }}');">
                        <div class="play-overlay">
                            <div class="play-icon">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="var(--primary)" stroke="var(--primary)" stroke-width="2" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                            </div>
                        </div>
                    </div>
                    <div class="info">
                        <div class="title">{{ video.Titulo }}</div>
                        <div class="date">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                            {{ video.Fecha }}
                        </div>
                    </div>
                </a>
                {% endfor %}
            {% endif %}
        </div>
        
        {% if total_pages > 1 %}
        <div class="pagination">
            {% if current_page > 1 %}
                <a href="?page={{ current_page - 1 }}" class="btn-page">Anterior</a>
            {% endif %}
            
            <span class="page-info">Página {{ current_page }} de {{ total_pages }}</span>
            
            {% if current_page < total_pages %}
                <a href="?page={{ current_page + 1 }}" class="btn-page">Siguiente</a>
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

HTML_PLAYER = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reproduciendo: {{ video.Titulo }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --border: #e2e8f0; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: var(--bg); display: flex; flex-direction: column; min-height: 100vh; }
        
        .nav-bar { width: 100%; padding: 1.2rem 2rem; background: var(--card); border-bottom: 1px solid var(--border); box-shadow: 0 1px 2px rgba(0,0,0,0.02); display: flex; align-items: center; position: sticky; top: 0; z-index: 10; }
        .btn-volver { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; background: #f1f5f9; color: #334155; border-radius: 8px; text-decoration: none; font-weight: 500; font-size: 0.9rem; transition: all 0.2s; border: 1px solid var(--border); }
        .btn-volver:hover { background: #e2e8f0; color: #0f172a; }
        
        .main-content { flex-grow: 1; display: flex; flex-direction: column; align-items: center; padding: 2rem 1rem; width: 100%; max-width: 1000px; margin: 0 auto; }
        
        .video-header { width: 100%; margin-bottom: 1rem; }
        .video-title { font-size: 1.4rem; font-weight: 600; color: var(--text); line-height: 1.3; }
        .video-meta { font-size: 0.85rem; color: #64748b; margin-top: 0.4rem; }
        
        .video-container { width: 100%; background: #000; border-radius: 12px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04); border: 1px solid #334155; display: flex; justify-content: center; align-items: center; }
        
        video { width: 100%; max-height: 75vh; outline: none; display: block; object-fit: contain; }
        
        @media (max-width: 600px) {
            .nav-bar { padding: 1rem; }
            .main-content { padding: 1.5rem 0.5rem; }
            .video-container { border-radius: 8px; }
            .video-title { font-size: 1.2rem; }
        }
    </style>
</head>
<body>
    <div class="nav-bar">
        <a href="/" class="btn-volver">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
            Catálogo
        </a>
    </div>
    
    <div class="main-content">
        <div class="video-header">
            <h1 class="video-title">{{ video.Titulo }}</h1>
            <div class="video-meta">Agregado el {{ video.Fecha }} • Entorno Privado</div>
        </div>
        
        <div class="video-container">
            <video controls controlsList="nodownload" preload="metadata">
                <source src="{{ video.Enlace_Mediafire }}" type="video/mp4">
                Tu navegador no soporta la reproducción de video.
            </video>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# RUTAS DEL SERVIDOR WEB
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            error = True
    return render_template_string(HTML_LOGIN, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    try:
        resp = requests.get(SHEET_URL)
        data_json = resp.json()
        all_videos = data_json.get('data', [])
        
        all_videos.reverse()
        
        per_page = data_json.get('config', {}).get('per_page', 12)
        page = request.args.get('page', 1, type=int)
        
        total_videos = len(all_videos)
        total_pages = math.ceil(total_videos / per_page)
        
        if page < 1: page = 1
        if page > total_pages and total_pages > 0: page = total_pages
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        videos_page = all_videos[start_idx:end_idx]
        
        return render_template_string(HTML_GALLERY, videos=videos_page, current_page=page, total_pages=total_pages)
    except:
        return "<div style='padding:2rem; font-family:sans-serif;'>Error al conectar con la base de datos segura.</div>"

@app.route('/ver/<video_id>')
def watch(video_id):
    try:
        resp = requests.get(SHEET_URL)
        data = resp.json().get('data', [])
        video = next((v for v in data if str(v['ID_Video']) == str(video_id)), None)
        if video:
            return render_template_string(HTML_PLAYER, video=video)
        return "<div style='padding:2rem; font-family:sans-serif;'>Video no encontrado en la bóveda.</div>", 404
    except:
        return "<div style='padding:2rem; font-family:sans-serif;'>Error al cargar el reproductor.</div>"

@app.route('/admin')
@requires_auth
def admin_panel():
    success = request.args.get('success', False)
    try:
        resp = requests.get(SHEET_URL)
        data_json = resp.json()
        data = data_json.get('data', [])
        per_page = data_json.get('config', {}).get('per_page', 12)
        data.reverse() 
        return render_template_string(HTML_ADMIN, videos=data, success=success, per_page=per_page)
    except:
        return "Error cargando datos administrativos."

# NUEVA RUTA: Recibe el número de páginas y actualiza Sheets
@app.route('/admin/config', methods=['POST'])
@requires_auth
def admin_update_config():
    new_per_page = int(request.form.get('per_page', 12))
    try:
        payload = {"action": "update_config", "per_page": new_per_page}
        requests.post(SHEET_URL, json=payload)
    except Exception as e:
        print("Error actualizando configuración:", e)
    return redirect(url_for('admin_panel', success=True))

@app.route('/admin/update', methods=['POST'])
@requires_auth
def admin_update_cover():
    v_id = request.form.get('id')
    v_url = request.form.get('url')
    v_min = int(request.form.get('min', 0))
    v_seg = int(request.form.get('seg', 0))
    
    time_format = f"00:{v_min:02d}:{v_seg:02d}"
    
    try:
        cmd = [
            'ffmpeg', '-ss', time_format, '-i', v_url, '-vframes', '1', 
            '-q:v', '5', '-vf', 'scale=480:-1', 
            '-f', 'image2', '-c:v', 'mjpeg', 'pipe:1'
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        out, _ = process.communicate()
        b64_string = "data:image/jpeg;base64," + base64.b64encode(out).decode('utf-8') if out else ""
        
        if b64_string:
            payload = {"action": "update_cover", "id": v_id, "portada": b64_string}
            requests.post(SHEET_URL, json=payload)
            
    except Exception as e:
        print("Error re-capturando:", e)
        
    return redirect(url_for('admin_panel', success=True))

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# ==========================================
# LÓGICA DEL BOT DE TELEGRAM (TU CÓDIGO ORIGINAL INTACTO)
# ==========================================
def send_main_menu(chat_id, text="Panel de Control del Catálogo:"):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎬 Abrir Catálogo Web", url=WEB_URL),
        InlineKeyboardButton("🔍 Ver Historial Rápido", callback_data="history")
    )
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['start', 'menu'])
def start_command(message):
    send_main_menu(message.chat.id, "Bienvenido a la Bóveda Lumina.\nEnvía un enlace, varios enlaces juntos, o un archivo TXT de Mediafire Premium para añadirlos al catálogo.")

# ==========================================
# MOTOR DE CARGA MASIVA (TXT, Bloques y Unitario) + LOG DE ERRORES
# ==========================================
@bot.message_handler(content_types=['text', 'document'])
def process_mediafire_inputs(message):
    chat_id = message.chat.id
    texto_crudo = ""
    
    if message.content_type == 'document':
        if not message.document.file_name.endswith('.txt'):
            bot.reply_to(message, "⚠️ El archivo de la bóveda debe ser formato .txt")
            return
            
        msg_lectura = bot.reply_to(message, "⏳ *Extrayendo enlaces del documento...*", parse_mode="Markdown")
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            texto_crudo = downloaded_file.decode('utf-8')
            bot.delete_message(chat_id, msg_lectura.message_id)
        except Exception as e:
            bot.edit_message_text("❌ Error al leer el documento de la bóveda.", chat_id=chat_id, message_id=msg_lectura.message_id)
            return
    else:
        texto_crudo = message.text

    urls_encontradas = [palabra for palabra in texto_crudo.split() if 'mediafire.com' in palabra and palabra.startswith('http')]
    urls_unicas = list(dict.fromkeys(urls_encontradas))
    total_urls = len(urls_unicas)
    
    if total_urls == 0:
        if message.content_type == 'document':
            bot.reply_to(message, "⚠️ No detecté enlaces válidos de Mediafire en este archivo.")
        return 

    if total_urls == 1:
        msg_status = bot.reply_to(message, "⏳ *Procesando enlace...*\nLimpiando título y extrayendo miniatura...", parse_mode="Markdown")
    else:
        msg_status = bot.reply_to(message, f"⏳ *CARGA MASIVA INICIADA*\n━━━━━━━━━━━━━━━━━━\n📁 Enlaces detectados: `{total_urls}`\n⚙️ Actualizando progreso cada 10 subidas...", parse_mode="Markdown")
    
    exitos = 0
    fallos = 0
    enlaces_malos = []
    msg_errores_id = None
    clean_name = ""
    
    for i, url in enumerate(urls_unicas, 1):
        hubo_error = False
        
        try:
            raw_name = url.split('/')[-2] if len(url.split('/')) > 2 else f"Video_Sin_Nombre_{i}"
            decoded_name = urllib.parse.unquote(urllib.parse.unquote(raw_name))
            decoded_name = decoded_name.replace('.mp4', '').replace('.mkv', '').replace('.avi', '')
            clean_name = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', ' ', decoded_name)
            clean_name = re.sub(r'\s+', ' ', clean_name).strip()
            
            if not clean_name:
                clean_name = f"Video Guardado {i}"
            
            cmd = [
                'ffmpeg', '-ss', '35', '-i', url, '-vframes', '1', 
                '-q:v', '5', '-vf', 'scale=480:-1', 
                '-f', 'image2', '-c:v', 'mjpeg', 'pipe:1'
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out, _ = process.communicate()
            
            b64_string = "data:image/jpeg;base64," + base64.b64encode(out).decode('utf-8') if out else ""
                
            video_id = str(int(time.time()) + i) 
            payload = {
                "id": video_id,
                "titulo": clean_name,
                "enlace": url,
                "portada": b64_string,
                "fecha": time.strftime("%d/%m/%Y")
            }
            
            response = requests.post(SHEET_URL, json=payload)
            
            if response.status_code == 200:
                exitos += 1
            else:
                hubo_error = True
                
        except Exception:
            hubo_error = True
            
        if hubo_error:
            fallos += 1
            enlaces_malos.append(url)
            
            texto_errores = "⚠️ *ENLACES CON ERROR (Actualización en vivo):*\n━━━━━━━━━━━━━━━━━━\n"
            texto_errores += "\n".join([f"`{link}`" for link in enlaces_malos])
            
            if not msg_errores_id:
                try:
                    err_msg = bot.reply_to(message, texto_errores, parse_mode="Markdown")
                    msg_errores_id = err_msg.message_id
                except:
                    pass
            else:
                try:
                    bot.edit_message_text(texto_errores, chat_id=chat_id, message_id=msg_errores_id, parse_mode="Markdown")
                except:
                    pass
            
        if total_urls > 1 and i % 10 == 0:
            try:
                bot.edit_message_text(f"⏳ *PROCESANDO LOTE...*\n━━━━━━━━━━━━━━━━━━\n📊 Avance: `{i}/{total_urls}`\n✅ Exitosos: `{exitos}`\n❌ Errores: `{fallos}`", chat_id=chat_id, message_id=msg_status.message_id, parse_mode="Markdown")
            except:
                pass 

    if total_urls == 1:
        if exitos == 1:
            bot.edit_message_text(f"✅ *Video Guardado Exitosamente*\n\n📄 *Título:* `{clean_name}`", chat_id=chat_id, message_id=msg_status.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ Error al guardar en la base de datos. Verifica el enlace de error arriba.", chat_id=chat_id, message_id=msg_status.message_id)
    else:
        bot.edit_message_text(f"✅ *CARGA MASIVA FINALIZADA*\n━━━━━━━━━━━━━━━━━━\n📁 Total escaneados: `{total_urls}`\n✅ Subidos a la Bóveda: `{exitos}`\n❌ Errores detectados: `{fallos}`", chat_id=chat_id, message_id=msg_status.message_id, parse_mode="Markdown")
    
    send_main_menu(chat_id, "¿Qué deseas hacer ahora?")

@bot.callback_query_handler(func=lambda call: call.data == "history")
def show_history(call):
    chat_id = call.message.chat.id
    bot.edit_message_text("⏳ Consultando la Bóveda...", chat_id=chat_id, message_id=call.message.message_id)
    
    try:
        resp = requests.get(SHEET_URL)
        data = resp.json().get('data', [])
        
        if not data:
            bot.edit_message_text("📭 La bóveda está vacía.", chat_id=chat_id, message_id=call.message.message_id)
            send_main_menu(chat_id)
            return
            
        markup = InlineKeyboardMarkup(row_width=1)
        for video in reversed(data[-5:]):
            url_reproductor = f"{WEB_URL}/ver/{video['ID_Video']}"
            markup.add(InlineKeyboardButton(f"▶️ {video['Titulo']}", url=url_reproductor))
            
        markup.add(InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu"))
        bot.edit_message_text("📋 *Últimos 5 videos guardados:*", chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        
    except Exception as e:
        bot.edit_message_text("❌ Error al leer el catálogo.", chat_id=chat_id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "menu")
def return_menu(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_main_menu(call.message.chat.id)

print("🚀 Lumina Streaming Vault Iniciado...")
bot.infinity_polling()
