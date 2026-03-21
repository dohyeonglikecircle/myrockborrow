import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_final_fixed_v8'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

SESSION_COLORS = {
    'Guitar': '#e67e22', 'Base': '#f1c40f', 'Drum': '#3498db', 'Keyboard': '#9b59b6', 'Vocal': '#2ecc71'
}

def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        if res.status_code == 200:
            return res.json().get('fields', {})
    except: return {}
    return {}

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'): return redirect(url_for('login'))

    # 파트장 정보 (데이터 없어도 미정으로 출력)
    s_raw = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_raw.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_raw.get('instagram', {}).get('stringValue', '@moyorak')
    }

    # 악기 목록 (기타/베이스 다중 대응)
    instruments = [{'name': f'{session_name} 1호'}]
    if session_name in ['Guitar', 'Base']:
        instruments.append({'name': f'{session_name} 2호'})

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

@app.route('/reserve', methods=['POST'])
def reserve():
    if not session.get('user'): return redirect(url_for('login'))
    flash("예약 신청이 완료되었습니다!")
    return redirect(request.referrer)

@app.route('/admin/add_instrument', methods=['POST'])
def add_instrument():
    if session.get('user') != 'admin': return redirect('/')
    flash("악기 등록이 완료되었습니다!")
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