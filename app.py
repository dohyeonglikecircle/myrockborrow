import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import timedelta

app = Flask(__name__)

# --- 세션 보안 및 유지 설정 (Vercel 필수) ---
app.config['SECRET_KEY'] = 'moyorak_ultra_secret_2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1) # 1일간 로그인 유지
app.config['SESSION_COOKIE_NAME'] = 'moyorak_session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 파이어베이스 프로젝트 ID (환경변수 확인!)
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/users"

def get_user_data(username):
    try:
        url = f"{FIRESTORE_URL}/{username}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            fields = response.json().get('fields', {})
            # 데이터 추출 시 안전하게 .get() 사용
            return {
                'username': fields.get('username', {}).get('stringValue'),
                'password': fields.get('password', {}).get('stringValue'),
                'role': fields.get('role', {}).get('stringValue', 'user')
            }
    except: return None
    return None

@app.route('/')
def home():
    # 세션에 유저가 있는지 확인
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        user_data = get_user_data(username)
        
        if user_data and user_data['password'] == password:
            # 세션에 정보 저장
            session.permanent = True # 세션 유지 설정 적용
            session['user'] = user_data['username']
            session['role'] = user_data['role']
            return redirect(url_for('home'))
        else:
            flash("로그인 정보가 일치하지 않습니다.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)