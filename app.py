import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_2026_full_final'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

# Vercel 환경변수
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def get_fb_data(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json().get('fields', {}) if res.status_code == 200 else {}
    except: return {}

@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

# --- 🎤 핵심: 악기 정보, 파트장 정보, 예약이 다 뜨는 페이지 ---
@app.route('/session/<session_name>')
def view_session(session_name):
    user = session.get('user')
    
    # 1. 파이어베이스 'sessions' 컬렉션에서 데이터 가져오기
    raw_info = get_fb_data(f"sessions/{session_name}")
    
    leader = {
        'name': raw_info.get('leader_name', {}).get('stringValue', '미정'),
        'contact': raw_info.get('contact', {}).get('stringValue', '정보 없음'),
        'notice': raw_info.get('notice', {}).get('stringValue', '공지사항이 없습니다.')
    }

    # 2. 반드시 templates/instrument.html 파일이 있어야 합니다!
    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        u_data = get_fb_data(f"users/{username}")
        if u_data.get('password', {}).get('stringValue') == password:
            session.permanent = True
            session['user'] = username
            return redirect(url_for('home'))
        flash("로그인 정보가 틀립니다.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)