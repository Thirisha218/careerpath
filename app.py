import json, os, re, secrets
import pymysql
from dotenv import load_dotenv
from flask import jsonify, Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE") == "1")

def conn():
    extra = {"ssl_ca": os.getenv("DB_SSL_CA")} if os.getenv("DB_SSL_CA") else {}
    return pymysql.connect(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
                           user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
                           database=os.getenv("DB_NAME", "careerpath"),
                           cursorclass=pymysql.cursors.DictCursor, autocommit=True, **extra)

def run(sql, args=(), one=False, write=False):
    try:
        c = conn()
        try:
            with c.cursor() as cur:
                cur.execute(sql, args)
                return cur.lastrowid if write else (cur.fetchone() if one else cur.fetchall())
        finally:
            c.close()
    except pymysql.err.IntegrityError:
        raise
    except pymysql.MySQLError:
        app.logger.exception("database error"); abort(503)

@app.errorhandler(503)
def db_down(e): return render_template("error.html", msg="The database is unavailable. Please try again in a moment."), 503
@app.errorhandler(403)
def forb(e): return render_template("error.html", msg="You do not have access to this page."), 403
@app.errorhandler(400)
def bad(e): return render_template("error.html", msg="Your session expired. Reload the page and try again."), 400
@app.errorhandler(404)
def nf(e): return render_template("error.html", msg="That page does not exist."), 404

@app.before_request
def csrf():
    session.setdefault("_t", secrets.token_hex(16))
    if request.method == "POST" and (request.form.get("_t") or request.headers.get("X-CSRF")) != session["_t"]: abort(400)

@app.context_processor
def inject(): return dict(token=session.get("_t"), logged_in="uid" in session)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session: return redirect(url_for("login"))
        return f(*a, **k)
    return w

