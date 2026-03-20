import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_final_secret'

def get_db():
    if not firebase_admin._apps:
        # 쪼개서 넣은 환경변수들 가져오기
        project_id = os.environ.get('FB_PROJECT_ID')
        client_email = os.environ.get('FB_CLIENT_EMAIL')
        private_key = os.environ.get('FB_PRIVATE_KEY')

        if not all([project_id, client_email, private_key]):
            # 로컬 환경 (파일 존재 시)
            try:
                cred = credentials.Certificate('firebase_key.json')
                firebase_admin.initialize_app(cred)
                return firestore.client()
            except: return None

        try:
            # 환경변수에서 가져온 프라이빗 키의 줄바꿈 보정
            formatted_key = private_key.replace('\\n', '\n')
            
            # 인증서 딕셔너리 수동 조립
            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": formatted_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            
            return google_firestore.Client(
                project=project_id,
                credentials=cred._get_credential()
            )
        except Exception as e:
            print(f"🚨 인증서 조립 실패: {str(e)}")
            return None
    else:
        return firestore.client()

# --- 라우팅 (로그인/회원가입 로직은 동일) ---

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        if not db:
            flash("DB 연결 실패! 환경변수(ID, Email, Key)를 다시 확인하세요.")
            return redirect(url_for('login'))
        
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        try:
            user_ref = db.collection('users').document(username)
            doc = user_ref.get()
            if doc.exists and doc.to_dict().get('password') == password:
                session['user'] = username
                return redirect(url_for('home'))
            else:
                flash("아이디 또는 비밀번호가 틀렸습니다.")
        except Exception as e:
            flash(f"오류: {str(e)}")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        db = get_db()
        if not db:
            flash("DB 연결 실패!")
            return redirect(url_for('signup'))
        
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        try:
            user_ref = db.collection('users').document(username)
            if not user_ref.get().exists:
                user_ref.set({'username': username, 'password': password, 'role': 'user'})
                flash("가입 성공!")
                return redirect(url_for('login'))
            else:
                flash("이미 존재하는 아이디입니다.")
        except Exception as e:
            flash(f"오류: {str(e)}")
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)