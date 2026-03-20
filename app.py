import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_final_system_2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Vercel 환경변수
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

# --- 데이터베이스 통신 함수 ---
def get_db_data(collection, document):
    try:
        url = f"{FIRESTORE_URL}/{collection}/{document}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get('fields', {})
    except: return None
    return None

# --- 메인 라우팅 ---
@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

# --- 🎤 세션 상세 페이지 (파트장 정보 & 예약) ---
@app.route('/session/<session_name>')
def view_session(session_name):
    # 1. 파트장 정보 가져오기 (sessions 컬렉션에서 해당 세션 문서 조회)
    leader_info = get_db_data('sessions', session_name)
    
    # 2. 악기 목록 가져오기 (instruments 컬렉션에서 해당 세션 악기 조회 - 실제로는 쿼리가 필요하지만 일단 단일 구조로 가정)
    # 보컬을 제외한 파트만 예약 버튼이 보이도록 HTML에서 처리할 거야.
    
    leader = {
        'name': leader_info.get('leader_name', {}).get('stringValue', '미정'),
        'contact': leader_info.get('contact', {}).get('stringValue', '정보 없음'),
        'notice': leader_info.get('notice', {}).get('stringValue', '공지사항이 없습니다.')
    }
    
    return render_template('session_view.html', 
                           session_name=session_name, 
                           leader=leader, 
                           user=session.get('user'))

# --- ⚙️ 관리자: 파트장 및 세션 설정 ---
@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    if session.get('user') != 'admin':
        flash("관리자 권한이 필요합니다.")
        return redirect(url_for('home'))

    if request.method == 'POST':
        s_name = request.form.get('session_name') # Vocal, Guitar 등
        l_name = request.form.get('leader_name')
        contact = request.form.get('contact')
        
        # Firestore에 파트장 정보 업데이트
        url = f"{FIRESTORE_URL}/sessions/{s_name}"
        payload = {
            "fields": {
                "leader_name": {"stringValue": l_name},
                "contact": {"stringValue": contact}
            }
        }
        requests.patch(url + "?updateMask.fieldPaths=leader_name&updateMask.fieldPaths=contact", json=payload)
        flash(f"{s_name} 세션 정보가 수정되었습니다.")
        return redirect(url_for('home'))

    return render_template('admin_setup.html')

# --- 📝 로그인/회원가입/로그아웃 (기존 동일) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        u_data = get_db_data('users', username)
        if u_data and u_data.get('password', {}).get('stringValue') == password:
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