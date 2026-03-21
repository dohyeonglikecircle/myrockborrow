import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_reservation_fix_v15'

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

SESSION_COLORS = {
    'Guitar': '#e67e22', 'Base': '#f1c40f', 'Drum': '#3498db', 'Keyboard': '#9b59b6', 'Vocal': '#2ecc71'
}

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
        res = requests.get(f"{BASE_URL}/users/{u}")
        if res.status_code == 200 and res.json().get('fields', {}).get('password', {}).get('stringValue') == p:
            session['user'] = u
            session['user_name'] = res.json().get('fields', {}).get('name', {}).get('stringValue')
            session['user_gen'] = res.json().get('fields', {}).get('generation', {}).get('stringValue')
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'): return redirect(url_for('login'))
    
    # 파트장 및 악기 정보
    s_raw = requests.get(f"{BASE_URL}/sessions/{session_name}").json().get('fields', {})
    leader = {'name': s_raw.get('leader_name', {}).get('stringValue', '미정'), 'instagram': s_raw.get('instagram', {}).get('stringValue', '@moyorak')}
    
    inst_docs = get_fb_collection("instruments")
    instruments = []
    for d in inst_docs:
        f = d.get('fields', {})
        if f.get('session', {}).get('stringValue') == session_name:
            instruments.append({'id': d.get('name').split('/')[-1], 'name': f.get('model_name', {}).get('stringValue', '이름 없음'), 'img': f.get('image_url', {}).get('stringValue', '')})
    
    if not instruments: instruments = [{'name': f'{session_name} 공용', 'img': '', 'id': 'default'}]
    
    # 예약 데이터 불러오기
    res_docs = get_fb_collection("reservations")
    reservations = []
    for d in res_docs:
        f = d.get('fields', {})
        if f.get('session', {}).get('stringValue') == session_name:
            reservations.append({
                'user': f.get('user_display', {}).get('stringValue'),
                'inst': f.get('inst_name', {}).get('stringValue'),
                'date': f.get('date', {}).get('stringValue'),
                'start': f.get('start_time', {}).get('stringValue'),
                'end': f.get('end_time', {}).get('stringValue')
            })

    today = datetime.now()
    week_days = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    return render_template('instrument.html', session_name=session_name, leader=leader, 
                           instruments=instruments, week_days=week_days, 
                           reservations=reservations,
                           color=SESSION_COLORS.get(session_name, '#333'), 
                           user=session.get('user'), is_admin=(session.get('user') == 'admin'))

@app.route('/reserve', methods=['POST'])
def reserve():
    if not session.get('user'): return redirect(url_for('login'))
    u_display = f"{session.get('user_gen', '')}기 {session.get('user_name', session.get('user'))}"
    payload = {"fields": {
        "session": {"stringValue": request.form.get('session_name')},
        "inst_name": {"stringValue": request.form.get('inst_name')},
        "date": {"stringValue": request.form.get('date')},
        "start_time": {"stringValue": request.form.get('start_time')},
        "end_time": {"stringValue": request.form.get('end_time')},
        "user_display": {"stringValue": u_display}
    }}
    requests.post(f"{BASE_URL}/reservations", json=payload)
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)