import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_2026_premium_key'

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json().get('fields', {}) if res.status_code == 200 else {}
    except: return {}

@app.route('/')
def home():
    # 키보드/드럼 활성화 상태 확인용 데이터 전달
    v_status = get_fb("sessions/Vocal") # 예시로 보컬 데이터 참고
    return render_template('index.html', user=session.get('user'))

# --- 🎸 세션 상세 페이지 (복합 로직) ---
@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'):
        flash("로그인이 필요합니다.")
        return redirect(url_for('login'))

    # 1. 오른쪽 파트장 정보 (이름, 인스타)
    s_data = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_data.get('leader_name', {}).get('stringValue', '미정'),
        'instagram': s_data.get('instagram', {}).get('stringValue', '@moyorak_official')
    }
    
    # 키보드/드럼 활성화 체크
    is_active = s_data.get('is_active', {}).get('booleanValue', True)
    if session_name in ['Keyboard', 'Drum'] and not is_active:
        return "<h3>현재 공연 기간이 아니어서 비활성화된 세션입니다.</h3><a href='/'>홈으로</a>"

    # 2. 중앙 악기 목록 (Guitar, Base 전용)
    # 실제로는 instruments 컬렉션에서 해당 세션을 filter해서 가져와야 함 (현재는 샘플)
    inst_list = [] 
    if session_name in ['Guitar', 'Base']:
        # DB에서 악기 리스트를 가져오는 로직 (REST API 쿼리는 복잡하므로 일단 구조만)
        inst_list = [{'id': '1', 'name': '펜더 스트라토캐스터', 'img': 'url', 'status': '대여가능'}]

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           instruments=inst_list,
                           user=session.get('user'))

# --- ⚙️ 관리자: 악기 등록 및 키보드/드럼 활성화 ---
@app.route('/admin/manage', methods=['GET', 'POST'])
def admin_manage():
    if session.get('user') != 'admin': return redirect('/')
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'toggle_session':
            s_name = request.form.get('s_name')
            current_status = request.form.get('status') == 'true'
            # DB 업데이트 로직 (PATCH)
            url = f"{BASE_URL}/sessions/{s_name}?updateMask.fieldPaths=is_active"
            requests.patch(url, json={"fields": {"is_active": {"booleanValue": not current_status}}})
            
    return render_template('admin_manage.html')

if __name__ == '__main__':
    app.run(debug=True)