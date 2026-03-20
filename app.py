import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
# 세션 유지를 위한 키 (브라우저 쿠키 보안)
app.config['SECRET_KEY'] = 'moyorak_final_secret_key_2026'

def get_db():
    """Vercel 환경변수 3개를 합쳐서 파이어베이스에 연결하는 함수"""
    if not firebase_admin._apps:
        project_id = os.environ.get('FB_PROJECT_ID')
        client_email = os.environ.get('FB_CLIENT_EMAIL')
        private_key = os.environ.get('FB_PRIVATE_KEY')

        # 환경변수가 없으면 로컬 파일 시도
        if not all([project_id, client_email, private_key]):
            try:
                cred = credentials.Certificate('firebase_key.json')
                firebase_admin.initialize_app(cred)
                return firestore.client()
            except:
                return None

        try:
            # 1. 프라이빗 키의 줄바꿈 문자(\n) 보정
            formatted_key = private_key.replace('\\n', '\n')
            
            # 2. 인증용 딕셔너리 수동 생성
            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": formatted_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            
            # 3. 인증서 등록
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            
            # 4. 🔥 [수정완료] 최신 라이브러리에 맞게 get_credential() 사용
            return google_firestore.Client(
                project=project_id,
                credentials=cred.get_credential() 
            )
        except Exception as e:
            # 이 에러가 Vercel 로그에 찍힘
            print(f"🚨 인증서 조립 실패: {str(e)}")
            return None
    else:
        # 이미 연결된 경우 기존 클라이언트 반환
        try:
            return firestore.client()
        except:
            return None

# --- 라우팅 (로그인/회원가입/로그아웃) ---

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        db = get_db()
        if not db:
            flash("DB 연결 실패! 환경변수를 확인하세요.")
            return redirect(url_for('signup'))
        
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        try:
            user_ref = db.collection('users').document(username)
            if user_ref.get().exists:
                flash("이미 존재하는 아이디입니다.")
            else:
                user_ref.set({
                    'username': username, 
                    'password': password, 
                    'role': 'user'
                })
                flash("회원가입 성공! 로그인해 주세요.")
                return redirect(url_for('login'))
        except Exception as e:
            flash(f"회원가입 오류: {str(e)}")
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        if not db:
            flash("DB 연결 실패! 환경변수를 확인하세요.")
            return redirect(url_for('login'))
        
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

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
                    flash("비밀번호가 틀렸습니다.")
            else:
                flash("존재하지 않는 아이디입니다.")
        except Exception as e:
            flash(f"로그인 오류: {str(e)}")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)