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
ADMIN_PASS = os.environ.get('ADMIN_PASS', '1234') # Contraseña del panel web

if not TOKEN or not SHEET_URL:
    print("⚠️ Faltan variables de entorno (TOKEN o SHEET_URL).")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
# Clave secreta necesaria para mantener la sesión de administrador iniciada
app.secret_key = os.environ.get('SECRET_KEY', 'zenith_clave_secreta_segura') 

# ==========================================
# PROTECCIÓN DEL PANEL ADMINISTRADOR (Sesiones)
# ==========================================
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ==========================================
# INTERFACES WEB (DISEÑO BLANCO Y PROFESIONAL)
# ==========================================

# 1. PANTALLA DE LOGIN
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso Restringido | Zenith Play</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { background: #f8fafc; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #0f172a; }
        .login-card { background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; width: 100%; max-width: 380px; text-align: center; }
        .logo-icon { width: 48px; height: 48px; background: #f1f5f9; border-radius: 12px; display: flex; justify-content: center; align-items: center; margin: 0 auto 1.5rem auto; border: 1px solid #e2e8f0; }
        h2 { margin-bottom: 0.5rem; font-weight: 600; font-size: 1.25rem; }
        p { color: #64748b; font-size: 0.9rem; margin-bottom: 2rem; }
        input[type="password"] { width: 100%; padding: 0.8rem; margin-bottom: 1rem; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font-size: 1rem; outline: none; transition: border-color 0.2s; }
        input[type="password"]:focus { border-color: #000; }
        button { width: 100%; padding: 0.8rem; background: #000; color: white; border: none; border-radius: 8px; font-weight: 500; font-size: 1rem; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #333; }
        .error { color: #dc2626; font-size: 0.85rem; margin-top: 1rem; background: #fef2f2; padding: 0.5rem; border-radius: 6px; border: 1px solid #fca5a5; display: {% if error %}block{% else %}none{% endif %}; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0f172a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
        </div>
        <h2>Panel de Administración</h2>
        <p>Ingresa tu clave de seguridad para continuar.</p>
        <form method="POST">
            <input type="password" name="password" placeholder="Contraseña..." required autofocus>
            <button type="submit">Acceder</button>
        </form>
        <div class="error">Contraseña incorrecta. Inténtalo de nuevo.</div>
    </div>
</body>
</html>
"""

# 2. GALERÍA PRINCIPAL (PAGINADA)
HTML_GALLERY = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zenith Play | Bóveda Personal</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --muted: #64748b; --border: #e2e8f0; --primary: #000000; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: var(--bg); color: var(--text); padding-bottom: 3rem; -webkit-font-smoothing: antialiased; }
        
        header { background: var(--card); border-bottom: 1px solid var(--border); padding: 1.2rem 2rem; position: sticky; top: 0; z-index: 50; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; }
        .logo { font-size: 1.2rem; font-weight: 700; display: flex; align-items: center; gap: 8px; }
        
        .container { max-width: 1200px; margin: 2.5rem auto; padding: 0 1.5rem; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; margin-bottom: 3rem; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: all 0.3s ease; text-decoration: none; color: inherit; display: flex; flex-direction: column; }
        .card:hover { transform: translateY(-4px); box-shadow: 0 12px 20px -8px rgba(0,0,0,0.15); }
        
        .thumbnail { width: 100%; aspect-ratio: 16/9; background-color: #f1f5f9; background-size: cover; background-position: center; border-bottom: 1px solid var(--border); }
        .info { padding: 1.2rem; }
        .title { font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        
        .pagination { display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 2rem; }
        .btn-page { padding: 0.5rem 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 6px; text-decoration: none; color: var(--text); font-weight: 500; transition: all 0.2s; }
        .btn-page:hover { background: #f1f5f9; }
        .page-info { font-size: 0.9rem; color: var(--muted); }
    </style>
</head>
<body>
    <header>
        <div class="logo">Zenith Play</div>
    </header>
    <div class="container">
        <div class="grid">
            {% for video in videos %}
            <a href="/ver/{{ video.ID_Video }}" class="card">
                <div class="thumbnail" style="background-image: url('{{ video.Portada_Base64 }}');"></div>
                <div class="info">
                    <div class="title">{{ video.Titulo }}</div>
                </div>
            </a>
            {% endfor %}
        </div>
        
        {% if total_pages > 1 %}
        <div class="pagination">
            {% if current_page > 1 %}<a href="?page={{ current_page - 1 }}" class="btn-page">Anterior</a>{% endif %}
            <span class="page-info">Página {{ current_page }} de {{ total_pages }}</span>
            {% if current_page < total_pages %}<a href="?page={{ current_page + 1 }}" class="btn-page">Siguiente</a>{% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# 3. PANEL DE ADMINISTRADOR
HTML_ADMIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin | Zenith Play</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: #f8fafc; padding: 2rem; color: #0f172a; margin: 0; }
        .nav-admin { max-width: 900px; margin: 0 auto 1rem auto; display: flex; justify-content: flex-end; }
        .btn-logout { background: #f1f5f9; color: #0f172a; border: 1px solid #e2e8f0; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 0.85rem; font-weight: 500; }
        .btn-logout:hover { background: #e2e8f0; }
        
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        h1 { margin-bottom: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 1rem; font-size: 1.5rem; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }
        th { font-weight: 600; color: #64748b; font-size: 0.9rem; }
        img { border-radius: 6px; width: 120px; aspect-ratio: 16/9; object-fit: cover; border: 1px solid #e2e8f0; }
        .form-row { display: flex; gap: 8px; align-items: center; }
        input[type="number"] { width: 60px; padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; text-align: center; font-family: inherit; }
        input[type="number"]:focus { outline: none; border-color: #000; }
        button { background: #000; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; font-family: inherit; transition: background 0.2s; }
        button:hover { background: #333; }
        .msg { background: #f0fdf4; color: #166534; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border: 1px solid #bbf7d0; display: {% if success %}block{% else %}none{% endif %}; }
    </style>
</head>
<body>
    <div class="nav-admin">
        <a href="/logout" class="btn-logout">Cerrar Sesión</a>
    </div>
    <div class="container">
        <h1>Gestor de Portadas</h1>
        <div class="msg">✅ Portada actualizada correctamente. Recarga la galería para ver los cambios.</div>
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

HTML_PLAYER = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{{ video.Titulo }}</title><style>body{background:#000;margin:0;display:flex;justify-content:center;align-items:center;height:100vh;}video{max-width:100%;max-height:100vh;outline:none;}</style></head><body><video controls controlsList="nodownload"><source src="{{ video.Enlace_Mediafire }}" type="video/mp4"></video></body></html>
"""

# ==========================================
# RUTAS DEL SERVIDOR WEB FLASK
# ==========================================

# Ruta de Inicio de Sesión
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

# Ruta para Cerrar Sesión
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
    except Exception as e:
        return "Error al conectar con la base de datos segura."

@app.route('/ver/<video_id>')
def watch(video_id):
    try:
        resp = requests.get(SHEET_URL)
        data = resp.json().get('data', [])
        video = next((v for v in data if str(v['ID_Video']) == str(video_id)), None)
        if video: return render_template_string(HTML_PLAYER, video=video)
        return "Video no encontrado.", 404
    except:
        return "Error al cargar el reproductor."

@app.route('/admin')
@requires_auth
def admin_panel():
    success = request.args.get('success', False)
    try:
        resp = requests.get(SHEET_URL)
        data = resp.json().get('data', [])
        data.reverse() 
        return render_template_string(HTML_ADMIN, videos=data, success=success)
    except:
        return "Error cargando datos administrativos."

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
# LÓGICA DEL BOT AETHER-BOX
# ==========================================
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, "⚡ Aether-Box Activo.\nEnvía enlaces de Mediafire para guardarlos en tu Bóveda.")

@bot.message_handler(content_types=['text'])
def process_links(message):
    urls_encontradas = [p for p in message.text.split() if 'mediafire.com' in p and p.startswith('http')]
    urls_unicas = list(dict.fromkeys(urls_encontradas))
    
    if not urls_unicas: return
    
    msg_status = bot.reply_to(message, "⏳ Recolectando e indexando...")
    
    for i, url in enumerate(urls_unicas, 1):
        try:
            raw_name = url.split('/')[-2] if len(url.split('/')) > 2 else f"Archivo_{int(time.time())}"
            clean_name = urllib.parse.unquote(urllib.parse.unquote(raw_name)).replace('.mp4', '').replace('.mkv', '')
            clean_name = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', ' ', clean_name).strip()
            
            cmd = ['ffmpeg', '-ss', '00:00:15', '-i', url, '-vframes', '1', '-q:v', '5', '-vf', 'scale=480:-1', '-f', 'image2', '-c:v', 'mjpeg', 'pipe:1']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out, _ = process.communicate()
            b64_string = "data:image/jpeg;base64," + base64.b64encode(out).decode('utf-8') if out else ""
            
            video_id = str(int(time.time()) + i) 
            payload = {
                "action": "insert",
                "id": video_id,
                "titulo": clean_name,
                "enlace": url,
                "portada": b64_string,
                "fecha": time.strftime("%d/%m/%Y")
            }
            requests.post(SHEET_URL, json=payload)
            
        except Exception as e:
            print("Error en enlace:", e)
            
    bot.edit_message_text("✅ Enlaces asegurados en Zenith Play.", chat_id=message.chat.id, message_id=msg_status.message_id)

print("🚀 Aether-Box & Zenith Play Iniciados...")
bot.infinity_polling()