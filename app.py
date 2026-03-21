import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_2026_final_v4'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

# Vercel 환경변수
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def get_fb(path):
    """Firestore 데이터를 안전하게 가져오는 함수"""
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        if res.status_code == 200:
            return res.json().get('fields', {})
    except: return {}
    return {}

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

# --- 🎸 세션 상세 페이지 (파트장 정보 + 악기 예약) ---
@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'):
        flash("로그인이 필요합니다.")
        return redirect(url_for('login'))

    # 1. 오른쪽 사이드바용 파트장 정보
    s_data = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_data.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_data.get('instagram', {}).get('stringValue', '@moyorak')
    }
    
    # 2. 키보드/드럼 활성화 상태 체크
    is_active = s_data.get('is_active', {}).get('booleanValue', True)
    if session_name in ['Keyboard', 'Drum'] and not is_active:
        return "<h3>현재 공연 기간이 아니어서 비활성화된 세션입니다.</h3><a href='/'>홈으로</a>"

    # 3. 악기 목록 (Guitar, Base 전용 - 현재는 샘플 데이터)
    instruments = []
    if session_name in ['Guitar', 'Base']:
        instruments = [{'name': f'{session_name} 공용 1호', 'status': '대여가능', 'img': '/static/images/inst_sample.png'}]

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           instruments=instruments,
                           user=session.get('user'))

# --- 🔐 로그인 / 로그아웃 ---
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