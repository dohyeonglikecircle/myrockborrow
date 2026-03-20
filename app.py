import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)

# --- 보안 및 세션 설정 ---
app.config['SECRET_KEY'] = 'moyorak_2026_full_system'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

# 파이어베이스 설정
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

# --- 공통 데이터 처리 함수 ---
def fetch_firestore(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json().get('fields', {}) if res.status_code == 200 else {}
    except: return {}

# --- [1] 메인 홈 ---
@app.route('/')
def home():
    return render_template('index.html', user=session.get('user'))

# --- [2] 세션별 상세 페이지 (핵심 기능) ---
@app.route('/session/<session_name>')
def view_session(session_name):
    user = session.get('user')
    
    # 파트장 정보 및 공지사항 가져오기
    raw_info = fetch_firestore(f"sessions/{session_name}")
    
    leader = {
        'name': raw_info.get('leader_name', {}).get('stringValue', '미정'),
        'contact': raw_info.get('contact', {}).get('stringValue', '정보 없음'),
        'notice': raw_info.get('notice', {}).get('stringValue', '현재 등록된 공지사항이 없습니다.')
    }
    
    # 보컬은 예약 기능을 막고, 나머지는 예약 버튼 활성화
    is_vocal = (session_name.lower() == 'vocal')
    
    return render_template('session_view.html', 
                           session_name=session_name, 
                           leader=leader, 
                           user=user,
                           is_vocal=is_vocal)

# --- [3] 관리자: 파트장 및 공지 수정 ---
@app.route('/admin/edit/<session_name>', methods=['GET', 'POST'])
def edit_session(session_name):
    if session.get('user') != 'admin':
        flash("관리자 권한이 필요합니다.")
        return redirect(url_for('home'))

    if request.method == 'POST':
        l_name = request.form.get('leader_name')
        contact = request.form.get('contact')
        notice = request.form.get('notice')

        url = f"{BASE_URL}/sessions/{session_name}"
        payload = {
            "fields": {
                "leader_name": {"stringValue": l_name},
                "contact": {"stringValue": contact},
                "notice": {"stringValue": notice}
            }
        }
        # 데이터를 업데이트 (PATCH 방식)
        requests.patch(f"{url}?updateMask.fieldPaths=leader_name&updateMask.fieldPaths=contact&updateMask.fieldPaths=notice", json=payload)
        flash(f"{session_name} 정보가 수정되었습니다!")
        return redirect(url_for('view_session', session_name=session_name))

    current = fetch_firestore(f"sessions/{session_name}")
    return render_template('admin_edit.html', session_name=session_name, current=current)

# --- [4] 계정 관련 (로그인/가입/로그아웃) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        u_data = fetch_firestore(f"users/{username}")
        
        if u_data.get('password', {}).get('stringValue') == password:
            session.permanent = True
            session['user'] = username
            session['role'] = u_data.get('role', {}).get('stringValue', 'user')
            return redirect(url_for('home'))
        flash("로그인 정보가 올바르지 않습니다.")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        if fetch_firestore(f"users/{username}"):
            flash("이미 존재하는 아이디입니다.")
        else:
            url = f"{BASE_URL}/users?documentId={username}"
            payload = {"fields": {"username": {"stringValue": username}, "password": {"stringValue": password}, "role": {"stringValue": "user"}}}
            requests.post(url, json=payload)
            flash("가입 성공!")
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)