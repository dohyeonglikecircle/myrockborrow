import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_dynamic_v11'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

SESSION_COLORS = {
    'Guitar': '#e67e22', 'Base': '#f1c40f', 'Drum': '#3498db', 'Keyboard': '#9b59b6', 'Vocal': '#2ecc71'
}

# 단일 문서 가져오기
def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json().get('fields', {}) if res.status_code == 200 else {}
    except: return {}

# 컬렉션 전체 목록 가져오기 (동적 악기 로딩용)
def get_fb_collection(collection):
    try:
        res = requests.get(f"{BASE_URL}/{collection}", timeout=5)
        if res.status_code == 200:
            return res.json().get('documents', [])
    except: return []
    return []

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'): return redirect(url_for('login'))

    # 1. 파트장 정보
    s_raw = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_raw.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_raw.get('instagram', {}).get('stringValue', '@moyorak')
    }

    # 2. 동적 악기 목록 가져오기 (관리자가 등록한 모든 악기)
    all_inst_docs = get_fb_collection("instruments")
    instruments = []
    
    for doc in all_inst_docs:
        f = doc.get('fields', {})
        # 해당 세션에 맞는 악기만 필터링
        if f.get('session', {}).get('stringValue') == session_name:
            instruments.append({
                'name': f.get('model_name', {}).get('stringValue', 'Unknown Model'),
                'img': f.get('image_url', {}).get('stringValue', '')
            })

    # 만약 등록된 악기가 하나도 없다면 기본값 표시
    if not instruments and session_name != 'Vocal':
        instruments = [{'name': f'{session_name} 공용', 'img': ''}]

    today = datetime.now()
    week_days = [(today + timedelta(days=i)).strftime('%m/%d') for i in range(7)]

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           instruments=instruments,
                           week_days=week_days,
                           color=SESSION_COLORS.get(session_name, '#333'),
                           user=session.get('user'),
                           is_admin=(session.get('user') == 'admin'))

@app.route('/admin/add_instrument', methods=['POST'])
def add_instrument():
    if session.get('user') != 'admin': return redirect('/')
    s_name = request.form.get('session_name')
    i_model = request.form.get('instrument_model')
    i_img = request.form.get('instrument_img')
    
    payload = {
        "fields": {
            "session": {"stringValue": s_name},
            "model_name": {"stringValue": i_model},
            "image_url": {"stringValue": i_img}
        }
    }
    # Firestore 'instruments' 컬렉션에 새 문서 생성
    requests.post(f"{BASE_URL}/instruments", json=payload)
    flash(f"{i_model} 등록 성공!")
    return redirect(url_for('home'))

@app.route('/admin/setup', methods=['POST'])
def admin_setup():
    if session.get('user') != 'admin': return redirect('/')
    t_s = request.form.get('target_session')
    l_n = request.form.get('leader_name')
    l_i = request.form.get('instagram')
    url = f"{BASE_URL}/sessions/{t_s}?updateMask.fieldPaths=leader_name&updateMask.fieldPaths=instagram"
    payload = {"fields": {"leader_name": {"stringValue": l_n}, "instagram": {"stringValue": l_i}}}
    requests.patch(url, json=payload)
    return redirect(url_for('view_session', session_name=t_s))

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
            return redirect(url_for('home'))
        flash("로그인 실패")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)