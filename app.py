import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_black_edition_2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json().get('fields', {}) if res.status_code == 200 else {}
    except: return {}

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

# --- 🎸 세션 상세 페이지 ---
@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'): return redirect(url_for('login'))

    s_data = get_fb(f"sessions/{session_name}")
    
    # 파트장 정보
    leader = {
        'name': s_data.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_data.get('instagram', {}).get('stringValue', '@moyorak'),
        'is_active': s_data.get('is_active', {}).get('booleanValue', True)
    }
    
    # 드럼, 키보드 비활성화 체크
    if session_name in ['Drum', 'Keyboard'] and not leader['is_active']:
        flash(f"현재 {session_name} 세션은 대여 기간이 아닙니다.")
        return redirect(url_for('home'))

    return render_template('instrument.html', session_name=session_name, leader=leader)

# --- ⚙️ 관리자 설정 페이지 (핵심!) ---
@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    if session.get('user') != 'admin': return redirect('/')

    if request.method == 'POST':
        target_s = request.form.get('target_session')
        new_name = request.form.get('leader_name')
        new_insta = request.form.get('instagram')
        # On/Off 스위치 값 처리 (체크박스)
        is_active = True if request.form.get('is_active') == 'on' else False

        url = f"{BASE_URL}/sessions/{target_s}"
        payload = {
            "fields": {
                "leader_name": {"stringValue": new_name},
                "instagram": {"stringValue": new_insta},
                "is_active": {"booleanValue": is_active}
            }
        }
        # PATCH로 부분 업데이트
        requests.patch(f"{url}?updateMask.fieldPaths=leader_name&updateMask.fieldPaths=instagram&updateMask.fieldPaths=is_active", json=payload)
        flash(f"{target_s} 정보가 업데이트되었습니다.")
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)