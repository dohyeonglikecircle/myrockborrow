import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_multi_inst_2026'

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

# 세션별 색상 지정
SESSION_COLORS = {
    'Guitar': '#e67e22', 'Base': '#f1c40f', 'Drum': '#3498db', 'Keyboard': '#9b59b6', 'Vocal': '#2ecc71'
}

def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json() if res.status_code == 200 else {}
    except: return {}

@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'): return redirect(url_for('login'))

    # 1. 파트장 정보 가져오기
    s_raw = get_fb(f"sessions/{session_name}").get('fields', {})
    leader = {
        'name': s_raw.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_raw.get('instagram', {}).get('stringValue', '@moyorak')
    }

    # 2. 악기 목록 가져오기 (기타, 베이스는 여러 대)
    # 실제 운영 시에는 'instruments' 컬렉션에서 해당 세션으로 필터링된 목록을 가져옵니다.
    instruments = []
    if session_name in ['Guitar', 'Base']:
        # 예시: 관리자가 등록한 악기들 (실제로는 DB 반복문 처리)
        instruments = [
            {'id': 'inst1', 'name': f'{session_name} 1호 (펜더)', 'img': 'url1'},
            {'id': 'inst2', 'name': f'{session_name} 2호 (깁슨)', 'img': 'url2'}
        ]
    elif session_name in ['Drum', 'Keyboard']:
        instruments = [{'id': 'inst_single', 'name': f'{session_name} 공용', 'img': 'url'}]

    # 3. 주간 날짜 계산
    today = datetime.now()
    start_week = today - timedelta(days=today.weekday())
    week_days = [(start_week + timedelta(days=i)).strftime('%m/%d') for i in range(7)]

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           instruments=instruments,
                           week_days=week_days,
                           color=SESSION_COLORS.get(session_name, '#333'))

# --- [추가] 관리자 악기 등록 API (사진 URL 포함) ---
@app.route('/admin/add_instrument', methods=['POST'])
def add_instrument():
    if session.get('user') != 'admin': return redirect('/')
    
    s_name = request.form.get('session_name') # Guitar, Base 등
    i_name = request.form.get('inst_name')
    i_img = request.form.get('inst_img_url') # 사진 파일 대신 URL로 관리 권장
    
    payload = {
        "fields": {
            "name": {"stringValue": i_name},
            "image_url": {"stringValue": i_img},
            "session": {"stringValue": s_name},
            "is_available": {"booleanValue": True}
        }
    }
    requests.post(f"{BASE_URL}/instruments", json=payload)
    flash(f"{i_name} 등록 완료!")
    return redirect(url_for('admin_setup'))