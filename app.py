import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_final_2026_fixed'
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

# --- [로그인] ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username', '').strip().lower()
        p = request.form.get('password', '')
        
        # 관리자 계정 하드코딩 (DB 연결 전 비상용)
        if u == 'admin' and p == '1234': # 비밀번호는 본인 설정에 맞게 수정
            session.permanent = True
            session['user'] = 'admin'
            return redirect(url_for('home'))
            
        u_d = get_fb(f"users/{u}")
        fb_pw = u_d.get('password', {}).get('stringValue')
        
        if fb_pw and fb_pw == p:
            session.permanent = True
            session['user'] = u
            return redirect(url_for('home'))
        flash("아이디 또는 비밀번호가 틀립니다.")
    return render_template('login.html')

# --- [세션 상세 & 악기 선택] ---
@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'): return redirect(url_for('login'))
    
    s_raw = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_raw.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_raw.get('instagram', {}).get('stringValue', '@moyorak')
    }

    # 기타/베이스 멀티 악기 (예시 데이터, 나중에 DB 연동)
    instruments = []
    if session_name in ['Guitar', 'Base']:
        instruments = [{'name': f'{session_name} 모델 A'}, {'name': f'{session_name} 모델 B'}]
    else:
        instruments = [{'name': f'{session_name} 공용'}]

    today = datetime.now()
    week_days = [(today + timedelta(days=i)).strftime('%m/%d') for i in range(7)]
    
    # 세션별 색상
    colors = {'Guitar':'#e67e22', 'Base':'#f1c40f', 'Drum':'#3498db', 'Keyboard':'#9b59b6', 'Vocal':'#2ecc71'}
    
    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           instruments=instruments,
                           week_days=week_days,
                           color=colors.get(session_name, '#333'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)