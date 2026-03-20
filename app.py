import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'moyorak_secret_key_1234' # 세션 보안키

# 1. 파이어베이스 인증 및 DB 연결 (가장 확실한 버전)
firebase_key_json = os.environ.get('FIREBASE_KEY')

if not firebase_admin._apps:
    if firebase_key_json:
        # 환경변수 문자열 정리
        raw_json = firebase_key_json.strip()
        if raw_json.startswith('"') and raw_json.endswith('"'):
            raw_json = raw_json[1:-1]
        
        # JSON 로드 시도
        cred_dict = json.loads(raw_json.replace('\\n', '\n'))
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        
        # Vercel용 REST 클라이언트 생성
        db = google_firestore.Client(
            project=cred_dict['project_id'],
            credentials=cred._get_credential()
        )
        print("✅ Firebase Connected!")
    else:
        # 로컬 테스트 환경
        cred = credentials.Certificate('firebase_key.json')
        firebase_admin.initialize_app(cred)
        db = firestore.client()
else:
    # 이미 앱이 실행 중인 경우 db 객체만 다시 확인
    try:
        db = firestore.client()
    except:
        # Vercel 환경에서 client()가 실패할 경우 위와 동일하게 생성
        pass

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