import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, make_response
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

DB_PATH = os.path.join(os.path.dirname(__file__), "complaints.db")
OFFICER_PIN = os.environ.get("OFFICER_PIN", "thfvcbdkiem3640")

# ---------- i18n ----------
I18N = {
    'en': {
        'site_title': 'Aran: Empowering Women, Protecting Children, Speak Up Safely',
        'nav_home': 'Home',
        'nav_track': 'Track',
        'nav_register': 'Register',
        'nav_login': 'Login',
        'nav_logout': 'Logout',
        'lang_toggle': 'தமிழ்',
        'submit_heading': 'Submit Complaint',
        'petitioner_name': 'Petitioner Name',
        'dob': 'DOB',
        'taluk': 'Taluk',
        'firka': 'Firka',
        'village': 'Village',
        'description': 'Description',
        'submit_btn': 'Submit',
        'login_prompt': 'Please login to submit a petition.',
        'guidelines_title': 'Guidelines',
        'guideline_1': 'Enter Anonymous if you want to keep your identity confidential.',
        'guideline_2': 'Include Perpetrator Information.',
        'guideline_3': 'If registering a Child Harassment, Please Enter On Behalf',
        'my_petitions_title': 'My Complaints',
        'name_col': 'Name',
        'location_col': 'Location',
        'response_col': 'Response',
        'status_col': 'Status',
        'created_col': 'Created',
        'download_col': 'Download',
        'no_petitions': 'No complaints yet.',
        'select': 'Select',
        'track_title': 'Track complaint',
        'petition_id': 'Complaint ID',
        'search_btn': 'Search',
        'track_helper': 'Enter your Complaint ID to view status and download PDF.',
        'results': 'Results',
        'footer': '© Tenkasi District Administration. All rights reserved.'
    },
    'ta': {
        'site_title': 'தொழியின் அரண்',
        'nav_home': 'முகப்பு',
        'nav_track': 'நிலை',
        'nav_register': 'பதிவு',
        'nav_login': 'உள்நுழை',
        'nav_logout': 'வெளியேறு',
        'lang_toggle': 'English',
        'submit_heading': 'மனு சமர்ப்பிக்க',
        'petitioner_name': 'மனுதாரர் பெயர்',
        'dob': 'பிறந்த தேதி',
        'taluk': 'தாலுக்கு',
        'firka': 'ஃபிர்கா',
        'village': 'கிராமம்',
        'description': 'விவரம்',
        'submit_btn': 'சமர்ப்பிக்க',
        'login_prompt': 'மனு சமர்ப்பிக்க தயவு செய்து உள்நுழைக.',
        'guidelines_title': 'வழிகாட்டுதல்',
        'guideline_1': 'உங்கள் அடையாளத்தை ரகசியமாக வைத்திருக்க விரும்பினால் "அநாமதேயர்" என பதிவிடவும்.',
        'guideline_2': 'சம்பவத்தில் தொடர்புடைய நபரின் விவரங்களை குறிப்பிடவும்.',
        'guideline_3': 'குழந்தை தொந்தரவு சம்பவத்தை பதிவு செய்கிறீர்களானால், தயவு செய்து "On Behalf" பகுதியில் பதிவு செய்யவும்.',
        'my_petitions_title': 'எனது புகார் பட்டியல்',
        'name_col': 'பெயர்',
        'location_col': 'இருப்பிடம்',
        'response_col': 'பதில்',
        'status_col': 'நிலை',
        'created_col': 'உருவாக்கப்பட்டது',
        'download_col': 'பதிவிறக்க',
        'no_petitions': 'இதுவரை மனுக்கள் இல்லை.',
        'select': 'தேர்வு',
        'track_title': 'மனு நிலையைப் பார்க்க',
        'petition_id': 'மனு எண்',
        'search_btn': 'தேடுக',
        'track_helper': 'உங்கள் மனு எண்ணை உள்ளிட்டு நிலையை பார்க்கவும், PDF பதிவிறக்கவும்.',
        'results': 'முடிவுகள்',
        'footer': '© தென்காசி மாவட்ட நிர்வாகம். அனைத்தும் உரிமையுரியது.'
    }
}

