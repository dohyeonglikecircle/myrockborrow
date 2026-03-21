import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_final_v5_2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

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
    if not session.get('user'):
        return redirect(url_for('login'))

    # 1. 파트장 정보 (sessions 컬렉션)
    s_raw = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_raw.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_raw.get('instagram', {}).get('stringValue', '@moyorak'),
        'is_active': s_raw.get('is_active', {}).get('booleanValue', True)
    }

    # 2. 악기 목록 로직 (Guitar, Base는 여러 대)
    instruments = []
    if session_name in ['Guitar', 'Base']:
        # 임시 데이터 (나중에 DB 쿼리로 대체 가능)
        instruments = [
            {'name': f'{session_name} 1호', 'img': ''},
            {'name': f'{session_name} 2호', 'img': ''}
        ]
    elif session_name in ['Drum', 'Keyboard']:
        instruments = [{'name': f'{session_name} 공용', 'img': ''}]

    # 3. 주간 날짜 (상단 날짜 표시용)
    today = datetime.now()
    start_week = today - timedelta(days=today.weekday())
    week_days = [(start_week + timedelta(days=i)).strftime('%m/%d') for i in range(7)]

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           instruments=instruments,
                           week_days=week_days,
                           color=SESSION_COLORS.get(session_name, '#333'))

# --- 관리자 설정 (사이트 내 수정) ---
@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    if session.get('user') != 'admin': return redirect('/')
    if request.method == 'POST':
        t_s = request.form.get('target_session')
        l_n = request.form.get('leader_name')
        l_i = request.form.get('instagram')
        act = True if request.form.get('is_active') == 'on' else False
        
        url = f"{BASE_URL}/sessions/{t_s}?updateMask.fieldPaths=leader_name&updateMask.fieldPaths=instagram&updateMask.fieldPaths=is_active"
        payload = {"fields": {"leader_name": {"stringValue": l_n}, "instagram": {"stringValue": l_i}, "is_active": {"booleanValue": act}}}
        requests.patch(url, json=payload)
        flash("설정 저장 완료!")
        return redirect(url_for('admin_setup'))
    return render_template('admin_setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username', '').strip().lower()
        p = request.form.get('password', '')
        u_d = get_fb(f"users/{u}")
        if u_d.get('password', {}).get('stringValue') == p:
            session.permanent = True
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

# 기존 코드 하단에 추가
@app.route('/reserve', methods=['POST'])
def reserve():
    if not session.get('user'): return redirect(url_for('login'))
    
    # 예약 정보 받아오기
    inst_name = request.form.get('inst_name')
    date = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    user_info = session.get('user') # 예: 28K 조도형 (로그인 시 저장된 값)

    # 파이어베이스 reservations 컬렉션에 저장
    payload = {
        "fields": {
            "inst_name": {"stringValue": inst_name},
            "date": {"stringValue": date},
            "start_time": {"stringValue": start_time},
            "end_time": {"stringValue": end_time},
            "user": {"stringValue": user_info}
        }
    }
    requests.post(f"{BASE_URL}/reservations", json=payload)
    
    flash(f"{inst_name} 예약이 완료되었습니다!")
    return redirect(request.referrer)