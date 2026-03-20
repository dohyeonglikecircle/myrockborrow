import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)

# --- 세션 및 쿠키 보안 설정 (Vercel 최적화) ---
app.config['SECRET_KEY'] = 'moyorak_2026_super_secret'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2) # 2시간 유지
app.config['SESSION_COOKIE_NAME'] = 'moyorak_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # Vercel(HTTPS) 환경 필수
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 파이어베이스 설정
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/users"

def get_user_data(username):
    try:
        url = f"{FIRESTORE_URL}/{username}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            fields = response.json().get('fields', {})
            # 데이터 추출 시 안전하게 .get() 사용 (대소문자 무관하게 아이디 반환)
            return {
                'username': fields.get('username', {}).get('stringValue', username),
                'password': fields.get('password', {}).get('stringValue', ''),
                'role': fields.get('role', {}).get('stringValue', 'user')
            }
    except Exception as e:
        print(f"🚨 API Error: {e}")
    return None

@app.route('/')
def home():
    # index.html에서 {{ session.get('user') }}를 쓰니까 세션 확인
    current_user = session.get('user')
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        user_data = get_user_data(username)
        
        if user_data and user_data['password'] == password:
            # 세션 강제 활성화
            session.clear() # 기존 세션 청소
            session.permanent = True
            session['user'] = user_data['username']
            session['role'] = user_data['role']
            print(f"✅ Login Success: {session['user']}")
            return redirect(url_for('home'))
        else:
            flash("아이디 또는 비밀번호가 틀렸습니다.")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        
        if get_user_data(username):
            flash("이미 존재하는 아이디입니다.")
        else:
            url = f"{FIRESTORE_URL}?documentId={username}"
            payload = {
                "fields": {
                    "username": {"stringValue": username},
                    "password": {"stringValue": password},
                    "role": {"stringValue": "user"}
                }
            }
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                flash("가입 성공! 로그인해주세요.")
                return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# 404 방지
@app.route('/session/<name>')
def temp_session(name):
    return f"<h3>{name} 세션 페이지 준비 중</h3><a href='/'>홈으로</a>"

if __name__ == '__main__':
    app.run(debug=True)