# ---------- Locations mapping (Taluk -> Firka -> [villages]) ----------
# (Using the mapping provided by the user)
locations = {
  "Tenkasi": {
    "Kallurani": [
      "Sundarapandiapuram","Thiruchitrambalam","Melapavoor","Pattakuruchi","Gunaramanallur",
      "Kulasekarapatti","Kallurani","Thippanampatti","Avudaiyannur"
    ],
    "Tenkasi": [
      "Pulliyur","Tenkasi","Kuthukkalvalasai","Ilanji","Courtrallam","Melagaram",
      "Pattapathu","Minnadicheri","Ayiraperi","Mathalamparai","Sillaraipuravu"
    ],
    "Kadayam": [
      "Mela Kadaiyam","Therkku Madathur","Ayan Pottalpudhur","Therkku Kadaiyam","Veerasamudram",
      "Ravanasamudram","Govindaperi","Ayan Dharmapuramadam","Kadaiyam Perumpathu Part-1",
      "Kadaiyam Perumpathu Part-2","Keela Kadaiyam Part-1","Keela Kadaiyam Part-2"
    ],
    "Alwarkurichi": [
      "Sivasailam","Keela Ambur","Vadakku Pappankulam","Adaichani","Alwarkurichi Part-1",
      "Alwarkurichi Part-2","Mela Ambur Part-1","Mela Ambur Part-2"
    ]
  },
  "Kadayanallur": {
    "Puliyangudi": [
      "Nagaram","Malayadikkurichi","Chinthamani","Puliyangudi","Melapuliyankudi",
      "Thirumalainayakan Pudukudi","Thalaivankottai","Ramasamiyapuram","Alangulam"
    ],
    "Kadayanallur": [
      "Vairavankulam","Krishnapuram","Chokkampatti","Boganallur","Kanagasabapathiperi",
      "Kadayanallur","Kasitharmam","Punnaivanam","Madathupatti","Ariyanayagipuram",
      "Sendamangalam","Achanpudur","Kampaneri Pudukudi Part-1","Kampaneri Pudukudi Part-2"
    ],
    "Ayikudi": [
      "Idaikal","Nainaragaram","Kilangadu","Kodikkurichi","Ayikudi","Urmelaalagiyaan","Poigai","Sambavar Vadakarai"
    ]
  },
  "Thiruvengadam": {
    "Karisalkulam": ["Malaiyan Kulam","Perungkottur","Chandirangondan","Azagapuri","Chavelkulam","Mathurapuri","A.Mathurapuri","A.Kariselkulam","Karisathan","Kulasekarapperi","Rengasamudram","Subbaiah Puram","Chathirapatti","Kalingapatti Part-1","Kalingapatti Part-2"],
    "Thiruvengadam": ["Thiruvengadam","Vellakulam","Kurinchakulam","Sangupatti","Maipparai","Varaganoor","Naduvappatti","Kulakkattakurichi","Sundaresapuram","Vadakku Kuruvikulam","Ramalinga Puram","Athippatti","Vagaikulam"],
    "Pazhankottai": ["K.Alangulam","Therku Kuruvikulam","Naluvasan Kottai","Pazhankottai","Usilangulam","Chettikulam","Mahendravadi","Maruthan Ginaru","Kalappalangulam","Nalanthula","K.Karisalkulam","Sayamalai Part-1","Sayamalai Part-2"]
  },
  "Sankarankoil": {
    "Karivalamvanthanallur": ["Perumalpatti","Valavanthapuram","Panthapuli","Paruvakudi","Karivalamvantha Nallur","Vayali","Kuvalaikanni","Panaiyoor","Periyoor"],
    "Sernthamangalam": ["Kulasekaramangalum","Vellalankulam","Yechantha","Pattadaikatti","Naduvakurichi-Major"],
    "Sankarankoil": ["Perumpathur","Manaloor","Vadikkottai","Kalappakulam","Sankarankovil"],
    "Veerasigamani": ["Vaddakuputhur","Veeriruppu","Nochikulam","Therku Sankarankovil","Poigai","Veerasigamani","Keelaveerasigamani"],
    "Gurukkalpatti": ["Naduvakurichi-Minor","Chinnakovilan Kulam","Periyakovilan Kulam","K.Maruthappapuram","Gurukkalpatti","Vadakku Panai Vadali","Keelaneelithanallur","Melaneelithanallur","Ilanthaikulam"]
  },
  "Shencottai": {
    "Shencottai": ["Nagalkadu","Pudur","Puliyarai","Karkudi","Sengottai Town","Sengottai Keelur","Sengottai Melur"],
    "Panpozhi": ["Mekkarai","Vadakarai Melpidagai","Vadakarai Keelpidagai","Panpoli","Thenpothai","Kanakkapillaivalasai","Periyapillaivalasai"],
    "Ilanthur": ["Neduvayal","Elathur","Kunnakudy","Piranoor","Vallam"]
  },
  "Veerakeralampudur": {
    "Veerakeralampudur": ["Vellakal","Veerakeralampudur","Rajagopalaperi","Agaram","Veeranam"],
    "Surandai": ["Kulayaneri","Sivagurunathapuram","Anaikulam","Zamin Surandai","Surandai Part-I","Surandai Part-II"],
    "Karuvantha": ["Melakalangal","Keelakalangal","Navaneethakrishnapuram","Kurichanpatti","Karuvantha","Vadi","Achankuttam"],
    "Uthumalai": ["Vadakkukavalakurichi","Uthumalai","Melamarudappapuram","Balapathiraramapuram","Marukkalankulam","Muthammalpuram"]
  },
  "Alangulam": {
    "Keelapavoor": ["Kaluneerkulam","Thuthikulam","Poolankulam","Keelapavoor Part-1","Keelapavoor Part-2","Pethanadarpatti Part-1","Pethanadarpatti Part-2"],
    "Nettur": ["Kidarakulam","Kasikkuvaithan","Kavalakuruchi","Kadanganeri","Kaduvetti","Subbiahpuram","Nettur","Naranapuram"],
    "Vengadampatti": ["Madathur","Anainthaperumalnadanur","Thuppakudi","Ravuthaperi","Anjankattalai","Venkadampatti Part-1","Venkadampatti Part-2"],
    "Puthupatti": ["Kuthapanjan","Odaimarichchan","Udaiyampuli","Pudupatti Part-1","Pudupatti Part-2","Maruthamputhur Part-1","Maruthamputhur Part-2"],
    "Alangulam": ["Mayamankuruchi","Ayyanarkulam","Sivalarkulam","Alangulam","Andipatti","Maranthai"]
  },
  "Sivagiri": {
    "Sivagiri": ["Ramanathapuram","Sivagiri - Part-1","Sivagiri - Part-2","Rayagiri - Part-1","Rayagiri - Part-2","Viswanathaperi - Part-1","Viswanathaperi - Part-2"],
    "Cuddalore": ["Inamkovilpatti","Cuddalor","Nelkkattumseval","Patakurichi","Ariyur","Thenmalai - Part-1","Thenmalai - Part-2"],
    "Vasudevanallur": ["Thirumalapuram","Vasudevanallur","Subramaniyapuram","Dharugapuram","Sanganaperi","Naranapuram - Part-1","Naranapuram - Part-2"]
  }
}
# ----------------------------------------------------------------------

