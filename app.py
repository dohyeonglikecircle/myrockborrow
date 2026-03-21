import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_full_v3_2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json() if res.status_code == 200 else {}
    except: return {}

# --- 메인 홈 ---
@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

# --- 🎤 핵심: instrument.html과 연결되는 세션 상세 페이지 ---
@app.route('/session/<session_name>')
def view_session(session_name):
    user = session.get('user')
    
    # 1. 파트장 정보 (sessions 컬렉션)
    s_data = get_fb(f"sessions/{session_name}").get('fields', {})
    leader = {
        'name': s_data.get('leader_name', {}).get('stringValue', '미정'),
        'contact': s_data.get('contact', {}).get('stringValue', '정보없음'),
        'notice': s_data.get('notice', {}).get('stringValue', '공지사항이 없습니다.')
    }

    # 2. 악기 목록 (instruments 컬렉션 - 해당 세션 필터링은 나중에 쿼리로 보강)
    # 현재는 간단하게 모든 악기를 가져오거나 빈 리스트로 처리
    inst_list = [] # 여기에 DB에서 가져온 악기 객체들을 담을 예정

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           user=user,
                           instruments=inst_list)

# --- 📅 예약 처리 (POST) ---
@app.route('/reserve', methods=['POST'])
def reserve():
    if not session.get('user'):
        flash("로그인이 필요한 서비스입니다.")
        return redirect(url_for('login'))
    
    # 예약 로직 (파이어베이스에 예약 시간 저장)
    flash("예약 요청이 전송되었습니다.")
    return redirect(request.referrer)

# --- 로그인/로그아웃 (생략 없이 유지) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        u_data = get_fb(f"users/{username}").get('fields', {})
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