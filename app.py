import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_yesterday_stable'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

# 파이어베이스 설정 (환경변수 사용)
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

SESSION_COLORS = {
    'Guitar': '#e67e22', 'Base': '#f1c40f', 'Drum': '#3498db', 'Keyboard': '#9b59b6', 'Vocal': '#2ecc71'
}

def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json().get('fields', {}) if res.status_code == 200 else {}
    except: return {}

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'): return redirect(url_for('login'))

    # 파트장 정보 가져오기
    s_raw = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_raw.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_raw.get('instagram', {}).get('stringValue', '@moyorak')
    }

    # 기타/베이스 멀티 악기 설정
    instruments = []
    if session_name in ['Guitar', 'Base']:
        instruments = [{'name': f'{session_name} 1호'}, {'name': f'{session_name} 2호'}]
    else:
        instruments = [{'name': f'{session_name} 공용'}]

    # 주간 날짜 계산
    today = datetime.now()
    start_week = today - timedelta(days=today.weekday())
    week_days = [(start_week + timedelta(days=i)).strftime('%m/%d') for i in range(7)]

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           instruments=instruments,
                           week_days=week_days,
                           color=SESSION_COLORS.get(session_name, '#333'),
                           user=session.get('user'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username', '').strip().lower()
        p = request.form.get('password', '')
        
        # 관리자 비상 로그인
        if u == 'admin' and p == '1234':
            session['user'] = 'admin'
            return redirect(url_for('home'))

        u_data = get_fb(f"users/{u}")
        if u_data.get('password', {}).get('stringValue') == p:
            session['user'] = u
            return redirect(url_for('home'))
        flash("로그인 실패")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# 관리자 설정 저장 (파트장 정보 수정 등)
@app.route('/admin/setup', methods=['POST'])
def admin_setup():
    if session.get('user') != 'admin': return redirect('/')
    t_s = request.form.get('target_session')
    l_n = request.form.get('leader_name')
    l_i = request.form.get('instagram')
    
    url = f"{BASE_URL}/sessions/{t_s}?updateMask.fieldPaths=leader_name&updateMask.fieldPaths=instagram"
    payload = {"fields": {"leader_name": {"stringValue": l_n}, "instagram": {"stringValue": l_i}}}
    requests.patch(url, json=payload)
    flash("수정 완료!")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)