STATUS_VALUES = ["Pending", "In Progress", "Resolved", "Rejected"]
STATUS_COLORS = {"Pending":"#f44336","In Progress":"#ff9800","Resolved":"#4caf50","Rejected":"#9e9e9e"}
STATUS_TAMIL = {"Pending":"நிலுவையில்","In Progress":"செயல்பாட்டில்","Resolved":"தீர்க்கப்பட்டது","Rejected":"நிராகரிக்கப்பட்டது"}

@app.context_processor
def inject_i18n():
    lang = session.get('lang', 'en')
    if lang not in I18N:
        lang = 'en'
    def status_text(s: str) -> str:
        return STATUS_TAMIL.get(s, s) if lang == 'ta' else s
    return dict(tr=I18N[lang], current_lang=lang, status_text=status_text)

@app.route('/lang/<code>')
def set_lang(code: str):
    if code not in I18N:
        return redirect(request.referrer or url_for('index'))
    session['lang'] = code
    return redirect(request.referrer or url_for('index'))

# ---------- DB helpers ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # users
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            mobile TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    # complaints (fresh schema includes new fields)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id TEXT PRIMARY KEY,
            mobile TEXT,
            petitioner_dob TEXT,
            taluk TEXT,
            firka TEXT,
            village TEXT,
            description TEXT,
            response_text TEXT,
            status TEXT,
            created_at TEXT,
            FOREIGN KEY(mobile) REFERENCES users(mobile)
        )
        """
    )
    # migrate existing complaints table to include new columns if missing
    cur.execute("PRAGMA table_info(complaints)")
    cols = [r[1] for r in cur.fetchall()]
    migrations = []
    if 'petitioner_name' not in cols:
        migrations.append("ALTER TABLE complaints ADD COLUMN petitioner_name TEXT")
    if 'petitioner_dob' not in cols:
        migrations.append("ALTER TABLE complaints ADD COLUMN petitioner_dob TEXT")
    if 'response_text' not in cols:
        migrations.append("ALTER TABLE complaints ADD COLUMN response_text TEXT")
    for m in migrations:
        try:
            cur.execute(m)
        except Exception:
            pass
    conn.commit()
    conn.close()


def create_user(mobile: str, password: str) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (mobile, password_hash, created_at) VALUES (?, ?, ?)",
            (mobile, generate_password_hash(password), datetime.now().isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user(mobile: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT mobile, password_hash, created_at FROM users WHERE mobile=?", (mobile,))
    row = cur.fetchone()
    conn.close()
    return row


def insert_complaint(c):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO complaints (id,mobile,petitioner_name,petitioner_dob,taluk,firka,village,description,response_text,status,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            c['id'],
            c['mobile'],
            c['petitioner_name'],
            c['petitioner_dob'],
            c['taluk'],
            c['firka'],
            c['village'],
            c['description'],
            c.get('response_text'),
            c['status'],
            c['created_at'],
        ),
    )
    conn.commit()
    conn.close()


def get_last_by_mobile(mobile):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT created_at FROM complaints WHERE mobile=? ORDER BY created_at DESC LIMIT 1",
        (mobile,),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def count_month_complaints(mobile: str, year: int, month: int) -> int:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM complaints
        WHERE mobile=? AND datetime(created_at) >= ? AND datetime(created_at) < ?
        """,
        (mobile, start.isoformat(), end.isoformat()),
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


