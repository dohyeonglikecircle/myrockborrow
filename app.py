import os
import requests
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_rest_final_secret'

# --- 파이어베이스 설정 ---
PROJECT_ID = os.environ.get('FB_PROJECT_ID')
# REST API 주소 설정
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/users"

def get_user_data(username):
    """Firestore에서 유저 데이터를 직접 가져오는 함수 (REST)"""
    try:
        url = f"{FIRESTORE_URL}/{username}"
        response = requests.get(url, timeout=5) # 5초 안에 대답 없으면 끊기
        if response.status_code == 200:
            data = response.json()
            # Firestore REST API 특유의 필드 구조 파싱
            fields = data.get('fields', {})
            return {
                'username': fields.get('username', {}).get('stringValue'),
                'password': fields.get('password', {}).get('stringValue'),
                'role': fields.get('role', {}).get('stringValue', 'user')
            }
    except Exception as e:
        print(f"🚨 REST GET Error: {e}")
    return None

def save_user_data(username, password):
    """Firestore에 유저 데이터를 직접 저장하는 함수 (REST)"""
    try:
        url = f"{FIRESTORE_URL}?documentId={username}"
        payload = {
            "fields": {
                "username": {"stringValue": username},
                "password": {"stringValue": password},
                "role": {"stringValue": "user"}
            }
        }
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"🚨 REST POST Error: {e}")
    return False

# --- 라우팅 ---

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        user_data = get_user_data(username)
        if user_data and user_data['password'] == password:
            session['user'] = username
            session['role'] = user_data['role']
            return redirect(url_for('home'))
        else:
            flash("아이디 또는 비밀번호가 틀렸습니다.")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        # 이미 존재하는지 확인
        if get_user_data(username):
            flash("이미 존재하는 아이디입니다.")
        else:
            if save_user_data(username, password):
                flash("회원가입 성공! 로그인해주세요.")
                return redirect(url_for('login'))
            else:
                flash("회원가입 중 서버 오류가 발생했습니다.")
                
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)