import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_calendar_2026'

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

# 세션별 지정 색상 (이미지 느낌 살리기)
SESSION_COLORS = {
    'Guitar': '#e67e22',   # 주황
    'Base': '#f1c40f',     # 노랑
    'Drum': '#3498db',     # 파랑
    'Keyboard': '#9b59b6', # 보라
    'Vocal': '#2ecc71'      # 초록
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

    s_data = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_data.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_data.get('instagram', {}).get('stringValue', '@moyorak'),
        'is_active': s_data.get('is_active', {}).get('booleanValue', True)
    }

    # 캘린더용 날짜 계산 (이번 주 월~일)
    today = datetime.now()
    start_week = today - timedelta(days=today.weekday())
    week_days = [(start_week + timedelta(days=i)).strftime('%m/%d') for i in range(7)]

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           week_days=week_days,
                           color=SESSION_COLORS.get(session_name, '#333'))

# --- 🔐 사이트 내 관리자 수정 기능 ---
@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    if session.get('user') != 'admin': return redirect('/')

    if request.method == 'POST':
        target_s = request.form.get('target_session')
        new_name = request.form.get('leader_name')
        new_insta = request.form.get('instagram')
        is_active = True if request.form.get('is_active') == 'on' else False

        url = f"{BASE_URL}/sessions/{target_s}"
        payload = {
            "fields": {
                "leader_name": {"stringValue": new_name},
                "instagram": {"stringValue": new_insta},
                "is_active": {"booleanValue": is_active}
            }
        }
        # 사이트 내에서 입력한 값으로 파이어베이스 즉시 업데이트
        requests.patch(f"{url}?updateMask.fieldPaths=leader_name&updateMask.fieldPaths=instagram&updateMask.fieldPaths=is_active", json=payload)
        flash(f"{target_s} 파트 정보가 성공적으로 수정되었습니다.")
        return redirect(url_for('admin_setup'))

    return render_template('admin_setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        u_data = get_fb(f"users/{username}")
        if u_data.get('password', {}).get('stringValue') == password:
            session.permanent = True
            session['user'] = username
            return redirect(url_for('home'))
        flash("로그인 실패")
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)