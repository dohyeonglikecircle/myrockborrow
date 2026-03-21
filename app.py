import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_final_full_v17'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

SESSION_COLORS = {
    'Guitar': '#e67e22', 'Base': '#f1c40f', 'Drum': '#3498db', 'Keyboard': '#9b59b6', 'Vocal': '#2ecc71'
}

# 🎸 화면 표시용 이름 매핑 (DB는 Base, 화면은 Bass)
SESSION_DISPLAY_NAMES = {
    'Vocal': '보컬', 'Guitar': '기타', 'Base': '베이스(Bass)', 'Drum': '드럼', 'Keyboard': '키보드'
}

SESSION_MAP = {'Vocal': 'V', 'Guitar': 'G', 'Base': 'B', 'Drum': 'D', 'Keyboard': 'K'}

def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json().get('fields', {}) if res.status_code == 200 else {}
    except: return {}

def get_fb_collection(collection):
    try:
        res = requests.get(f"{BASE_URL}/{collection}", timeout=5)
        return res.json().get('documents', []) if res.status_code == 200 else []
    except: return []

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u_id = request.form.get('username').strip().lower()
        payload = {"fields": {
            "password": {"stringValue": request.form.get('password')},
            "name": {"stringValue": request.form.get('name')},
            "generation": {"stringValue": request.form.get('generation')},
            "session": {"stringValue": request.form.get('session')}
        }}
        requests.patch(f"{BASE_URL}/users/{u_id}", json=payload)
        flash("회원가입 완료!")
        return redirect(url_for('login'))
    gens = [str(int(g)) if g % 1 == 0 else str(g) for g in [x * 0.5 for x in range(38, 59)]]
    return render_template('signup.html', generations=gens)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username', '').strip().lower()
        p = request.form.get('password', '')
        if u == 'admin' and p == '1234':
            session['user'] = 'admin'
            return redirect(url_for('home'))
        u_d = get_fb(f"users/{u}")
        if u_d.get('password', {}).get('stringValue') == p:
            session['user'] = u
            session['user_name'] = u_d.get('name', {}).get('stringValue')
            session['user_gen'] = u_d.get('generation', {}).get('stringValue')
            session['user_session'] = u_d.get('session', {}).get('stringValue')
            return redirect(url_for('home'))
        flash("로그인 실패")
    return render_template('login.html')

@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'): return redirect(url_for('login'))
    s_raw = get_fb(f"sessions/{session_name}")
    leader = {'name': s_raw.get('leader_name', {}).get('stringValue', '미정'), 'instagram': s_raw.get('instagram', {}).get('stringValue', '@moyorak')}
    all_docs = get_fb_collection("instruments")
    instruments = []
    for doc in all_docs:
        f = doc.get('fields', {})
        if f.get('session', {}).get('stringValue') == session_name:
            instruments.append({'id': doc.get('name').split('/')[-1], 'name': f.get('model_name', {}).get('stringValue', '이름 없음'), 'img': f.get('image_url', {}).get('stringValue', '')})
    if not instruments and session_name != 'Vocal':
        instruments = [{'name': f'{session_name} 공용', 'img': '', 'id': 'default'}]
    res_docs = get_fb_collection("reservations")
    reservations = []
    for d in res_docs:
        f = d.get('fields', {})
        if f.get('session', {}).get('stringValue') == session_name:
            reservations.append({'user': f.get('user_display', {}).get('stringValue'), 'inst': f.get('inst_name', {}).get('stringValue'), 'date': f.get('date', {}).get('stringValue'), 'start': f.get('start_time', {}).get('stringValue'), 'end': f.get('end_time', {}).get('stringValue')})
    today = datetime.now()
    week_days = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    # Bass로 표시하기 위한 display_name
    display_name = 'Bass' if session_name == 'Base' else session_name
    
    return render_template('instrument.html', session_name=session_name, display_name=display_name, leader=leader, instruments=instruments, week_days=week_days, reservations=reservations, color=SESSION_COLORS.get(session_name, '#333'), user=session.get('user'), is_admin=(session.get('user') == 'admin'))

@app.route('/reserve', methods=['POST'])
def reserve():
    if not session.get('user'): return redirect(url_for('login'))
    gen = session.get('user_gen', ''); s_short = SESSION_MAP.get(session.get('user_session', ''), ''); name = session.get('user_name', '')
    u_display = f"{gen}{s_short} {name}"
    payload = {"fields": {"session": {"stringValue": request.form.get('session_name')}, "inst_name": {"stringValue": request.form.get('inst_name')}, "date": {"stringValue": request.form.get('date')}, "start_time": {"stringValue": request.form.get('start_time')}, "end_time": {"stringValue": request.form.get('end_time')}, "user_display": {"stringValue": u_display}}}
    requests.post(f"{BASE_URL}/reservations", json=payload)
    return redirect(request.referrer)

@app.route('/admin/setup', methods=['POST'])
def admin_setup():
    if session.get('user') != 'admin': return redirect('/')
    t_s = request.form.get('target_session')
    payload = {"fields": {"leader_name": {"stringValue": request.form.get('leader_name')}, "instagram": {"stringValue": request.form.get('instagram')}}}
    requests.patch(f"{BASE_URL}/sessions/{t_s}?updateMask.fieldPaths=leader_name&updateMask.fieldPaths=instagram", json=payload)
    return redirect(url_for('view_session', session_name=t_s))

@app.route('/admin/add_instrument', methods=['POST'])
def add_instrument():
    if session.get('user') != 'admin': return redirect('/')
    payload = {"fields": {"session": {"stringValue": request.form.get('session_name')}, "model_name": {"stringValue": request.form.get('instrument_model')}, "image_url": {"stringValue": request.form.get('instrument_img')}}}
    requests.post(f"{BASE_URL}/instruments", json=payload)
    return redirect(url_for('home'))

@app.route('/admin/delete_instrument/<doc_id>')
def delete_instrument(doc_id):
    if session.get('user') != 'admin': return redirect('/')
    requests.delete(f"{BASE_URL}/instruments/{doc_id}")
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)