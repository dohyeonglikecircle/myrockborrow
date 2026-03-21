import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_2026_legacy_restore'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

# Vercel 환경변수 (FB_PROJECT_ID 하나만 정확하면 됩니다)
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def get_fb(path):
    """예전처럼 데이터를 슥슥 가져오기 위한 함수"""
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        if res.status_code == 200:
            return res.json().get('fields', {})
    except: return {}
    return {}

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

# --- 🎸 예전에 했던 그 instrument.html 로직 ---
@app.route('/session/<session_name>')
def view_session(session_name):
    user = session.get('user')
    
    # 1. 파트장 정보 가져오기 (sessions 컬렉션)
    s_data = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_data.get('leader_name', {}).get('stringValue', '미정'),
        'contact': s_data.get('contact', {}).get('stringValue', '정보없음'),
        'notice': s_data.get('notice', {}).get('stringValue', '공지사항이 없습니다.')
    }

    # 2. 악기 목록 가져오기 (instruments 컬렉션)
    # 예전에 쓰던 그 구조 그대로!
    inst_raw = get_fb(f"instruments/{session_name}") 
    instruments = []
    if inst_raw:
        instruments.append({
            'name': inst_raw.get('name', {}).get('stringValue', f'{session_name} 공용 1호'),
            'status': inst_raw.get('status', {}).get('stringValue', '대여가능')
        })

    # templates/instrument.html을 호출합니다. (이 이름 맞죠?)
    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           user=user,
                           instruments=instruments)

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