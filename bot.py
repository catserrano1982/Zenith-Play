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
from flask import Flask, render_template_string, request, Response, redirect, url_for, session, jsonify

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

# Memoria RAM exclusiva para usuarios "En Vivo"
SYSTEM_STATS = {'en_vivo': {}}

# Ícono Global Favicon en formato SVG (Evita el mundo gris por defecto)
FAVICON_LINK = '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>">'

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
# INTERFAZ WEB (DISEÑO BLANCO Y PROFESIONAL)
# ==========================================
HTML_LOGIN = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso Restringido | Vault</title>
    {FAVICON_LINK}
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ background: #f8fafc; font-family: 'Inter', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #0f172a; }}
        .login-card {{ background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; width: 100%; max-width: 380px; text-align: center; }}
        .logo-icon {{ width: 48px; height: 48px; background: #eff6ff; color: #2563eb; border-radius: 12px; display: flex; justify-content: center; align-items: center; margin: 0 auto 1.5rem auto; border: 1px solid #bfdbfe; }}
        h2 {{ margin-bottom: 0.5rem; font-weight: 600; font-size: 1.25rem; }}
        p {{ color: #64748b; font-size: 0.9rem; margin-bottom: 2rem; }}
        input[type="password"] {{ width: 100%; padding: 0.8rem; margin-bottom: 1rem; border: 1px solid #cbd5e1; border-radius: 8px; box-sizing: border-box; font-size: 1rem; outline: none; transition: border-color 0.2s; }}
        input[type="password"]:focus {{ border-color: #2563eb; }}
        button {{ width: 100%; padding: 0.8rem; background: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 500; font-size: 1rem; cursor: pointer; transition: background 0.2s; }}
        button:hover {{ background: #1d4ed8; }}
        .error {{ color: #dc2626; font-size: 0.85rem; margin-top: 1rem; background: #fef2f2; padding: 0.5rem; border-radius: 6px; border: 1px solid #fca5a5; display: {{% if error %}}block{{% else %}}none{{% endif %}}; }}
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

HTML_ADMIN = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin | Vault</title>
    {FAVICON_LINK}
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background: #f8fafc; padding: 2rem; color: #0f172a; margin: 0; }}
        .nav-admin {{ max-width: 1000px; margin: 0 auto 1rem auto; display: flex; justify-content: flex-end; }}
        .btn-logout {{ background: #f1f5f9; color: #0f172a; border: 1px solid #e2e8f0; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 0.85rem; font-weight: 500; }}
        .btn-logout:hover {{ background: #e2e8f0; }}
        
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 2rem; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        h1 {{ margin-bottom: 1.5rem; font-size: 1.5rem; color: #0f172a; }}
        
        .tabs {{ display: flex; gap: 1rem; margin-bottom: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem; }}
        .tab-btn {{ background: none; border: none; font-size: 1rem; font-weight: 500; color: #64748b; cursor: pointer; padding: 0.5rem 1rem; border-radius: 6px; transition: all 0.2s; }}
        .tab-btn.active {{ color: #2563eb; background: #eff6ff; }}
        .tab-btn:hover:not(.active) {{ color: #0f172a; background: #f1f5f9; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        .config-card {{ background: #eff6ff; border: 1px solid #bfdbfe; padding: 1.5rem; border-radius: 8px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }}
        .config-title {{ font-weight: 600; color: #1e3a8a; margin-bottom: 0.25rem; font-size: 1rem; }}
        .config-desc {{ color: #3b82f6; font-size: 0.85rem; margin: 0; }}
        
        h2 {{ font-size: 1.2rem; color: #0f172a; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }}
        th {{ font-weight: 600; color: #64748b; font-size: 0.9rem; }}
        img {{ border-radius: 6px; width: 120px; aspect-ratio: 16/9; object-fit: cover; border: 1px solid #e2e8f0; }}
        .form-row {{ display: flex; gap: 8px; align-items: center; }}
        input[type="number"] {{ width: 60px; padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; text-align: center; font-family: inherit; }}
        button {{ background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; font-family: inherit; transition: background 0.2s; }}
        button:hover {{ background: #1d4ed8; }}
        
        .switch {{ position: relative; display: inline-block; width: 44px; height: 24px; }}
        .switch input {{ opacity: 0; width: 0; height: 0; }}
        .slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; transition: .4s; border-radius: 24px; }}
        .slider:before {{ position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }}
        input:checked + .slider {{ background-color: #2563eb; }}
        input:checked + .slider:before {{ transform: translateX(20px); }}
        .toggle-label {{ font-size: 0.85rem; color: #475569; display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}

        .report-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
        .report-header {{ display: flex; gap: 1rem; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.8rem; margin-bottom: 0.8rem; }}
        .report-video-info {{ flex-grow: 1; }}
        .report-badge {{ background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; display: inline-block; }}
        .report-item {{ background: #f8fafc; padding: 1rem; border-radius: 6px; margin-bottom: 0.5rem; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="nav-admin">
        <a href="/" class="btn-logout" style="margin-right: auto; background: #eff6ff; color: #2563eb; border-color: #bfdbfe;">Volver al Catálogo</a>
        <a href="/logout" class="btn-logout">Cerrar Sesión</a>
    </div>
    <div class="container">
        <h1>Panel de Control</h1>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="showTab('gestor')">Gestor de Bóveda</button>
            <button class="tab-btn" onclick="showTab('reportes')">Centro de Reportes</button>
        </div>

        <div id="gestor" class="tab-content active">
            <div class="config-card">
                <div>
                    <div class="config-title">Controles Globales de Visibilidad</div>
                    <p class="config-desc">Activa para mostrar los números en todas las entradas.</p>
                </div>
                <div style="display: flex; gap: 1.5rem;">
                    <label class="toggle-label">
                        <div class="switch"><input type="checkbox" onchange="toggleGlobal('global_vistas')" {{% if config.global_vistas %}}checked{{% endif %}}><span class="slider"></span></div>
                        Vistas Totales
                    </label>
                    <label class="toggle-label">
                        <div class="switch"><input type="checkbox" onchange="toggleGlobal('global_vivo')" {{% if config.global_vivo %}}checked{{% endif %}}><span class="slider"></span></div>
                        En Vivo
                    </label>
                </div>
            </div>

            <div class="config-card" style="background: white;">
                <div>
                    <div class="config-title" style="color: #0f172a;">Paginación del Catálogo</div>
                </div>
                <form action="/admin/config" method="POST" class="form-row">
                    <input type="number" name="per_page" value="{{ config.per_page }}" min="1" max="100" style="width: 80px;">
                    <button type="submit">Guardar</button>
                </form>
            </div>

            <h2>Gestor de Archivos y Analíticas</h2>
            <table>
                <tr>
                    <th>Miniatura</th>
                    <th>Título del Archivo</th>
                    <th>Analíticas (RAM + DB)</th>
                    <th>Visibilidad Pública</th>
                    <th>Acciones</th>
                </tr>
                {% for video in videos %}
                <tr>
                    <td><img src="{{ video.Portada_Base64 }}"></td>
                    <td style="max-width: 200px; word-wrap: break-word; font-size: 0.95rem; font-weight: 500;">{{ video.Titulo }}</td>
                    <td>
                        <div style="font-size: 0.9rem; color: #0f172a; margin-bottom: 4px;">👁️ {{ video.Vistas }} vistas</div>
                        <div style="font-size: 0.9rem; color: #2563eb;">🔴 {{ en_vivo.get(video.ID_Video|string, {})|length }} en vivo</div>
                    </td>
                    <td>
                        <label class="toggle-label">
                            <div class="switch"><input type="checkbox" onchange="toggleVideo('{{ video.ID_Video }}', 'vistas')" {{% if video.Mostrar_Vistas %}}checked{{% endif %}}><span class="slider"></span></div> Vistas
                        </label>
                        <label class="toggle-label">
                            <div class="switch"><input type="checkbox" onchange="toggleVideo('{{ video.ID_Video }}', 'vivo')" {{% if video.Mostrar_Vivo %}}checked{{% endif %}}><span class="slider"></span></div> En Vivo
                        </label>
                    </td>
                    <td>
                        <form action="/admin/update" method="POST" class="form-row">
                            <input type="hidden" name="id" value="{{ video.ID_Video }}">
                            <input type="hidden" name="url" value="{{ video.Enlace_Mediafire }}">
                            <input type="number" name="min" value="0" min="0" title="Minutos">
                            <button type="submit" style="padding: 8px;">Capturar</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div id="reportes" class="tab-content">
            <h2>Bandeja de Reportes Maliciosos y Enlaces Caídos</h2>
            {% set has_reports = false %}
            {% for v_id, reps in reportes.items() %}
                {% if reps|length > 0 %}
                    {% set has_reports = true %}
                    
                    {# Buscar el video correspondiente para extraer su miniatura y título #}
                    {% set current_video = None %}
                    {% for v in videos %}
                        {% if v.ID_Video|string == v_id|string %}
                            {% set current_video = v %}
                        {% endif %}
                    {% endfor %}

                    <div class="report-card">
                        <div class="report-header">
                            {% if current_video %}
                                <img src="{{ current_video.Portada_Base64 }}" style="width: 100px; height: 56px; object-fit: cover; border-radius: 4px;">
                                <div class="report-video-info">
                                    <h3 style="margin: 0; font-size: 1.1rem; color: #0f172a;">{{ current_video.Titulo }}</h3>
                                    <span style="font-size: 0.8rem; color: #64748b;">ID del Video: {{ v_id }}</span>
                                </div>
                            {% else %}
                                <div class="report-video-info">
                                    <h3 style="margin: 0; font-size: 1.1rem; color: #0f172a;">Archivo eliminado o ID Huérfano</h3>
                                    <span style="font-size: 0.8rem; color: #64748b;">ID: {{ v_id }}</span>
                                </div>
                            {% endif %}
                        </div>
                        {% for r in reps %}
                        <div class="report-item">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                                <span class="report-badge">{{ r.motivo }}</span>
                                <span style="font-size: 0.8rem; color: #64748b;">{{ r.fecha }}</span>
                            </div>
                            {% if r.nombre %}<div><strong>Nombre Reportante:</strong> {{ r.nombre }}</div>{% endif %}
                            {% if r.correo %}<div><strong>Correo:</strong> {{ r.correo }}</div>{% endif %}
                            <div style="margin-top: 8px; color: #334155;"><strong>Detalle enviado:</strong> {{ r.detalle }}</div>
                        </div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endfor %}
            {% if not has_reports %}
                <p style="color: #64748b; text-align: center; padding: 2rem;">No hay reportes registrados en el sistema.</p>
            {% endif %}
        </div>
    </div>

    <script>
        function showTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }}
        function toggleGlobal(setting) {{
            fetch('/api/admin/toggle', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{type: 'global', setting: setting}}) }}).then(() => setTimeout(()=>location.reload(), 500));
        }}
        function toggleVideo(v_id, setting) {{
            fetch('/api/admin/toggle', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{type: 'video', id: v_id, setting: setting}}) }}).then(() => setTimeout(()=>location.reload(), 500));
        }}
    </script>
</body>
</html>
"""

HTML_GALLERY = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catálogo | Vault</title>
    {FAVICON_LINK}
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --muted: #64748b; --border: #e2e8f0; --primary: #2563eb; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text); padding-bottom: 3rem; -webkit-font-smoothing: antialiased; }}
        header {{ background: var(--card); border-bottom: 1px solid var(--border); padding: 1.2rem 2rem; position: sticky; top: 0; z-index: 50; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 1.2rem; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 8px; }}
        .badge {{ background: #eff6ff; color: var(--primary); padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; border: 1px solid #bfdbfe; }}
        .container {{ max-width: 1200px; margin: 2.5rem auto; padding: 0 1.5rem; }}
        .section-title {{ font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem; color: var(--text); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: all 0.3s ease; text-decoration: none; color: inherit; display: flex; flex-direction: column; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
        .card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 20px -8px rgba(0,0,0,0.15); border-color: #cbd5e1; }}
        .thumbnail {{ width: 100%; aspect-ratio: 16/9; background-color: #f1f5f9; background-size: cover; background-position: center; border-bottom: 1px solid var(--border); position: relative; }}
        .play-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.1); display: flex; justify-content: center; align-items: center; opacity: 0; transition: opacity 0.2s; }}
        .card:hover .play-overlay {{ opacity: 1; }}
        .play-icon {{ width: 48px; height: 48px; background: rgba(255,255,255,0.9); border-radius: 50%; display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .info {{ padding: 1.2rem; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }}
        .title {{ font-size: 1rem; font-weight: 600; line-height: 1.4; margin-bottom: 0.5rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
        .date {{ font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }}
        .stat-badge {{ display: flex; align-items: center; gap: 4px; }}
        .live-pulse {{ width: 8px; height: 8px; background-color: #ef4444; border-radius: 50%; animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }} 70% {{ box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }} }}
        
        .pagination {{ display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 3rem; }}
        .btn-page {{ padding: 0.5rem 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 6px; text-decoration: none; color: var(--text); font-weight: 500; transition: all 0.2s; font-size: 0.9rem; }}
        .btn-page:hover {{ background: #f1f5f9; }}
        .page-info {{ font-size: 0.9rem; color: var(--muted); }}
    </style>
</head>
<body>
    <header>
        <div class="logo"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="2" y1="7" x2="7" y2="7"></line><line x1="2" y1="17" x2="7" y2="17"></line><line x1="17" y1="17" x2="22" y2="17"></line><line x1="17" y1="7" x2="22" y2="7"></line></svg> Lumina Vault</div>
        <div class="badge">Conexión Segura</div>
    </header>
    <div class="container">
        <h1 class="section-title">Tu Bóveda Multimedia</h1>
        <div class="grid">
            {{% for video in videos %}}
            {{% set v_id = video.ID_Video|string %}}
            {{% set show_vistas = config.global_vistas or video.Mostrar_Vistas %}}
            {{% set show_vivo = config.global_vivo or video.Mostrar_Vivo %}}
            <a href="/ver/{{ video.ID_Video }}" class="card">
                <div class="thumbnail" style="background-image: url('{{ video.Portada_Base64 }}');"><div class="play-overlay"><div class="play-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="var(--primary)" stroke="var(--primary)" stroke-width="2" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg></div></div></div>
                <div class="info">
                    <div class="title">{{ video.Titulo }}</div>
                    <div class="date">
                        <span class="stat-badge"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg> {{ video.Fecha }}</span>
                        {{% if show_vistas %}}<span class="stat-badge">👁️ {{ video.Vistas }} vistas</span>{{% endif %}}
                        {{% if show_vivo and en_vivo.get(v_id, {{}})|length > 0 %}}<span class="stat-badge" style="color: #ef4444;"><div class="live-pulse"></div> {{ en_vivo.get(v_id, {{}})|length }} en vivo</span>{{% endif %}}
                    </div>
                </div>
            </a>
            {{% endfor %}}
        </div>
        
        {{% if total_pages > 1 %}}
        <div class="pagination">
            {{% if current_page > 1 %}}
                <a href="?page={{ current_page - 1 }}" class="btn-page">Anterior</a>
            {{% endif %}}
            <span class="page-info">Página {{ current_page }} de {{ total_pages }}</span>
            {{% if current_page < total_pages %}}
                <a href="?page={{ current_page + 1 }}" class="btn-page">Siguiente</a>
            {{% endif %}}
        </div>
        {{% endif %}}
    </div>
</body>
</html>
"""

HTML_PLAYER = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reproduciendo: {{ video.Titulo }}</title>
    {FAVICON_LINK}
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --border: #e2e8f0; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
        body {{ background-color: var(--bg); display: flex; flex-direction: column; min-height: 100vh; }}
        .nav-bar {{ width: 100%; padding: 1.2rem 2rem; background: var(--card); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 10; }}
        .btn-volver {{ display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; background: #f1f5f9; color: #334155; border-radius: 8px; text-decoration: none; font-weight: 500; font-size: 0.9rem; border: 1px solid var(--border); }}
        .main-content {{ flex-grow: 1; display: flex; flex-direction: column; align-items: center; padding: 2rem 1rem; width: 100%; max-width: 1000px; margin: 0 auto; }}
        .video-header {{ width: 100%; margin-bottom: 1rem; }}
        .video-title {{ font-size: 1.4rem; font-weight: 600; color: var(--text); line-height: 1.3; }}
        .video-meta {{ font-size: 0.9rem; color: #64748b; margin-top: 0.6rem; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
        .video-container {{ width: 100%; background: #000; border-radius: 12px; overflow: hidden; display: flex; justify-content: center; align-items: center; }}
        video {{ width: 100%; max-height: 75vh; outline: none; display: block; object-fit: contain; }}
        
        .btn-report {{ background: none; border: none; color: #64748b; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 4px; padding: 4px 8px; border-radius: 4px; margin-left: auto; font-family: inherit;}}
        .btn-report:hover {{ background: #f1f5f9; color: #0f172a; }}
        
        /* Modal Styles */
        .modal-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.6); display: none; justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(2px); }}
        .modal-card {{ background: white; padding: 2rem; border-radius: 12px; width: 100%; max-width: 450px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
        .modal-card h3 {{ margin-top: 0; margin-bottom: 1rem; color: #0f172a; font-size: 1.2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.8rem; }}
        .form-group {{ margin-bottom: 1rem; }}
        .form-group label {{ display: block; font-size: 0.85rem; font-weight: 500; color: #475569; margin-bottom: 0.4rem; }}
        select, input, textarea {{ width: 100%; padding: 0.75rem; border: 1px solid #cbd5e1; border-radius: 6px; font-family: inherit; font-size: 0.9rem; outline: none; box-sizing: border-box; }}
        textarea {{ resize: vertical; min-height: 80px; }}
        .btn-submit {{ width: 100%; background: #2563eb; color: white; border: none; padding: 0.8rem; border-radius: 6px; font-weight: 500; cursor: pointer; margin-top: 0.5rem; }}
        .btn-cancel {{ width: 100%; background: transparent; color: #64748b; border: none; padding: 0.6rem; margin-top: 0.5rem; cursor: pointer; font-size: 0.85rem;}}
        
        .live-pulse {{ width: 8px; height: 8px; background-color: #ef4444; border-radius: 50%; animation: pulse 2s infinite; display: inline-block; }}
        @keyframes pulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }} 70% {{ box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }} 100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }} }}
    </style>
</head>
<body>
    <div class="nav-bar">
        <a href="/" class="btn-volver"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg> Catálogo</a>
    </div>
    
    <div class="main-content">
        <div class="video-header">
            <h1 class="video-title">{{ video.Titulo }}</h1>
            <div class="video-meta">
                <span>{{ video.Fecha }}</span>
                {{% set v_id = video.ID_Video|string %}}
                {{% if config.global_vistas or video.Mostrar_Vistas %}}
                    <span>• 👁️ <span id="viewCount">{{ video.Vistas }}</span> vistas</span>
                {{% endif %}}
                {{% if config.global_vivo or video.Mostrar_Vivo %}}
                    <span style="color: #ef4444;" id="liveContainer">• <div class="live-pulse"></div> <span id="liveCount">{{ en_vivo.get(v_id, {{}})|length }}</span> en vivo</span>
                {{% endif %}}
                
                <button class="btn-report" onclick="document.getElementById('modalOverlay').style.display='flex'">🚩 Reportar</button>
            </div>
        </div>
        <div class="video-container">
            <video controls controlsList="nodownload" preload="metadata"><source src="{{ video.Enlace_Mediafire }}" type="video/mp4"></video>
        </div>
    </div>

    <div class="modal-overlay" id="modalOverlay">
        <form class="modal-card" id="modalForm" onsubmit="event.preventDefault(); enviarReporte();">
            <h3>¿Qué problema presenta este video?</h3>
            <div class="form-group">
                <select id="repMotivo" onchange="checkReason()">
                    <option value="El video no carga / Enlace roto">El video no carga / Enlace roto</option>
                    <option value="Infracción de derechos de autor (DMCA)">Infracción de derechos de autor (DMCA)</option>
                    <option value="Desnudos o contenido sexual">Desnudos o contenido sexual</option>
                    <option value="Spam o contenido engañoso">Spam o contenido engañoso</option>
                    <option value="Infringe mis derechos de privacidad">Infringe mis derechos de privacidad</option>
                    <option value="Otro / Consulta general">Otro / Consulta general</option>
                </select>
            </div>
            <div id="honeypotFields" style="display: none;">
                <div class="form-group"><label>Nombre Legal / Titular</label><input type="text" id="repNombre" placeholder="Tu nombre completo"></div>
                <div class="form-group"><label>Correo electrónico de contacto</label><input type="email" id="repCorreo" placeholder="usuario@dominio.com"></div>
            </div>
            <div class="form-group">
                <label id="lblDetalle">Detalles (Opcional)</label>
                <textarea id="repDetalle" placeholder="Describe el problema..."></textarea>
            </div>
            <button class="btn-submit" type="submit">Enviar Reporte</button>
            <button class="btn-cancel" type="button" onclick="document.getElementById('modalOverlay').style.display='none'">Cancelar</button>
        </form>
        <div class="modal-card" id="modalSuccess" style="display: none; text-align: center;">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2" style="margin-bottom: 1rem;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            <h3 style="border: none; color: #16a34a;">Reporte Recibido</h3>
            <p style="font-size: 0.9rem; color: #475569; margin-bottom: 1.5rem;">El número de seguimiento es #<span id="tkNum"></span>. Nuestro equipo legal actuará en 24 a 48 horas si se comprueba la infracción.</p>
            <button class="btn-submit" type="button" onclick="document.getElementById('modalOverlay').style.display='none'">Cerrar</button>
        </div>
    </div>

    <script>
        const v_id = "{{ video.ID_Video }}";
        
        function checkReason() {{
            const val = document.getElementById('repMotivo').value;
            const isSerious = val !== 'El video no carga / Enlace roto';
            document.getElementById('honeypotFields').style.display = isSerious ? 'block' : 'none';
            document.getElementById('repCorreo').required = isSerious;
            document.getElementById('repNombre').required = isSerious;
            document.getElementById('lblDetalle').innerText = isSerious ? 'Detalles de la infracción' : 'Detalles (Opcional)';
        }}

        function enviarReporte() {{
            const val = document.getElementById('repMotivo').value;
            const isSerious = val !== 'El video no carga / Enlace roto';
            
            // Verificación extra en el lado de JavaScript por seguridad
            if (isSerious && !document.getElementById('repCorreo').value.includes('@')) {{
                alert('Por favor, introduce una dirección de correo electrónico válida.');
                return;
            }}

            const data = {{
                id: v_id,
                motivo: document.getElementById('repMotivo').value,
                nombre: document.getElementById('repNombre').value,
                correo: document.getElementById('repCorreo').value,
                detalle: document.getElementById('repDetalle').value
            }};
            fetch('/api/report', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data) }});
            document.getElementById('modalForm').style.display = 'none';
            document.getElementById('tkNum').innerText = Math.floor(Math.random() * 90000) + 10000;
            document.getElementById('modalSuccess').style.display = 'block';
        }}

        setInterval(() => {{
            fetch(`/api/ping/${{v_id}}`, {{method: 'POST'}})
                .then(r => r.json())
                .then(data => {{
                    const el = document.getElementById('liveCount');
                    if(el) el.innerText = data.en_vivo;
                }});
        }}, 10000);
    </script>
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
        config = data_json.get('config', {})
        
        all_videos.reverse()
        per_page = config.get('per_page', 12)
        page = request.args.get('page', 1, type=int)
        
        total_videos = len(all_videos)
        total_pages = math.ceil(total_videos / per_page)
        
        if page < 1: page = 1
        if page > total_pages and total_pages > 0: page = total_pages
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        videos_page = all_videos[start_idx:end_idx]
        
        return render_template_string(HTML_GALLERY, videos=videos_page, config=config, en_vivo=SYSTEM_STATS['en_vivo'], current_page=page, total_pages=total_pages)
    except:
        return "<div style='padding:2rem; font-family:sans-serif;'>Error al conectar con la base de datos segura.</div>"

@app.route('/ver/<video_id>')
def watch(video_id):
    try:
        if video_id not in SYSTEM_STATS['en_vivo']:
            SYSTEM_STATS['en_vivo'][video_id] = {}
        user_ip = request.remote_addr or "unknown"
        SYSTEM_STATS['en_vivo'][video_id][user_ip] = time.time()

        requests.post(SHEET_URL, json={"action": "add_view", "id": video_id})

        resp = requests.get(SHEET_URL)
        data_json = resp.json()
        videos = data_json.get('data', [])
        config = data_json.get('config', {})
        video = next((v for v in videos if str(v['ID_Video']) == str(video_id)), None)
        
        if video:
            return render_template_string(HTML_PLAYER, video=video, config=config, en_vivo=SYSTEM_STATS['en_vivo'])
        return "Video no encontrado.", 404
    except:
        return "Error al cargar reproductor."

@app.route('/admin')
@requires_auth
def admin_panel():
    try:
        resp = requests.get(SHEET_URL)
        data_json = resp.json()
        videos = data_json.get('data', [])
        config = data_json.get('config', {})
        reportes = data_json.get('reportes', {})
        videos.reverse() 
        return render_template_string(HTML_ADMIN, videos=videos, config=config, reportes=reportes, en_vivo=SYSTEM_STATS['en_vivo'])
    except:
        return "Error cargando datos."

# ==========================================
# RUTAS DE API
# ==========================================
@app.route('/api/ping/<video_id>', methods=['POST'])
def api_ping(video_id):
    if video_id not in SYSTEM_STATS['en_vivo']:
        SYSTEM_STATS['en_vivo'][video_id] = {}
    user_ip = request.remote_addr or "unknown"
    now = time.time()
    SYSTEM_STATS['en_vivo'][video_id][user_ip] = now
    SYSTEM_STATS['en_vivo'][video_id] = {ip: t for ip, t in SYSTEM_STATS['en_vivo'][video_id].items() if now - t < 15}
    return jsonify({"en_vivo": len(SYSTEM_STATS['en_vivo'][video_id])})

@app.route('/api/report', methods=['POST'])
def api_report():
    data = request.json
    payload = {
        "action": "save_report",
        "id": data.get('id'),
        "motivo": data.get('motivo'),
        "nombre": data.get('nombre'),
        "correo": data.get('correo'),
        "detalle": data.get('detalle'),
        "fecha": time.strftime("%d/%m/%Y %H:%M")
    }
    requests.post(SHEET_URL, json=payload)
    return jsonify({"status": "ok"})

@app.route('/api/admin/toggle', methods=['POST'])
@requires_auth
def api_toggle():
    data = request.json
    if data['type'] == 'global':
        requests.post(SHEET_URL, json={"action": "toggle_global", "setting": data['setting']})
    elif data['type'] == 'video':
        requests.post(SHEET_URL, json={"action": "toggle_video", "id": data['id'], "setting": data['setting']})
    return jsonify({"status": "ok"})

@app.route('/admin/config', methods=['POST'])
@requires_auth
def admin_update_config():
    new_per_page = int(request.form.get('per_page', 12))
    requests.post(SHEET_URL, json={"action": "update_config", "per_page": new_per_page})
    return redirect(url_for('admin_panel'))

@app.route('/admin/update', methods=['POST'])
@requires_auth
def admin_update_cover():
    v_id = request.form.get('id')
    v_url = request.form.get('url')
    v_min = int(request.form.get('min', 0))
    time_format = f"00:{v_min:02d}:00"
    try:
        cmd = ['ffmpeg', '-ss', time_format, '-i', v_url, '-vframes', '1', '-q:v', '5', '-vf', 'scale=480:-1', '-f', 'image2', '-c:v', 'mjpeg', 'pipe:1']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        out, _ = process.communicate()
        if out:
            b64 = "data:image/jpeg;base64," + base64.b64encode(out).decode('utf-8')
            requests.post(SHEET_URL, json={"action": "update_cover", "id": v_id, "portada": b64})
    except: pass
    return redirect(url_for('admin_panel'))

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# ==========================================
# LÓGICA DEL BOT DE TELEGRAM 
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

@bot.message_handler(content_types=['text', 'document'])
def process_mediafire_inputs(message):
    chat_id = message.chat.id
    texto_crudo = ""
    
    if message.content_type == 'document':
        if not message.document.file_name.endswith('.txt'):
            bot.reply_to(message, "⚠️ El archivo de la bóveda debe ser formato .txt")
            return
        msg_lectura = bot.reply_to(message, "⏳ *Extrayendo enlaces...*", parse_mode="Markdown")
        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            texto_crudo = downloaded_file.decode('utf-8')
            bot.delete_message(chat_id, msg_lectura.message_id)
        except Exception:
            return
    else:
        texto_crudo = message.text

    urls_encontradas = [p for p in texto_crudo.split() if 'mediafire.com' in p and p.startswith('http')]
    urls_unicas = list(dict.fromkeys(urls_encontradas))
    total_urls = len(urls_unicas)
    if total_urls == 0: return 

    msg_status = bot.reply_to(message, f"⏳ *Procesando {total_urls} enlace(s)...*", parse_mode="Markdown")
    exitos = 0
    
    for i, url in enumerate(urls_unicas, 1):
        try:
            raw_name = url.split('/')[-2] if len(url.split('/')) > 2 else f"Video_{i}"
            clean_name = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', ' ', urllib.parse.unquote(raw_name)).strip()
            cmd = ['ffmpeg', '-ss', '35', '-i', url, '-vframes', '1', '-q:v', '5', '-vf', 'scale=480:-1', '-f', 'image2', '-c:v', 'mjpeg', 'pipe:1']
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out, _ = process.communicate()
            b64_string = "data:image/jpeg;base64," + base64.b64encode(out).decode('utf-8') if out else ""
            requests.post(SHEET_URL, json={"id": str(int(time.time()) + i), "titulo": clean_name, "enlace": url, "portada": b64_string, "fecha": time.strftime("%d/%m/%Y")})
            exitos += 1
        except: pass
            
    bot.edit_message_text(f"✅ *CARGA FINALIZADA*\nSubidos: `{exitos}`", chat_id=chat_id, message_id=msg_status.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "history")
def show_history(call):
    chat_id = call.message.chat.id
    try:
        resp = requests.get(SHEET_URL)
        data = resp.json().get('data', [])
        if not data: return
        markup = InlineKeyboardMarkup(row_width=1)
        for video in reversed(data[-5:]):
            markup.add(InlineKeyboardButton(f"▶️ {video['Titulo']}", url=f"{WEB_URL}/ver/{video['ID_Video']}"))
        bot.edit_message_text("📋 *Últimos 5:*", chat_id=chat_id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except: pass

print("🚀 Lumina Streaming Vault Iniciado...")
bot.infinity_polling()