@app.route("/")
def home():
    return render_template("home.html", cats=run("SELECT * FROM categories"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower()
        pw, stream = request.form.get("password", ""), request.form.get("stream", "Other")
        if not (1 < len(name) <= 80 and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) and len(pw) >= 8 and stream in ("Science", "Commerce", "Arts", "Other")):
            flash("Enter a name, a valid email, and a password of at least 8 characters.", "danger")
        else:
            try:
                uid = run("INSERT INTO users(name,email,password_hash) VALUES(%s,%s,%s)", (name, email, generate_password_hash(pw)), write=True)
                run("INSERT INTO student_profiles(user_id,stream) VALUES(%s,%s)", (uid, stream), write=True)
                session.clear(); session["uid"] = uid; session["name"] = name
                return redirect(url_for("quiz"))
            except pymysql.err.IntegrityError:
                flash("That email is already registered. Try logging in.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = run("SELECT * FROM users WHERE email=%s", (request.form.get("email", "").strip().lower(),), one=True)
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session.clear(); session["uid"], session["name"], session["role"] = u["id"], u["name"], u["role"]
            return redirect(url_for("results"))
        flash("Email or password is incorrect.", "danger")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    run("DELETE FROM users WHERE id=%s", (session["uid"],), write=True)
    session.clear(); flash("Your account and data were deleted.", "success"); return redirect(url_for("home"))

@app.route("/courses")
def courses():
    s, cat = request.args.get("q", "").strip(), request.args.get("category", type=int)
    order = {"name": "c.name", "duration": "c.duration_years"}.get(request.args.get("sort"), "c.name")
    sql, args = "SELECT c.*, g.name cat, g.icon FROM courses c JOIN categories g ON g.id=c.category_id WHERE 1=1", []
    if s: sql += " AND (c.name LIKE %s OR c.description LIKE %s)"; args += [f"%{s}%"] * 2
    if cat: sql += " AND c.category_id=%s"; args.append(cat)
    rows = run(sql + f" ORDER BY {order}", args)
    saved = {r["course_id"] for r in run("SELECT course_id FROM saved_courses WHERE user_id=%s", (session["uid"],))} if "uid" in session else set()
    return render_template("courses.html", rows=rows, cats=run("SELECT * FROM categories"), saved=saved, q=s, cat=cat, sort=request.args.get("sort", "name"))

@app.route("/courses/<int:cid>/save", methods=["POST"])
@login_required
def save_course(cid):
    if run("SELECT 1 FROM saved_courses WHERE user_id=%s AND course_id=%s", (session["uid"], cid), one=True):
        run("DELETE FROM saved_courses WHERE user_id=%s AND course_id=%s", (session["uid"], cid), write=True)
    elif run("SELECT 1 FROM courses WHERE id=%s", (cid,), one=True):
        run("INSERT INTO saved_courses VALUES(%s,%s)", (session["uid"], cid), write=True)
    return redirect(request.referrer or url_for("courses"))

@app.route("/saved")
@login_required
def saved():
    rows = run("SELECT c.*, g.name cat, g.icon FROM saved_courses s JOIN courses c ON c.id=s.course_id JOIN categories g ON g.id=c.category_id WHERE s.user_id=%s", (session["uid"],))
    return render_template("courses.html", rows=rows, cats=[], saved={r["id"] for r in rows}, q="", cat=None, sort="name", saved_page=True)

@app.route("/careers/<int:cid>")
def career(cid):
    c = run("SELECT r.*, g.name cat FROM careers r JOIN categories g ON g.id=r.category_id WHERE r.id=%s", (cid,), one=True) or abort(404)
    return render_template("career.html", c=c, steps=c["roadmap"].split("\n"),
                           courses=run("SELECT * FROM courses WHERE category_id=%s", (c["category_id"],)))

# Quiz: each option adds a point to one category id (1 Tech, 2 Health, 3 Business, 4 Creative)
QUIZ = [
 ("Which activity sounds most fun?", ["Building an app or website", "Helping someone feel better", "Running a small business or event", "Designing posters or making videos"]),
 ("Your favourite school subject?", ["Maths / Computer Science", "Biology", "Economics / Accountancy", "Art / Languages"]),
 ("In a group project you usually...", ["Solve the technical problem", "Look after the team's wellbeing", "Plan and lead", "Come up with the ideas and look"]),
 ("Which workplace appeals to you?", ["Tech company", "Hospital or clinic", "Corporate office", "Studio or newsroom"]),
 ("What do you want to be known for?", ["Inventing useful things", "Saving or improving lives", "Building successful ventures", "Creating things people love"]),
 ("Pick a weekend project", ["Code a small game", "Volunteer at a health camp", "Sell something online", "Shoot and edit a short film"]),
]

@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():
    if request.method == "POST":
        scores = {1: 0, 2: 0, 3: 0, 4: 0}
        for i in range(len(QUIZ)):
            a = request.form.get(f"q{i}", type=int)
            if a not in (0, 1, 2, 3):
                flash("Please answer every question.", "danger"); return render_template("quiz.html", quiz=QUIZ)
            scores[a + 1] += 1
        run("INSERT INTO assessments(user_id,scores) VALUES(%s,%s)", (session["uid"], json.dumps(scores)), write=True)
        return redirect(url_for("results"))
    return render_template("quiz.html", quiz=QUIZ)

@app.route("/results")
@login_required
def results():
    a = run("SELECT scores FROM assessments WHERE user_id=%s ORDER BY created_at DESC, id DESC LIMIT 1", (session["uid"],), one=True)
    if not a: return render_template("results.html", ranked=None)
    sc = {int(k): v for k, v in json.loads(a["scores"]).items()}
    cats = {c["id"]: c for c in run("SELECT * FROM categories")}
    ranked = []
    for cid in sorted(sc, key=sc.get, reverse=True)[:2]:
        if sc[cid]:
            ranked.append(dict(cat=cats[cid], pct=round(100 * sc[cid] / len(QUIZ)), careers=run("SELECT id,title,summary FROM careers WHERE category_id=%s", (cid,))))
    return render_template("results.html", ranked=ranked)

@app.route("/scholarships")
def scholarships():
    return render_template("scholarships.html", rows=run("SELECT * FROM scholarships"))

@app.route("/about")
def about(): return render_template("about.html")

@app.cli.command("create-demo")
def create_demo():
    """Create a non-production test student: demo@example.com / Demo@1234"""
    uid = run("INSERT IGNORE INTO users(name,email,password_hash) VALUES('Demo Student','demo@example.com',%s)", (generate_password_hash("Demo@1234"),), write=True)
    if uid: run("INSERT IGNORE INTO student_profiles VALUES(%s,'Science')", (uid,), write=True)
    print("demo@example.com / Demo@1234")

# ---------- Phase 2: REST API, compare, chat, admin ----------
from functools import wraps

def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if session.get("role") != "admin": abort(403)
        return f(*a, **k)
    return w

@app.get("/api/courses")
def api_courses():
    return jsonify(run("SELECT c.id,c.name,c.duration_years,c.eligibility,c.description,g.name category FROM courses c JOIN categories g ON g.id=c.category_id"))

@app.get("/api/courses/<int:cid>")
def api_course(cid):
    return jsonify(run("SELECT * FROM courses WHERE id=%s", (cid,), one=True) or abort(404))

@app.get("/api/careers")
def api_careers():
    return jsonify(run("SELECT id,title,summary,category_id FROM careers"))

@app.get("/api/careers/<int:cid>")
def api_career(cid):
    c = run("SELECT * FROM careers WHERE id=%s", (cid,), one=True) or abort(404)
    c["roadmap"] = c["roadmap"].split("\n"); return jsonify(c)

@app.get("/api/scholarships")
def api_scholarships(): return jsonify(run("SELECT * FROM scholarships"))

@app.get("/api/recommendations")
def api_recs():
    if "uid" not in session: return jsonify(error="Login required"), 401
    a = run("SELECT scores FROM assessments WHERE user_id=%s ORDER BY created_at DESC, id DESC LIMIT 1", (session["uid"],), one=True)
    if not a: return jsonify([])
    sc = json.loads(a["scores"]); top = sorted(sc, key=lambda k: sc[k], reverse=True)[:2]
    return jsonify([dict(category_id=int(k), match_pct=round(100 * sc[k] / len(QUIZ)), careers=run("SELECT id,title FROM careers WHERE category_id=%s", (k,))) for k in top if sc[k]])

@app.route("/compare")
def compare():
    allc = run("SELECT id,title FROM careers ORDER BY title")
    a, b = request.args.get("a", type=int), request.args.get("b", type=int)
    pair = [run("SELECT title,study_years,demand_score,entry_pay_lpa FROM careers WHERE id=%s", (i,), one=True) for i in (a, b)] if a and b else None
    if pair and not all(pair): pair = None
    if pair: pair = [{k: float(v) if k != "title" else v for k, v in p.items()} for p in pair]
    return render_template("compare.html", allc=allc, a=a, b=b, pair=pair)

@app.route("/chat")
def chat(): return render_template("chat.html")

@app.post("/api/chat")
def api_chat():
    m = ((request.get_json(silent=True) or {}).get("message") or "").strip()[:200].lower()
    if not m: return jsonify(error="Type a question first."), 400
    words = {w for w in re.findall(r"[a-z]+", m) if len(w) > 3}
    if "scholar" in m:
        rows = run("SELECT name,eligibility FROM scholarships")
        return jsonify(reply="Sample scholarships: " + "; ".join(f"{r['name']} ({r['eligibility']})" for r in rows) + ". Check official sites for real ones.")
    hit = [c for c in run("SELECT c.id,c.title,c.summary,g.name cat FROM careers c JOIN categories g ON g.id=c.category_id")
           if words & set(re.findall(r"[a-z]+", (c["title"] + " " + c["cat"]).lower()))]
    crs = [c for c in run("SELECT name,duration_years,eligibility FROM courses") if words & set(re.findall(r"[a-z]+", c["name"].lower()))]
    if not hit and not crs:
        return jsonify(reply="I could not match that. Try a career or course name like 'software developer' or 'nursing', or take the career quiz.")
    out = [f"{c['title']}: {c['summary']} Roadmap: /careers/{c['id']}" for c in hit[:3]]
    out += [f"{c['name']} takes {c['duration_years']} years. Eligibility: {c['eligibility']}" for c in crs[:3]]
    return jsonify(reply=" | ".join(out))

@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", courses=run("SELECT c.id,c.name,g.name cat FROM courses c JOIN categories g ON g.id=c.category_id"),
                           schs=run("SELECT * FROM scholarships"), cats=run("SELECT * FROM categories"),
                           n_users=run("SELECT COUNT(*) n FROM users", one=True)["n"], n_tests=run("SELECT COUNT(*) n FROM assessments", one=True)["n"])

@app.post("/admin/courses")
@admin_required
def admin_add_course():
    f = request.form
    try:
        v = (int(f["category_id"]), f["name"].strip()[:120], float(f["duration"]), f["eligibility"].strip()[:255], f["description"].strip())
        assert all(v[1:2] + v[3:]) and 0 < v[2] <= 10
        run("INSERT INTO courses(category_id,name,duration_years,eligibility,description) VALUES(%s,%s,%s,%s,%s)", v, write=True)
        flash("Course added.", "success")
    except (KeyError, ValueError, AssertionError, pymysql.err.IntegrityError):
        flash("Fill every course field with valid values.", "danger")
    return redirect(url_for("admin"))

@app.post("/admin/courses/<int:cid>/delete")
@admin_required
def admin_del_course(cid):
    run("DELETE FROM courses WHERE id=%s", (cid,), write=True); flash("Course deleted.", "success"); return redirect(url_for("admin"))

@app.post("/admin/scholarships")
@admin_required
def admin_add_sch():
    n, e, u = request.form.get("name", "").strip()[:120], request.form.get("eligibility", "").strip()[:255], request.form.get("url", "").strip()[:255]
    if not (n and e) or (u and not u.startswith("https://")): flash("Enter a name, eligibility, and an https:// link if you add one.", "danger")
    else: run("INSERT INTO scholarships(name,eligibility,official_url) VALUES(%s,%s,%s)", (n, e, u or None), write=True); flash("Scholarship added.", "success")
    return redirect(url_for("admin"))

@app.post("/admin/scholarships/<int:sid>/delete")
@admin_required
def admin_del_sch(sid):
    run("DELETE FROM scholarships WHERE id=%s", (sid,), write=True); flash("Scholarship deleted.", "success"); return redirect(url_for("admin"))

@app.cli.command("create-admin")
def create_admin():
        """Create an admin using ADMIN_PASSWORD from the environment"""
        run("INSERT IGNORE INTO users(name,email,password_hash,role) VALUES('Admin','admin@example.com',%s,'admin')", (generate_password_hash(os.environ["ADMIN_PASSWORD"]),), write=True)
        print("Admin created: admin@example.com")
