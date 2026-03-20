import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
# 세션 유지를 위한 키 (절대 수정 금지)
app.config['SECRET_KEY'] = 'moyorak_1234_secret'

# --- 파이어베이스 연결 로직 (Vercel 최적화) ---
db = None

def initialize_firebase():
    global db
    try:
        if not firebase_admin._apps:
            firebase_key_json = os.environ.get('FIREBASE_KEY')
            
            if firebase_key_json:
                # 환경변수 클리닝 (따옴표, 줄바꿈 제거)
                key_data = firebase_key_json.strip()
                if key_data.startswith('"') and key_data.endswith('"'):
                    key_data = key_data[1:-1]
                
                # JSON 로드 및 인증서 생성
                cred_dict = json.loads(key_data.replace('\\n', '\n'))
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                
                # Vercel 무한 로딩 방지를 위해 REST 모드 Client 사용
                db = google_firestore.Client(
                    project=cred_dict['project_id'],
                    credentials=cred._get_credential()
                )
                print("✅ Firebase Connected via REST")
            else:
                # 로컬 환경 (파일이 있을 경우)
                cred = credentials.Certificate('firebase_key.json')
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                print("✅ Firebase Connected via Local File")
        else:
            # 이미 연결된 경우 db 객체만 가져오기
            db = firestore.client()
    except Exception as e:
        print(f"❌ Firebase Init Error: {e}")
        db = None

# 앱 시작 시 연결 실행
initialize_firebase()

# --- 라우팅 ---

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        if not username or not password:
            flash("아이디와 비밀번호를 모두 입력해주세요.")
            return redirect(url_for('signup'))

        try:
            if db is None: initialize_firebase() # DB 유실 대비 재연결
            user_ref = db.collection('users').document(username)
            if user_ref.get().exists:
                flash("이미 존재하는 아이디입니다.")
            else:
                user_ref.set({
                    'username': username,
                    'password': password,
                    'role': 'user'
                })
                flash("회원가입 성공! 로그인해주세요.")
                return redirect(url_for('login'))
        except Exception as e:
            flash(f"회원가입 오류: {e}")
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        try:
            if db is None: initialize_firebase()
            user_ref = db.collection('users').document(username)
            doc = user_ref.get()

            if doc.exists:
                user_data = doc.to_dict()
                if user_data.get('password') == password:
                    session['user'] = username
                    session['role'] = user_data.get('role', 'user')
                    return redirect(url_for('home'))
                else:
                    flash("비밀번호가 틀렸습니다.")
            else:
                flash("존재하지 않는 아이디입니다.")
        except Exception as e:
            flash(f"로그인 오류: {e}")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Vercel 배포 시 필요 (app 객체 노출)
if __name__ == '__main__':
    app.run(debug=True)