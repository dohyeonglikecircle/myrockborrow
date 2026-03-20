import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_final_2026_key'

# 전역 변수로 DB 객체 관리
db = None

def get_db():
    global db
    if db is None:
        project_id = os.environ.get('FB_PROJECT_ID')
        client_email = os.environ.get('FB_CLIENT_EMAIL')
        private_key = os.environ.get('FB_PRIVATE_KEY')

        # 1. 환경변수가 없으면 로컬 파일로 시도
        if not all([project_id, client_email, private_key]):
            try:
                if not firebase_admin._apps:
                    cred = credentials.Certificate('firebase_key.json')
                    firebase_admin.initialize_app(cred)
                db = firestore.client()
                return db
            except: return None

        # 2. Vercel 환경: REST 모드로 초고속 연결
        try:
            if not firebase_admin._apps:
                formatted_key = private_key.replace('\\n', '\n')
                cred_dict = {
                    "type": "service_account",
                    "project_id": project_id,
                    "private_key": formatted_key,
                    "client_email": client_email,
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)

            # 🔥 중요: Vercel 무한 로딩을 방지하기 위해 'rest' 방식을 명시적으로 사용
            db = google_firestore.Client(
                project=project_id,
                credentials=credentials.Certificate(cred_dict).get_credential(),
                client_options={"api_endpoint": "firestore.googleapis.com"} # REST 엔드포인트 강제
            )
            return db
        except Exception as e:
            print(f"🚨 DB 연결 실패: {str(e)}")
            return None
    return db

# --- 라우팅 ---

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        current_db = get_db()
        if not current_db:
            flash("DB 연결에 실패했습니다.")
            return redirect(url_for('login'))
        
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        try:
            # 💥 .get() 호출 시 타임아웃 방지를 위해 가볍게 호출
            user_ref = current_db.collection('users').document(username)
            doc = user_ref.get()

            if doc.exists:
                user_data = doc.to_dict()
                if user_data.get('password') == password:
                    session['user'] = username
                    return redirect(url_for('home'))
                else: flash("비밀번호가 틀렸습니다.")
            else: flash("존재하지 않는 아이디입니다.")
        except Exception as e:
            flash(f"로그인 오류: {str(e)}")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        current_db = get_db()
        if not current_db:
            flash("DB 연결 실패")
            return redirect(url_for('signup'))
        
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        try:
            user_ref = current_db.collection('users').document(username)
            if not user_ref.get().exists:
                user_ref.set({'username': username, 'password': password, 'role': 'user'})
                flash("가입 성공!")
                return redirect(url_for('login'))
            else: flash("이미 존재하는 아이디입니다.")
        except Exception as e:
            flash(f"회원가입 오류: {str(e)}")
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)