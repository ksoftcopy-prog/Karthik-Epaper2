import os
import fitz  # PyMuPDF కోసం
from flask import Flask, render_template_string, request, redirect, url_for, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'telangana_secure_2026'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/epaper_data')
ADMIN_PASS = "123"

# అప్‌లోడ్ ఫోల్డర్ లేకపోతే క్రియేట్ చేస్తుంది
if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- PDF ని ఇమేజ్‌లుగా మార్చే ఫంక్షన్ ---
def save_pdf_pages(pdf_path, output_folder):
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        page = doc.load_page(i)
        # Matrix(2, 2) అంటే మంచి క్వాలిటీ వస్తుంది
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  
        pix.save(os.path.join(output_folder, f"p{i+1}.jpg"))
    doc.close()
    return len(doc)

# --- UI TEMPLATE (మీరు ఇచ్చిన HTML కోడ్ ఇక్కడ ఉంటుంది) ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Mana Telangana E-Paper</title>
    <style>
        :root { --gold: #ffc107; --red: #ce1212; --dark: #222; }
        body { margin: 0; font-family: sans-serif; background: #444; overflow: hidden; }
        header { background: white; padding: 10px 40px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; height: 60px; box-sizing: border-box; }
        .toolbar { background: #f8f9fa; padding: 10px 40px; display: flex; gap: 15px; border-bottom: 2px solid var(--gold); align-items: center; height: 50px; box-sizing: border-box; }
        .btn { background: var(--gold); border: none; padding: 8px 15px; font-weight: bold; cursor: pointer; border-radius: 4px; text-decoration: none; color: black; font-size: 13px; }
        .main-container { display: flex; height: calc(100vh - 110px); }
        .sidebar { width: 220px; background: white; border-right: 1px solid #ddd; overflow-y: auto; padding: 15px; }
        .viewer { flex: 1; overflow: auto; padding: 40px; text-align: center; position: relative; scroll-behavior: smooth; }
        .page-box { background: white; box-shadow: 0 0 20px rgba(0,0,0,0.5); display: inline-block; margin-bottom: 40px; transform-origin: top center; transition: 0.1s; position: relative; }
        .page-box img { width: 900px; display: block; cursor: crosshair; -webkit-user-drag: none; }
        #selector { position: absolute; border: 2px solid #ff0000; background: rgba(255, 0, 0, 0.2); display: none; pointer-events: none; z-index: 9999; }
        .modal { display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); width:70%; height:85%; background:white; z-index:2000; padding:20px; box-shadow: 0 0 100px #000; border-radius: 8px; }
        .overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:1999; }
        .thumb { width: 100%; border: 1px solid #ddd; margin-bottom: 10px; cursor: pointer; transition: 0.2s; }
    </style>
</head>
<body>
    <header>
        <div onclick="location.href='/'" style="cursor:pointer;"><h1 style="color:var(--red); margin:0; font-family: serif;">MANA TELANGANA</h1></div>
        <nav>
            <a href="/about" style="margin-left:20px; color:#333; text-decoration:none; font-weight:bold;">About Us</a>
            <a href="/contact" style="margin-left:20px; color:#333; text-decoration:none; font-weight:bold;">Contact Us</a>
        </nav>
    </header>

    <div class="toolbar">
        <label style="font-weight:bold;">📅 Archive:</label>
        <input type="date" id="archiveDate" value="{{date}}" onchange="changeDate(this.value)">
        <button class="btn" onclick="zoom(0.1)">Zoom In (+)</button>
        <button class="btn" onclick="zoom(-0.1)">Zoom Out (-)</button>
        <div style="margin-left:auto;">
            <button class="btn" id="cropBtn" onclick="toggleCrop()">✂ Clip News</button>
        </div>
    </div>

    <div class="main-container">
        <div class="sidebar">
            {% for i in range(pages) %}
            <div onclick="goto({{i+1}})" style="text-align:center; margin-bottom:15px;">
                <img src="/static/epaper_data/{{date}}/p{{i+1}}.jpg" class="thumb">
                <small style="font-weight:bold;">Page {{i+1}}</small>
            </div>
            {% endfor %}
        </div>
        <div class="viewer" id="v-area">
            <div id="selector"></div>
            {% for i in range(pages) %}
            <div id="p{{i+1}}" class="page-box">
                <img src="/static/epaper_data/{{date}}/p{{i+1}}.jpg" id="img{{i+1}}" 
                     onmousedown="sDown(event)" onmousemove="sMove(event)" onmouseup="sUp(event, {{i+1}})">
            </div><br>
            {% endfor %}
        </div>
    </div>

    <div class="overlay" onclick="closeM()"></div>
    <div id="modal" class="modal">
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #ddd; padding-bottom:10px;">
            <h3 style="margin:0; color:var(--red);">Clip Preview</h3>
            <button onclick="closeM()" class="btn">Close X</button>
        </div>
        <div id="canvasArea" style="height:70%; overflow:auto; text-align:center; padding:20px; background:#f0f0f0; margin-top:10px;"></div>
        <div style="text-align:center; margin-top:15px; display:flex; justify-content:center; gap:10px;">
            <button onclick="downloadC()" class="btn" style="background:#007bff; color:white;">💾 Download</button>
            <button onclick="window.open('https://api.whatsapp.com/send?text=Mana Telangana E-Paper {{date}}')" class="btn" style="background:#25D366; color:white;">📱 Share</button>
        </div>
    </div>

    <script>
        let isC=false, draw=false, sx, sy, curZoom=1.0, startX, startY;
        const sel = document.getElementById('selector');

        function changeDate(d) { window.location.href = '/?date=' + d; }
        function goto(n) { document.getElementById('p'+n).scrollIntoView({behavior:'smooth'}); }
        function zoom(v) { curZoom += v; curZoom = Math.max(0.5, Math.min(curZoom, 2.0)); document.querySelectorAll('.page-box').forEach(b => b.style.transform = `scale(${curZoom})`); }
        function toggleCrop() { isC=!isC; document.getElementById('cropBtn').style.background = isC?"black":"#ffc107"; document.getElementById('cropBtn').style.color = isC?"white":"black"; }
        
        function sDown(e) {
            if(!isC) return; draw=true;
            const rect = e.target.getBoundingClientRect();
            sx = (e.clientX - rect.left) / curZoom;
            sy = (e.clientY - rect.top) / curZoom;
            startX = e.pageX; startY = e.pageY;
            sel.style.display="block"; sel.style.width="0"; sel.style.height="0";
            sel.style.left = startX + "px"; sel.style.top = startY + "px";
        }
        function sMove(e) {
            if(!draw) return;
            sel.style.width = Math.abs(e.pageX - startX) + "px";
            sel.style.height = Math.abs(e.pageY - startY) + "px";
            sel.style.left = Math.min(e.pageX, startX) + "px";
            sel.style.top = Math.min(e.pageY, startY) + "px";
        }
        function sUp(e, i) {
            if(!draw) return; draw=false; sel.style.display="none";
            const rect = e.target.getBoundingClientRect();
            process(i, sx, sy, (e.clientX-rect.left)/curZoom, (e.clientY-rect.top)/curZoom);
        }
        function process(id, x1, y1, x2, y2) {
            const img = document.getElementById('img'+id);
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const s = img.naturalWidth / 900;
            const w = Math.abs(x2-x1); const h = Math.abs(y2-y1);
            if(w < 15) return;
            canvas.width = w*s; canvas.height = (h*s)+120;
            ctx.fillStyle="white"; ctx.fillRect(0,0,canvas.width,canvas.height);
            ctx.fillStyle="#ce1212"; ctx.font="bold 45px serif"; ctx.fillText("MANA TELANGANA", 30, 65);
            ctx.fillStyle="#666"; ctx.font="20px Arial"; ctx.fillText("Date: {{date}} | Page: "+id, 30, 100);
            ctx.drawImage(img, Math.min(x1,x2)*s, Math.min(y1,y2)*s, w*s, h*s, 0, 120, w*s, h*s);
            document.getElementById('canvasArea').innerHTML = `<img src="${canvas.toDataURL('image/jpeg', 0.9)}" id="fImg" style="max-width:100%;">`;
            document.getElementById('modal').style.display="block"; document.querySelector('.overlay').style.display="block";
        }
        function closeM() { document.getElementById('modal').style.display="none"; document.querySelector('.overlay').style.display="none"; }
        function downloadC() { let a=document.createElement('a'); a.download="Clip.jpg"; a.href=document.getElementById('fImg').src; a.click(); }
    </script>
</body>
</html>
'''

# --- ROUTES ---
@app.route('/')
def home():
    selected_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    path = os.path.join(UPLOAD_FOLDER, selected_date)
    pages = 0
    if os.path.exists(path):
        pages = len([f for f in os.listdir(path) if f.endswith('.jpg')])
    
    if pages > 0:
        return render_template_string(HTML_TEMPLATE, date=selected_date, pages=pages)
    return f"<body style='text-align:center;padding-top:100px;'><h1>No Paper Found for {selected_date}</h1><a href='/login'>Admin Login</a></body>"

@app.route('/login')
def login():
    return '<body style="text-align:center;padding-top:100px;"><h2>Admin Login</h2><form action="/auth" method="post">Password: <input type="password" name="p"><button>Login</button></form></body>'

@app.route('/auth', methods=['POST'])
def auth():
    if request.form.get('p') == ADMIN_PASS:
        session['admin'] = True
        return redirect('/dashboard')
    return "Wrong Password"

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'): return redirect('/login')
    return '<h2>Admin Panel</h2><form action="/upload" method="post" enctype="multipart/form-data">Date: <input type="date" name="d" required><br><br>File: <input type="file" name="f" required><br><br><button>Upload & Publish</button></form>'

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin'): return "Unauthorized"
    f = request.files.get('f')
    d = request.form.get('d') # యూజర్ సెలెక్ట్ చేసిన డేట్ తీసుకుంటుంది
    if f and d:
        p = os.path.join(UPLOAD_FOLDER, d)
        if not os.path.exists(p): os.makedirs(p, exist_ok=True)
        pdf_path = os.path.join(p, "temp.pdf")
        f.save(pdf_path)
        
        # ఇమేజ్‌లుగా మారుస్తుంది (fitz ఉపయోగిస్తోంది)
        save_pdf_pages(pdf_path, p)
        
        if os.path.exists(pdf_path): os.remove(pdf_path)
        return redirect(f'/?date={d}')
    return "Error"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    # Render కోసం port 10000 లేదా సర్వర్ ఇచ్చే పోర్ట్ వాడాలి
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)