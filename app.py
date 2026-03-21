import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'moyorak_premium_system_v3'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=3)

PROJECT_ID = os.environ.get('FB_PROJECT_ID')
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

# 세션별 색상 지정
SESSION_COLORS = {
    'Guitar': '#e67e22', 'Base': '#f1c40f', 'Drum': '#3498db', 'Keyboard': '#9b59b6', 'Vocal': '#2ecc71'
}

def get_fb(path):
    try:
        res = requests.get(f"{BASE_URL}/{path}", timeout=5)
        return res.json().get('fields', {}) if res.status_code == 200 else {}
    except: return {}

# --- [1] 메인 페이지 ---
@app.route('/')
def home():
    # 키보드/드럼 활성화 상태 확인용 데이터 전달
    v_status = get_fb("sessions/Vocal") 
    return render_template('index.html', user=session.get('user'))

# --- [2] 세션 상세 페이지 (instrument.html과 연결) ---
@app.route('/session/<session_name>')
def view_session(session_name):
    if not session.get('user'):
        flash("로그인이 필요합니다.")
        return redirect(url_for('login'))

    # 1. 오른쪽 파트장 정보 (sessions 컬렉션)
    s_data = get_fb(f"sessions/{session_name}")
    leader = {
        'name': s_data.get('leader_name', {}).get('stringValue', '미정'),
        'contact': s_data.get('contact', {}).get('stringValue', '정보 없음'),
        'notice': s_data.get('notice', {}).get('stringValue', '공지사항이 없습니다.')
    }
    
    # 키보드/드럼 활성화 체크
    is_active = s_data.get('is_active', {}).get('booleanValue', True)
    if session_name in ['Keyboard', 'Drum'] and not is_active:
        return "<h3>현재 공연 기간이 아니어서 비활성화된 세션입니다.</h3><a href='/'>홈으로</a>"

    # 2. 악기 목록 가져오기 (instruments 컬렉션)
    # Guitar, Base는 여러 대의 악기를 가져옵니다.
    instruments = []
    if session_name in ['Guitar', 'Base']:
        inst_list = get_fb(f"instruments?where.session.stringValue={session_name}") # 실제로는 쿼리 필요
        for inst in inst_list:
            instruments.append({
                'id': inst.get('documentId'),
                'name': inst.get('fields', {}).get('name', {}).get('stringValue', f'{session_name} 공용'),
                'img': inst.get('fields', {}).get('image_url', {}).get('stringValue', ''),
                'status': '대여가능' if inst.get('fields', {}).get('is_available', {}).get('booleanValue', True) else '대여불가'
            })
    elif session_name in ['Drum', 'Keyboard']:
        instruments = [{'id': 'inst_single', 'name': f'{session_name} 공용', 'img': '', 'status': '대여가능'}]

    return render_template('instrument.html', 
                           session_name=session_name, 
                           leader=leader, 
                           instruments=instruments,
                           user=session.get('user'),
                           color=SESSION_COLORS.get(session_name, '#333'))

# --- [3] 관리자: 악기 등록 및 파트 정보 수정 ---
@app.route('/admin/manage', methods=['GET', 'POST'])
def admin_manage():
    if session.get('user') != 'admin': return redirect('/')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # 3-1. 악기 등록 (instruments 컬렉션)
        if action == 'add_instrument':
            s_name = request.form.get('session_name') # Guitar, Base 등
            i_name = request.form.get('inst_name')
            # Vercel에서는 파일을 Storage에 올릴 수 없으므로 Imgur URL 등을 권장
            i_img = request.form.get('inst_img_url') 
            
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
            
        # 3-2. 키보드/드럼 활성화 토글 (sessions 컬렉션)
        elif action == 'toggle_session':
            s_name = request.form.get('s_name')
            current_status = request.form.get('status') == 'true'
            url = f"{BASE_URL}/sessions/{s_name}?updateMask.fieldPaths=is_active"
            requests.patch(url, json={"fields": {"is_active": {"booleanValue": not current_status}}})
            flash(f"{s_name} 상태 변경 완료")
            
        return redirect(url_for('home'))

    return render_template('admin_manage.html')

if __name__ == '__main__':
    app.run(debug=True)