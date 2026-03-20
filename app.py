import json  # 💥 import는 무조건 맨 위로!
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'moyorak_secret_key_1234'

app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ==========================================
# 💥 파이어베이스 연결 (보안 강화 및 중복 제거 버전) 💥
# ==========================================
firebase_key_json = os.environ.get('FIREBASE_KEY')

if firebase_key_json:
    # 1. Render 배포 서버일 때 (환경변수 사용)
    cred_dict = json.loads(firebase_key_json)
    cred = credentials.Certificate(cred_dict)
else:
    # 2. 내 컴퓨터 로컬 환경일 때 (파일 사용)
    # 반드시 파일명이 firebase_key.json 이어야 해!
    cred = credentials.Certificate('firebase_key.json')

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()
# ==========================================

# (이 아래 @app.route('/') 부터는 기존 코드 그대로 놔두면 됨!)
@app.route('/')
def home(): return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        if username == 'admin':
            generation, session_type = '없음', 'admin'
        else:
            generation = request.form['generation']
            session_type = request.form['session_type']
        db.collection('users').document(username).set({
            'password': password, 'name': name, 'generation': generation, 'session_type': session_type
        })
        flash("회원가입이 완료되었습니다. 로그인해주세요!")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        doc = db.collection('users').document(username).get()
        if doc.exists and doc.to_dict().get('password') == password:
            session['username'] = username
            return redirect('/')
        flash("아이디나 비밀번호가 틀렸습니다.")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add():
    if session.get('username') != 'admin': 
        flash("관리자만 접근 가능합니다.")
        return redirect('/')
    if request.method == 'POST':
        name = request.form['name']
        session_type = request.form['session_type']
        status = request.form['status']
        file = request.files.get('image_file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_url = '/' + file_path
        else: image_url = ''
        db.collection('instruments').add({
            'name': name, 'session_type': session_type, 'status': status, 'image_url': image_url
        })
        return redirect(url_for('session_page', session_name=session_type))
    return render_template('admin_add.html')

@app.route('/admin/delete/<item_id>/<session_name>')
def admin_delete(item_id, session_name):
    if session.get('username') == 'admin': db.collection('instruments').document(item_id).delete()
    return redirect(url_for('session_page', session_name=session_name))

@app.route('/admin/update_leader/<session_name>', methods=['POST'])
def update_leader(session_name):
    if session.get('username') != 'admin': return redirect('/')
    db.collection('leaders').document(session_name).set({'name': request.form['name'], 'insta': request.form['insta']})
    return redirect(url_for('session_page', session_name=session_name))

@app.route('/admin/toggle_booking', methods=['POST'])
def toggle_booking():
    if session.get('username') != 'admin': return redirect('/')
    current_doc = db.collection('settings').document('booking').get()
    current_status = current_doc.to_dict().get('is_active', False) if current_doc.exists else False
    db.collection('settings').document('booking').set({'is_active': not current_status})
    return redirect(request.referrer or '/')

@app.route('/book/<session_name>', methods=['POST'])
def book_instrument(session_name):
    username = session.get('username')
    if not username: 
        flash("로그인이 필요합니다.")
        return redirect(url_for('login'))

    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    model = request.form.get('model', '기본 장비')

    user_doc = db.collection('users').document(username).get()
    if not user_doc.exists: return redirect('/')
    user_data = user_doc.to_dict()
    
    gen = user_data.get('generation', '')
    name = user_data.get('name', username)
    user_actual_session = user_data.get('session_type', '') 
    gen_str = "" if gen == "없음" else str(gen) 
    initials = {'Keyboard': 'K', 'Drum': 'D', 'Guitar': 'G', 'Base': 'B', 'Vocal': 'V', 'admin': 'A'}
    display_name = f"{gen_str}{initials.get(user_actual_session, '')} {name}".strip()

    start_dt = datetime.strptime(start_time, "%H:%M")
    if end_time == "24:00":
        end_dt = datetime.strptime("23:59", "%H:%M") + timedelta(minutes=1)
    else:
        end_dt = datetime.strptime(end_time, "%H:%M")

    if start_dt >= end_dt:
        flash("종료 시간이 시작 시간보다 늦어야 합니다. 다시 설정해주세요!")
        return redirect(url_for('session_page', session_name=session_name, date=date))

    slots_to_book = []
    current_dt = start_dt
    while current_dt < end_dt:
        slots_to_book.append(current_dt.strftime("%H:%M"))
        current_dt += timedelta(minutes=30)

    existing_bookings = db.collection('bookings').where('session_type', '==', session_name).where('date', '==', date).where('model', '==', model).stream()
    booked_slots_db = [doc.to_dict()['time_slot'] for doc in existing_bookings]
    
    for slot in slots_to_book:
        if slot in booked_slots_db:
            flash(f"앗! '{model}' 장비는 {slot}에 이미 예약되어 있습니다.")
            return redirect(url_for('session_page', session_name=session_name, date=date))

    batch = db.batch()
    for slot in slots_to_book:
        doc_ref = db.collection('bookings').document()
        batch.set(doc_ref, {
            'session_type': session_name, 'date': date, 'time_slot': slot,
            'booked_by': username, 'display_name': display_name, 'model': model
        })
    batch.commit()
    return redirect(url_for('session_page', session_name=session_name, date=date))


@app.route('/session/<session_name>')
def session_page(session_name):
    leader_doc = db.collection('leaders').document(session_name).get()
    leader_info = leader_doc.to_dict() if leader_doc.exists else {'name': '공석', 'insta': ''}

    if session_name == 'Vocal':
        return render_template('instruments.html', session_name=session_name, leader_info=leader_info)

    elif session_name in ['Keyboard', 'Drum', 'Guitar', 'Base']:
        setting_doc = db.collection('settings').document('booking').get()
        is_booking_active = setting_doc.to_dict().get('is_active', False) if setting_doc.exists else False

        docs = db.collection('instruments').where('session_type', '==', session_name).stream()
        instruments = [{'id': doc.id, **doc.to_dict()} for doc in docs]

        target_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        monday = target_date - timedelta(days=target_date.weekday())
        
        week_days = []
        week_dates_str = []
        weekdays_kr = ['월', '화', '수', '목', '금', '토', '일']
        for i in range(7):
            day = monday + timedelta(days=i)
            week_days.append({'date': day.strftime('%Y-%m-%d'), 'label': f"{day.day}({weekdays_kr[i]})"})
            week_dates_str.append(day.strftime('%Y-%m-%d'))
            
        prev_week = (monday - timedelta(weeks=1)).strftime('%Y-%m-%d')
        next_week = (monday + timedelta(weeks=1)).strftime('%Y-%m-%d')

        time_slots = []
        for h in range(6, 24):
            time_slots.extend([f"{h:02d}:00", f"{h:02d}:30"])
        end_time_slots = time_slots[1:] + ['24:00']

        bookings_ref = db.collection('bookings').where('session_type', '==', session_name).where('date', 'in', week_dates_str).stream()
        
        booking_events = defaultdict(list)
        daily_models = {d: set() for d in week_dates_str}
        all_week_models = set() # 💥 이번 주에 등장한 모든 악기를 싹 모음!

        for doc in bookings_ref:
            data = doc.to_dict()
            d = data['date']
            slot = data['time_slot']
            model = data.get('model', '기본 장비')
            user = data.get('display_name', data['booked_by'])
            
            daily_models[d].add(model)
            all_week_models.add(model)
            event_key = (d, model, user)
            booking_events[event_key].append(slot)
            
        model_cols = {}
        for d in week_dates_str:
            model_cols[d] = {m: i for i, m in enumerate(sorted(list(daily_models[d])))}

        # 💥 색깔 겹침 원천 차단! (악기 종류를 이름순으로 0, 1, 2번 등수로 매김) 💥
        global_model_color_idx = {m: i for i, m in enumerate(sorted(list(all_week_models)))}

        grid = {d: {slot: [] for slot in time_slots} for d in week_dates_str}
        
        for d in week_dates_str:
            num_cols = len(daily_models[d]) if len(daily_models[d]) > 0 else 1
            for slot in time_slots:
                grid[d][slot] = [None] * num_cols

        for event_key, slots in booking_events.items():
            d, model, user = event_key
            slots.sort()
            col_idx = model_cols[d][model] 
            
            # 💥 이름 획수 계산 다 빼고, 악기 등수(0,1,2)를 넣어서 완벽하게 다른 색 부여!
            color_index = global_model_color_idx[model] % 5
            bg_colors = ['#4285F4', '#EA4335', '#FBBC05', '#34A853', '#9C27B0']
            text_colors = ['white', 'white', '#121212', 'white', 'white']
            
            for i, slot in enumerate(slots):
                is_start = (i == 0)
                grid[d][slot][col_idx] = {
                    'user': user,
                    'model': model,
                    'is_start': is_start,
                    'bg_color': bg_colors[color_index],
                    'text_color': text_colors[color_index]
                }

        return render_template('instruments.html', session_name=session_name, leader_info=leader_info, 
                               is_booking_active=is_booking_active, target_date_str=monday.strftime('%Y-%m-%d'),
                               prev_week=prev_week, next_week=next_week, week_days=week_days, 
                               time_slots=time_slots, end_time_slots=end_time_slots, grid=grid, instruments=instruments)

if __name__ == '__main__':
    app.run(debug=True, port=8080)