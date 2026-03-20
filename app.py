import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_1234_secret'

def get_db():
    """매 요청마다 안전하게 DB 객체를 가져오는 함수"""
    try:
        if not firebase_admin._apps:
            firebase_key_json = os.environ.get('FIREBASE_KEY')
            
            if not firebase_key_json:
                # 로컬 환경 (파일로 인증)
                cred = credentials.Certificate('firebase_key.json')
                firebase_admin.initialize_app(cred)
                return firestore.client()
            
            # Vercel 환경: JSON 파싱 시도
            key_clean = firebase_key_json.strip()
            # 앞뒤에 불필요한 따옴표가 붙어있는 경우 제거
            if key_clean.startswith('"') and key_clean.endswith('"'):
                key_clean = key_clean[1:-1]
            
            cred_dict = json.loads(key_clean.replace('\\n', '\n'))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            
            # gRPC 무한로딩 방지를 위한 REST 방식 클라이언트 사용
            return google_firestore.Client(
                project=cred_dict['project_id'],
                credentials=cred._get_credential()
            )
        else:
            # 이미 앱이 초기화된 경우
            try:
                # 일반적인 클라이언트 반환 시도
                return firestore.client()
            except:
                # Vercel 특유의 연결 끊김 대비 재설정 로직 (필요 시)
                return firestore.client()
                
    except Exception as e:
        # 이 메시지가 Vercel Logs에 찍힙니다.
        print(f"🔥 DB Connection Failed: {str(e)}")
        return None

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

        db = get_db()
        if db is None:
            # 이제 화면에 '왜' 안되는지 에러가 뜰 거예요.
            flash("데이터베이스 연결 실패! Vercel 환경변수 설정을 확인하세요.")
            return redirect(url_for('login'))

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
            flash(f"로그인 중 오류 발생: {str(e)}")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()
        if db is None:
            flash("DB 연결 실패")
            return redirect(url_for('signup'))

        try:
            user_ref = db.collection('users').document(username)
            if user_ref.get().exists:
                flash("이미 존재하는 아이디입니다.")
            else:
                user_ref.set({'username': username, 'password': password, 'role': 'user'})
                flash("회원가입 성공!")
                return redirect(url_for('login'))
        except Exception as e:
            flash(f"회원가입 오류: {str(e)}")
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)