def find_complaints_by_mobile(mobile):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id,mobile,petitioner_name,petitioner_dob,taluk,firka,village,description,response_text,status,created_at
        FROM complaints WHERE mobile=? ORDER BY datetime(created_at) DESC
        """,
        (mobile,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_by_id(cid):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id,mobile,petitioner_name,petitioner_dob,taluk,firka,village,description,response_text,status,created_at
        FROM complaints WHERE id=?
        """,
        (cid,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def list_all_complaints(filters: dict | None = None, limit: int = 500):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    query = (
        "SELECT id,mobile,petitioner_name,petitioner_dob,taluk,firka,village,description,response_text,status,created_at FROM complaints"
    )
    clauses = []
    params = []
    if filters:
        if filters.get('status'):
            clauses.append("status = ?")
            params.append(filters['status'])
        if filters.get('taluk'):
            clauses.append("taluk = ?")
            params.append(filters['taluk'])
        if filters.get('firka'):
            clauses.append("firka = ?")
            params.append(filters['firka'])
        if filters.get('village'):
            clauses.append("village = ?")
            params.append(filters['village'])
        if filters.get('from_date'):
            clauses.append("datetime(created_at) >= ?")
            params.append(filters['from_date'] + "T00:00:00")
        if filters.get('to_date'):
            clauses.append("datetime(created_at) <= ?")
            params.append(filters['to_date'] + "T23:59:59")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY datetime(created_at) DESC LIMIT ?"
    params.append(limit)
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_status(cid, new_status):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE complaints SET status=? WHERE id=?", (new_status, cid))
    conn.commit()
    conn.close()


def update_response_and_resolve(cid: str, response_text: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE complaints SET response_text=?, status='Resolved' WHERE id=?",
        (response_text, cid),
    )
    conn.commit()
    conn.close()


# ---------- Routes ----------
@app.route("/")
def index():
    user_mobile = session.get("user_mobile")
    my_complaints = []
    if user_mobile:
        my_complaints = find_complaints_by_mobile(user_mobile)
    return render_template("index.html", user_mobile=user_mobile, my_complaints=my_complaints, status_colors=STATUS_COLORS)


@app.route("/locations")
def get_locations():
    return jsonify(locations)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "")
    if not mobile or not password:
        flash("Mobile and password are required")
        return redirect(url_for("register"))
    if create_user(mobile, password):
        flash("Registration successful. Please login.")
        return redirect(url_for("login"))
    else:
        flash("Mobile already registered")
        return redirect(url_for("register"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "")
    row = get_user(mobile)
    if not row:
        flash("Invalid credentials")
        return redirect(url_for("login"))
    if not check_password_hash(row[1], password):
        flash("Invalid credentials")
        return redirect(url_for("login"))
    session["user_mobile"] = mobile
    flash("Logged in successfully")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("user_mobile", None)
    return redirect(url_for("index"))


@app.route("/submit", methods=["POST"])
def submit():
    user_mobile = session.get("user_mobile")
    if not user_mobile:
        return jsonify({"status": "error", "message": "Login required."}), 401
    petitioner_name = request.form.get("petitioner_name", "").strip()
    petitioner_dob = request.form.get("petitioner_dob", "").strip()
    taluk = request.form.get("taluk")
    firka = request.form.get("firka")
    village = request.form.get("village")
    description = request.form.get("description", "").strip()

    if not petitioner_name or not petitioner_dob or not taluk or not firka or not village or not description:
        return jsonify({"status":"error","message":"All fields required."}), 400

      # enforce max 2 per calendar month
    now = datetime.now()
    count_this_month = count_month_complaints(user_mobile, now.year, now.month)
    if count_this_month >= 10:
        return jsonify({"status":"error","message":f"Monthly limit reached. Only 10 petitions allowed in {now.strftime('%B %Y')}."}), 429

    cid = str(uuid.uuid4())[:8]
    complaint = {
        "id": cid,
        "mobile": user_mobile,
        "petitioner_name": petitioner_name,
        "petitioner_dob": petitioner_dob,
        "taluk": taluk,
        "firka": firka,
        "village": village,
        "description": description,
        "response_text": None,
        "status": "Pending",
        "created_at": datetime.now().isoformat()
    }
    insert_complaint(complaint)
    return jsonify({"status":"success","message":"Petition registered.","complaint_id": cid})


@app.route("/track", methods=["GET","POST"])
def track():
    if request.method == "GET":
        return render_template("track.html")
    key = request.form.get("key", "").strip()
    result = None
    if not key:
        flash("Enter mobile number or petition ID.")
        return redirect(url_for("track"))
    row = get_by_id(key)
    if row:
        result = [row]
    else:
        rows = find_complaints_by_mobile(key)
        result = rows
    return render_template("track.html", results=result, status_colors=STATUS_COLORS)


@app.route("/petition/<cid>/download")
def download_petition(cid: str):
    row = get_by_id(cid)
    if not row:
        return "Not found", 404
    # Build PDF in memory
    buf = BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    left_margin = 1.5 * cm
    right_margin = 1.5 * cm
    x = left_margin
    y = height - 1.5 * cm
    max_width = width - left_margin - right_margin

    def line(txt: str, gap: float = 0.8 * cm):
        nonlocal y
        p.drawString(x, y, txt)
        y -= gap

    p.setFont("Helvetica-Bold", 14)
    line("Tenkasi District Administration - Petition")
    p.setFont("Helvetica", 10)
    y -= 0.2 * cm

    line(f"Petition ID: {row[0]}")
    line(f"Mobile: {row[1]}")
    line(f"Petitioner Name: {row[2]}")
    line(f"DOB: {row[3]}")
    line(f"Taluk: {row[5]}")
    line(f"Firka: {row[6]}")
    line(f"Village: {row[7]}")

    y -= 0.5 * cm
    p.setFont("Helvetica-Bold", 12)
    line("Description:")
    p.setFont("Helvetica", 10)
    for para in (row[8] or "").split("\n"):
        wrapped = simpleSplit(para, "Helvetica", 10, max_width)
        for chunk in wrapped:
            line(chunk, 0.55 * cm)

    y -= 0.5 * cm
    p.setFont("Helvetica-Bold", 12)
    line("Officer Response:")
    p.setFont("Helvetica", 10)
    for para in (row[9] or "").split("\n"):
        wrapped = simpleSplit(para, "Helvetica", 10, max_width)
        for chunk in wrapped:
            line(chunk, 0.55 * cm)

    y -= 0.5 * cm
    p.setFont("Helvetica-Bold", 12)
    line("Status & Timestamps:")
    p.setFont("Helvetica", 10)
    line(f"Status: {row[10]}")
    line(f"Created At: {row[11]}")

    p.showPage()
    p.save()
    pdf = buf.getvalue()
    buf.close()

    resp = make_response(pdf)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = f"attachment; filename=petition-{cid}.pdf"
    return resp


# --- Officer ---
@app.before_request
def guard_officer_routes():
    # Protect all officer routes, except login and logout
    if request.path.startswith('/officer'):
        if request.endpoint in ('officer_login', 'officer_logout', 'static'):
            return None
        is_officer = bool(session.get('officer'))
        if not is_officer:
            return redirect(url_for('officer_login'))
        # Enforce TTL of 30 minutes
        ts = session.get('officer_at')
        try:
            ts_float = float(ts) if ts is not None else None
        except Exception:
            ts_float = None
        if ts_float is None or (datetime.now().timestamp() - ts_float) > 1800:
            session.pop('officer', None)
            session.pop('officer_at', None)
            return redirect(url_for('officer_login'))
    return None


@app.route("/officer/login", methods=["GET","POST"])
def officer_login():
    if request.method == "GET":
        # Force fresh PIN entry by clearing any existing officer session
        session.pop("officer", None)
        session.pop("officer_at", None)
        return render_template("officer_login.html")
    pin = request.form.get("pin", "")
    if pin == OFFICER_PIN:
        session["officer"] = True
        session["officer_at"] = datetime.now().timestamp()
        return redirect(url_for("officer_panel"))
    flash("Invalid PIN.")
    return redirect(url_for("officer_login"))


@app.route("/officer/logout")
def officer_logout():
    session.pop("officer", None)
    return redirect(url_for("index"))


@app.route("/officer")
def officer_root():
    return redirect(url_for("officer_login"))


@app.route("/officer/panel")
def officer_panel():
    if not session.get("officer"):
        return redirect(url_for("officer_login"))
    filters = {
        'status': request.args.get('status') or None,
        'taluk': request.args.get('taluk') or None,
        'firka': request.args.get('firka') or None,
        'village': request.args.get('village') or None,
        'from_date': request.args.get('from_date') or None,
        'to_date': request.args.get('to_date') or None,
    }
    rows = list_all_complaints(filters=filters, limit=1000)
    return render_template("officer.html", complaints=rows, statuses=STATUS_VALUES, colors=STATUS_COLORS, filters=filters)


@app.route("/officer/update", methods=["POST"])
def officer_update():
    if not session.get("officer"):
        return jsonify({"status":"error","message":"not authorized"}), 401
    cid = request.form.get("cid")
    new_status = request.form.get("status")
    response_text = request.form.get("response_text", "").strip()
    if response_text:
        update_response_and_resolve(cid, response_text)
        return redirect(url_for("officer_panel"))
    if new_status not in STATUS_VALUES:
        return jsonify({"status":"error","message":"invalid status"}), 400
    update_status(cid, new_status)
    return redirect(url_for("officer_panel"))


# ---------- Security headers ----------
@app.after_request
def add_security_headers(resp):
    resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    resp.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' data:"
    return resp


# Ensure DB is initialized when app is imported (e.g., under gunicorn)
init_db()

# ---------- start ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
