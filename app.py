import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'moyorak_secret_key_1234' # 세션 보안키

# 1. 파이어베이스 인증 및 DB 연결 (REST 방식 강제)
firebase_key_json = os.environ.get('FIREBASE_KEY')

try:
    if not firebase_admin._apps:
        if firebase_key_json:
            # Vercel 환경: 환경변수에서 JSON 로드
            key_clean = firebase_key_json.strip()
            # 혹시 앞뒤에 따옴표가 붙어있으면 제거
            if key_clean.startswith('"') and key_clean.endswith('"'):
                key_clean = key_clean[1:-1]
            
            cred_dict = json.loads(key_clean.replace('\\n', '\n'))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            
            # Vercel 무한 로딩 방지를 위해 REST 클라이언트 사용
            db = google_firestore.Client(
                project=cred_dict['project_id'],
                credentials=cred._get_credential()
            )
        else:
            # 로컬 환경: 파일에서 로드
            cred = credentials.Certificate('firebase_key.json')
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            
    print("✅ Firebase Connected Successfully!")
except Exception as e:
    print(f"❌ Firebase Connection Error: {e}")
    db = None

# --- 라우팅 시작 ---

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # 대소문자 문제 해결: 아이디를 소문자로 통일
        username = request.form.get('username').strip().lower()
        password = request.form.get('password')

        if not username or not password:
            flash("아이디와 비밀번호를 입력해주세요.", "danger")
            return redirect(url_for('signup'))

        try:
            user_ref = db.collection('users').document(username)
            if user_ref.get().exists:
                flash("이미 존재하는 아이디입니다.", "danger")
            else:
                user_ref.set({
                    'username': username,
                    'password': password,
                    'role': 'user'
                })
                flash("회원가입 성공! 로그인해주세요.", "success")
                return redirect(url_for('login'))
        except Exception as e:
            flash(f"오류 발생: {e}", "danger")
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 로그인 시에도 소문자로 변환해서 찾기
        username = request.form.get('username').strip().lower()
        password = request.form.get('password')

        try:
            user_ref = db.collection('users').document(username)
            doc = user_ref.get()

            if doc.exists:
                user_data = doc.to_dict()
                if user_data.get('password') == password:
                    session['user'] = username
                    session['role'] = user_data.get('role', 'user')
                    return redirect(url_for('home'))
                else:
                    flash("비밀번호가 틀렸습니다.", "danger")
            else:
                flash("존재하지 않는 아이디입니다.", "danger")
        except Exception as e:
            flash(f"로그인 중 오류 발생: {e}", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    # 로컬 테스트용
    app.run(debug=True)