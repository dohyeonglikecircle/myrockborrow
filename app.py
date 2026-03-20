import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as google_firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_1234_secret'

def get_db():
    if not firebase_admin._apps:
        # 환경변수 가져오기
        raw_key = os.environ.get('FIREBASE_KEY', '').strip()
        
        if not raw_key:
            # 로컬 테스트 (파일 존재 시)
            try:
                cred = credentials.Certificate('firebase_key.json')
                firebase_admin.initialize_app(cred)
                return firestore.client()
            except: return None

        try:
            # [강제 보정 로직] 
            # 1. Vercel이 앞뒤에 붙였을지 모르는 따옴표 제거
            if raw_key.startswith('"') and raw_key.endswith('"'):
                raw_key = raw_key[1:-1]
            
            # 2. 파이썬 스타일의 이중 백슬래시 보정
            raw_key = raw_key.replace('\\\\n', '\\n')
            
            # 3. JSON 파싱
            cred_dict = json.loads(raw_key, strict=False)
            
            # 4. private_key 내의 실제 줄바꿈 문자 처리
            if 'private_key' in cred_dict:
                cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            
            return google_firestore.Client(
                project=cred_dict['project_id'],
                credentials=cred._get_credential()
            )
        except Exception as e:
            # 실패 시 로그에 에러 원인 출력
            print(f"🚨 JSON 파싱 최종 실패: {str(e)}")
            return None
    else:
        return firestore.client()

# --- 이하 라우팅 (기존과 동일하지만 db 체크 강화) ---

@app.route('/')
def home():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        if not db:
            flash("DB 연결 실패! 환경변수 형식이 여전히 잘못되었습니다.")
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