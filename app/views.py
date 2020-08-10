import datetime
import os
import uuid
import hashlib

from threading import Thread
from PIL import Image
from flask import request, redirect, session, jsonify, render_template, make_response, url_for, abort, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from flask_socketio import join_room, leave_room, emit
from app import app, socketio
from flask_mail import Mail, Message

UPLOAD_FOLDER = '/static/img'
GET_FOLDER = '/static/img-get'
PHYSICAL_ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS_PER_PAGE = 10

# NOTE: hard-coding the configuration for postgresql to prevent weird issues.
# Migrate(app,db) can be activated by calling 'flask db __' for the appropriate command.
# This now requires Postgresql, feel free to use a GUI app like Postgres.app (I'm using that).
# Don't worry, Postgresql doesn't really do anything when you aren't querying it,
# So feel free to leave it on.
#app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://preshot:wepreshot@localhost:5432/preshot"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = hashlib.sha256(b"wepreshot").hexdigest()
app.config["UPLOAD_FOLDER"] = PHYSICAL_ROOT + UPLOAD_FOLDER
app.config["GET_FOLDER"] = PHYSICAL_ROOT + GET_FOLDER
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ["PNG", "JPG", "JPEG"]

#flaskemail
app.config['DEBUG'] = True
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
#app.config['MAIL_PORT'] = 587 if ur using TLS
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'preshot.info@gmail.com'
app.config['MAIL_PASSWORD'] = 'vwxyvzweofqhlono'
app.config['MAIL_DEFAULT_SENDER'] = ('Preshotの通知','preshot.info@gmail.com')
app.config['MAIL_MAX_EMAILS'] = False
app.config['MAIL_ASCII_ATTACHMENTS'] = False

# see the img folder
# file_list = os.listdir( app.config['UPLOAD_FOLDER'] )

app.debug = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)

# Define Models

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False, unique=True)
    created_at = db.Column(db.DateTime())


class Mentor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mid = db.Column(db.String(80), nullable=False, unique=True)
    name = db.Column(db.String(80))
    email = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    filename = db.Column(db.String(255), unique=True)
    university = db.Column(db.String(80))
    faculty = db.Column(db.String(80))
    firm = db.Column(db.String(80))
    history = db.Column(db.String(255))
    position = db.Column(db.String(80))
    graduation = db.Column(db.Integer)
    comment = db.Column(db.String(255))
    created_at = db.Column(db.DateTime())


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sid = db.Column(db.String(80), nullable=False, unique=True)
    day = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(80), nullable=False)  # think it as time
    place = db.Column(db.String(80), nullable=False)
    mentor_id = db.Column(db.String(80), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime())


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.String(80), nullable=False, unique=True)
    title = db.Column(db.String(80), nullable=False)
    text = db.Column(db.UnicodeText, nullable=False)
    student_id = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime())


class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.String(80), nullable=False)
    post_id = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime())


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rid = db.Column(db.String(80), nullable=False, unique=True)
    student_id = db.Column(db.String(80), nullable=False)
    schedule_id = db.Column(db.String(80), nullable=False)
    mentor_id = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime())


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.String(80), nullable=False)
    is_mentor = db.Column(db.Boolean, nullable=False)
    message = db.Column(db.UnicodeText(), nullable=False)
    created_at = db.Column(db.DateTime(), nullable=False)

#db.create_all()


# ----------------------------------------------------------------
# Functions for images

def allowed_image(filename):
    if not "." in filename:
        return False

    ext = filename.rsplit(".", 1)[1]

    if ext.upper() in app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return True
    else:
        return False


def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))


def crop_max_square(pil_img):
    return crop_center(pil_img, min(pil_img.size), min(pil_img.size))

def send_email_thread(msg):
    with app.app_context():
        mail.send(msg)

# ----------------------------------------------------------------
# Student API
# ----------------------------------------------------------------

@app.route("/")
def index():
    student = Student.query.count()
    mentor = Mentor.query.count()
    reservation = Reservation.query.count()
    post = Post.query.count()

    data = {
            "student": student-1,
            "mentor": mentor-1,
            "reservation": reservation-1,
            "post": post-1
            }

    return render_template("index.html", data = data)

@app.route("/mentor_index")
def mentor_index():

    return render_template("mentor_index.html")

@app.route("/tutorial")
def tutorial():

    return render_template("tutorial.html")

@app.route("/test", methods=["GET"])
def test():
    mentors = Mentor.query.all()

    return render_template("test.html", mentors=mentors)

@app.route("/admin/<password>", methods=["GET"])
def admin(password):
    code = "1234"
    if password == code:
        #セッションをいれる
        session['adminkey'] = "1234"
        return redirect(url_for('emailcheck'))
    else:
        return redirect(request.url)
        

@app.route("/emailcheck", methods=["GET"])
def emailcheck():
    #verification
    # adminkey = session.get('adminkey')
    # if adminkey is not "1234":
    #     return redirect(url_for('admin/1234'))

    mentor_emails = []
    mentors = Mentor.query.all()
    for mentor in mentors:
        mentor_email = mentor.email
        mentor_emails.append(mentor_email)

    student_emails = []
    students = Student.query.all()
    for student in students:
        student_email = student.email
        student_emails.append(student_email)

    emails = {
        "student": student_emails,
        "mentor": mentor_emails
    }

    return render_template("emailcheck.html", data = emails)




@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form

        if data["email"] is "":
            flash("メールアドレスを入力してください")
            return redirect(request.url)
        if data["password"] is "":
            flash("パスワードを入力してください")
            return redirect(request.url)

        student = Student.query.filter_by(email=data["email"]).first()

        if student is None:

            uid = str(uuid.uuid4())
            session['uid'] = uid
            session.pop('mid', None)
            newuser = Student(
                email=data["email"],
                uid=uid,
                # Password now uses hashing, using sha256 + email as salt
                password=hashlib.sha256((data["password"]+data["email"]).encode('utf-8')).hexdigest(),
                created_at=datetime.datetime.now()
            )

            db.session.add(newuser)
            db.session.commit()
            flash("アカウントが作成されました")
            return redirect(url_for('tutorial'))

        else:
            if student.password == hashlib.sha256((data["password"]+data["email"]).encode('utf-8')).hexdigest():
                session['uid'] = student.uid
                session.pop('mid', None)

                flash("ログインしました")
                return redirect(url_for('mypost'))

            else:
                # "password is wrong"
                flash("パスワードが違います")
                return redirect(request.url)

    return render_template("register.html")


@app.route("/setting", methods=["GET", "DELETE"])
def setting():
    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました")
        return redirect(url_for('register'))

    student = Student.query.filter_by(uid=uid).first()

    return render_template("setting.html", data=student)


@app.route('/mypost', methods=["GET"])
def mypost():
    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました")
        return redirect(url_for('register'))

    try:
        posts = Post.query.order_by(Post.created_at.desc()).all()

        response = []

        for post in posts:
            post_data = {
                "id":post.id,
                "pid": post.pid,
                "title": post.title[:18] + " ..",
                "text": post.text[:105] + "...",
                "created_at": post.created_at
            }
            response.append(post_data)

            print(post.text)

    except FileNotFoundError:
        abort(404)

    return render_template("mypost.html", posts=response)


@app.route("/mypost/<pid>", methods=["GET"])
def eachpost(pid):
    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました")
        return redirect(url_for('register'))

    post = Post.query.filter_by(pid=pid).first()
    responses = Response.query.filter_by(post_id=pid).all()

    # Need it for reservation route
    session['pid'] = pid

    mentor_info = []

    for response in responses:
        mentor = Mentor.query.filter_by(mid=response.mentor_id).first()
        if mentor is not None:
            if mentor.filename is None:
                mentor.filename = "default.jpg"

            mentor_data = {
                "mid": mentor.mid,
                "name": mentor.name,
                "filename": 'static/img-get/' + mentor.filename
            }
            mentor_info.append(mentor_data)

    post_data = {
        "pid": post.pid,
        "title": post.title,
        "text": post.text,
        "response": mentor_info,
        "count": len(mentor_info),
        "created_at": post.created_at
    }

    return render_template('eachpost.html', post=post_data)


@app.route("/post", methods=["GET", "POST"])
def post():
    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました")
        return redirect(url_for('register'))

    if request.method == "POST":
        if request.form:
            data = request.form

            pid = str(uuid.uuid4())

            post = Post(
                title=data["title"],
                pid=pid,
                text=data["text"],
                student_id=uid,
                created_at=datetime.datetime.now()
            )

            db.session.add(post)
            db.session.commit()
            flash("投稿しました")

            return redirect(url_for('mypost'))

    return render_template("post.html")


@app.route("/select_mentor/<mid>", methods=["GET", "POST"])
def select_mentor(mid):
    # need to call the Schedule too
    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました")
        return redirect(url_for('register'))

    # Need it for making reservation post
    session['mentor_id'] = mid

    mentor = Mentor.query.filter_by(mid=mid).first()
    schedules = Schedule.query.filter_by(mentor_id=mid).filter_by(is_active=True).all()

    if mentor.filename is None:
        mentor.filename = "default.jpg"

    schedule_info = []

    for schedule in schedules:
        schedule_data = {
            "sid": schedule.sid,
            "day": schedule.day,
            "date": schedule.date,
            "place": schedule.place
        }
        schedule_info.append(schedule_data)

    mentor_data = {
        "mid": mentor.mid,
        "name": mentor.name,
        "filename": 'static/img-get/' + mentor.filename,
        "university": mentor.university,
        "faculty": mentor.faculty,
        "firm": mentor.firm,
        "position": mentor.position,
        "history": mentor.history,
        "schedule": schedule_info,
        "comment": mentor.comment,
        "graduation": mentor.graduation
    }

    return render_template("select_mentor.html", mentor=mentor_data)


@app.route("/reservation/<sid>", methods=["GET", "POST"])
def reservation(sid):
    uid = session.get('uid')
    mid = session.get('mentor_id')
    pid = session.get('pid')

    if uid is None:
        return redirect(url_for('register'))
        flash("セッションが切れました")
    if mid is None:
        return redirect(url_for('register'))
        flash("セッションが切れました")
    if pid is None:
        return redirect(url_for('register'))
        flash("セッションが切れました")

    #-------Hey roman here is what I need you to do! 1 and 2----------

    #1. I need this data to be get the data with the sid and pid condition but pid missing in Reservation schema.
    reservation = Reservation.query.filter_by(schedule_id=sid).filter_by(mentor_id=mid).filter_by(student_id=uid).first()
    #reservation = Reservation.query.filter_by(schedule_id=sid).filter_by(pid=pid).first()

    if reservation is not None:
        flash("この指導者はすでに予約済みです")
        return redirect(url_for('chat', rid = reservation.rid))

    rid = str(uuid.uuid4())

    mentor = Reservation(
        rid=rid,
        student_id=uid,
        mentor_id=mid,
        schedule_id=sid,
        created_at=datetime.datetime.now()
    )
    db.session.add(mentor)
    db.session.commit()

    post = Post.query.filter_by(pid=pid).first()
    post_data = "タイトル:\n" + post.title 
    post_data2 = "質問内容:\n" + post.text

    c = Chat(
        reservation_id=rid,
        is_mentor=False,
        message=post_data,
        created_at=datetime.datetime.now()
    )
    db.session.add(c)
    db.session.commit()

    c = Chat(
        reservation_id=rid,
        is_mentor=False,
        message=post_data2,
        created_at=datetime.datetime.now()
    )
    db.session.add(c)
    db.session.commit()

    #2. I need those reservation_info(post.title, post.text) to be sent in the chat

    #flask_mail
    schedule = Schedule.query.filter_by(sid=sid).first()
    #schedule_info = schedule.day + schedule.date + '時に' + schedule.place
    student = Student.query.filter_by(uid=uid).first()

    mentor = Mentor.query.filter_by(mid=mid).first()

    msg = Message('就活生から指導の予約が入りました！', recipients=[mentor.email])
    html = "就活生から以下の内容で指導の予約が入りました。<br><br>"\
        "曜日：{0}<br>時間：{1}<br>場所：{2}<br><br>"\
        "今すぐPreshotにログインして指導を開始しましょう！<br>https://preshot.app/mentor_register<br>（＊モバイル端末のみ対応）<br><br>"\
        "----------------------------<br>運営：team preshot<br>Email：preshot.info@gmail.com<br>HP：https://preshot.app/<br>----------------------------".format(schedule.day, schedule.date, schedule.place)
    mail.send(msg)

    flash("予約しました")

    mentor = Mentor.query.filter_by(mid=mid).first()
    schedule = Schedule.query.filter_by(sid=sid).first()

    if mentor.filename is None:
        mentor.filename = "default.jpg"

    data = {
        "date": schedule.date,
        "day": schedule.day,
        "place": schedule.place,
        "filename": 'static/img-get/' + mentor.filename,
        "name": mentor.name,
        "rid": rid
    }

    return render_template("reservation.html", data=data)


@app.route("/chat/<rid>", methods=["GET", "POST"])
def chat(rid):
    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました")
        return redirect(url_for('register'))

    reservation = Reservation.query.filter_by(rid=rid).first()

    mid = reservation.mentor_id

    schedule = Schedule.query.filter_by(sid=reservation.schedule_id).first()
    mentor = Mentor.query.filter_by(mid=mid).first()
    session['mentor_email'] = mentor.email
    if mentor.filename is None:
        mentor.filename = "default.jpg"

    data = {
        "date": schedule.date,
        "day": schedule.day,
        "place": schedule.place,
        "rid": reservation.rid,
        "name": mentor.name,
        "filename": 'static/img-get/' + mentor.filename
    }

    session['room'] = rid  # Set room as Reservation ID
    return render_template("chat.html", data=data)


@socketio.on('connect')
def test_connect():
    room = session.get('room')
    print(room + ' has connected')
    emit('connect')


@socketio.on('joined')
def on_join():
    print('!!JOINED!!')
    uid = session.get('uid')
    mid = session.get('mid')
    if uid is not None and mid is not None:
        print('ERROR: Both Mentor and Student logged in')
    cid = uid if uid is not None else mid
    room = session.get('room')
    join_room(room)
    if cid is None:
        raise socketio.ConnectionRefusedError('unauthorized')
    if room is None:
        raise socketio.ConnectionRefusedError('no rid specified')
    emit('join')


@socketio.on('loaded')
def load_messages(data):
    room = session['room']
    page = data.get('page')
    print("page: " + str(page))
    message_list = Chat.query.filter_by(reservation_id=room) \
        .order_by(Chat.created_at.desc()) \
        .paginate(page, 25, False).items
    messages = []
    for m in message_list:
        messages.append({
            'reservation_id': m.reservation_id,
            'is_mentor': m.is_mentor,
            'message': m.message,
            'created_at': m.created_at.isoformat()
        })
    emit('load', {'messages': messages})


@socketio.on('left')
def on_leave(data):
    room = session.pop('room', None)
    leave_room(room)
    emit('leave')


@socketio.on('messaged')
def message(data):
    room = session['room']
    is_mentor = True if session.get('mid') else False
    print("is_mentor: "+ ("true" if is_mentor else "false"))
    message = data['message']
    print("message: "+message)
    created_at = datetime.datetime.now()
    c = Chat(
        reservation_id=room,
        is_mentor=is_mentor,
        message=message,
        created_at=created_at,
    )
    db.session.add(c)
    db.session.commit()

    emit('message',{
        'message': {
            'reservation_id': c.reservation_id,
            'is_mentor': c.is_mentor,
            'message': c.message,
            'created_at': c.created_at.isoformat()
        }
    }, room=room)

    veri = True
    websiteurl = "https://preshot.app/register"
    email = ""
    sender = ""

    if c.is_mentor == True:
        email = session['student_email']
        # mid = session['mid']
        # mentor = Mentor.query.filter_by(mid=mid).first
        # if mentor.name == "":
        #     sender = mentor.email[:-1]
        # else:
        #     sender = mentor.name

        # chat = Chat.query.filter_by(reservation_id=room).order_by(Chat.created_at.desc()).first()
        # if chat.is_mentor == False:
        #     veri=True
        #     flash("就活生にEメールが送られました。")
    else:
        email = session['mentor_email']
        # sid = session["sid"]
        # student = Student.query.filter_by(sid=sid).first
        # sender = student.email[:-1]
        websiteurl = "https://preshot.app/mentor_register"
        # chat = Chat.query.filter_by(reservation_id=room).order_by(Chat.created_at.desc()).first()
        # if chat.is_mentor == True:
        #     veri=True
        #     flash("指導者にEメールが送られました。")

    #Multithread process
    if veri == True:
        with app.app_context():
            msg = Message('Preshotからの通知', recipients=[email])
            flash("メールが送られました。")
            msg.html = "チャットの返信が来ています。<br><br>"\
            "今すぐPreshotにログインして会話を開始しましょう！<br>{0}<br>（＊モバイル端末のみ対応）<br><br>"\
            "----------------------------<br>運営：team preshot<br>Email：preshot.info@gmail.com<br>HP：https://preshot.app/<br>----------------------------".format(websiteurl)
            thr = Thread(target=send_email_thread, args=[msg])
            thr.start()


@app.route("/chatlist", methods=["GET", "POST"])
def chatlist():
    # need to call the Schedule too
    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました")
        return redirect(url_for('register'))

    reservations = Reservation.query.filter_by(student_id=uid).all()
    chatlist = []
    filename = ""

    for reservation in reservations:
        schedule = Schedule.query.filter_by(sid=reservation.schedule_id).first()
        mentor = Mentor.query.filter_by(mid=reservation.mentor_id).first()
        if mentor is not None:
            if schedule is not None:
                if mentor.filename is None:
                    filename = "default.jpg"
                else:
                    filename = mentor.filename

                chat_history = {
                    "date": schedule.date,
                    "day": schedule.day,
                    "place": schedule.place,
                    "rid": reservation.rid,
                    "filename": 'static/img-get/' + filename,
                    "name": mentor.name,
                    "created_at": reservation.created_at
                }
                chatlist.append(chat_history)

    chatlist.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template("chatlist.html", chatlist=chatlist)


# ----------------------------------------------------------------
# Mentor API
# ----------------------------------------------------------------

@app.route("/mentor_register", methods=["GET", "POST"])
def mentor_register():
    if request.method == "POST":
        data = request.form

        if data["email"] is "":
            flash("メールアドレスを入力してください")
            return redirect(request.url)
        if data["password"] is "":
            flash("パスワードを入力してください")
            return redirect(request.url)

        mentor = Mentor.query.filter_by(email=data["email"]).first()

        if mentor is None:

            mid = str(uuid.uuid4())
            sid = str(uuid.uuid4())

            session['mid'] = mid
            session.pop('uid', None)

            mentor = Mentor(
                email=data["email"],
                mid=mid,
                password=hashlib.sha256((data["password"]+data["email"]).encode('utf-8')).hexdigest(),
                created_at=datetime.datetime.now()
            )

            schedule = Schedule(
                sid=sid,
                day="土曜日",
                date="18:00",
                place="オンライン",
                mentor_id=mid,
                created_at=datetime.datetime.now()
            )

            db.session.add(mentor)
            db.session.add(schedule)
            db.session.commit()
            flash("プロフィールを充実させましょう")
            return redirect(url_for('mentor_profile'))

        else:
            if mentor.password == hashlib.sha256((data["password"]+data["email"]).encode('utf-8')).hexdigest():
                session['mid'] = mentor.mid
                session.pop('uid', None)

                flash("ログインしました")
                return redirect(url_for('mentor_home'))

            else:
                # "password is wrong"
                flash("パスワードが違います")
                return redirect(request.url)

    return render_template("mentor_register.html")


@app.route("/mentor_profile", methods=["GET", "POST"])
def mentor_profile():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('mentor_register'))

    mentor = Mentor.query.filter_by(mid=mid).first()

    if request.method == "POST":
        filename = ""

        if request.form:

            data = request.form.to_dict()

            if request.files["image"]:
                image = request.files["image"]

                if image.filename == "":
                    flash("ファイル名を入力してください")
                    return redirect(request.url)

                if not allowed_image(image.filename):
                    flash("PNG, JPG, JPEGを選んでください")
                    return redirect(request.url)
                else:
                    filename = secure_filename(image.filename)
                    emp_file = Mentor.query.filter_by(filename=filename).first()
                    if emp_file:
                        flash("ファイル名が重複しています")
                        return redirect(request.url)

                    image.save(os.path.join(app.config["UPLOAD_FOLDER"], image.filename))

                    img = Image.open(os.path.join(app.config["UPLOAD_FOLDER"], image.filename))
                    img = crop_max_square(img)
                    img_resize_lanczos = img.resize((350, 350), Image.LANCZOS)
                    img_resize_lanczos.save(os.path.join(app.config["GET_FOLDER"], image.filename))

            if data["name"] == "":
                data["name"] = mentor.name

            if request.files["image"].filename == "":
                filename = mentor.filename

            if data["university"] == '':
                data["university"] = mentor.university

            if data["faculty"] == '':
                data["faculty"] = mentor.faculty

            if data["firm"] == "":
                data["firm"] = mentor.firm

            if data["history"] == "":
                data["history"] = mentor.history

            if data["graduation"] == '':
                data["graduation"] = mentor.graduation

            if data["position"] == '':
                data["position"] = mentor.position

            if data["comment"] == '':
                data["comment"] = mentor.comment

            mentor.name = data["name"]
            mentor.filename = filename
            mentor.university = data["university"]
            mentor.faculty = data["faculty"]
            mentor.firm = data["firm"]
            mentor.graduation = data["graduation"]
            mentor.position = data["position"]
            mentor.history = data["history"]
            mentor.comment = data["comment"]
            mentor.updated_at = datetime.datetime.now()
            db.session.commit()

            flash("プロフィールを更新しました")

            return redirect(request.url)

    if mentor.filename is None:
        mentor.filename = "default.jpg"

    data = {
        "name": mentor.name,
        "filename": 'static/img-get/' + mentor.filename,
        "university": mentor.university,
        "faculty": mentor.faculty,
        "firm": mentor.firm,
        "graduation": mentor.graduation,
        "position": mentor.position,
        "history": mentor.history,
        "comment": mentor.comment
    }

    return render_template("mentor_profile.html", data = data)


@app.route("/mentor_profile_view", methods=["GET", "POST"])
def mentor_profile_view():
    # need to call the Schedule too
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました")
        return redirect(url_for('mentor_register'))

    mentor = Mentor.query.filter_by(mid=mid).first()
    schedules = Schedule.query.filter_by(mentor_id=mid).filter_by(is_active=True).all()

    if mentor.filename is None:
        mentor.filename = "default.jpg"

    schedule_info = []

    for schedule in schedules:
        schedule_data = {
            "sid": schedule.sid,
            "day": schedule.day,
            "date": schedule.date,
            "place": schedule.place
        }
        schedule_info.append(schedule_data)

    mentor_data = {
        "mid": mentor.mid,
        "name": mentor.name,
        "filename": 'static/img-get/' + mentor.filename,
        "university": mentor.university,
        "faculty": mentor.faculty,
        "firm": mentor.firm,
        "position": mentor.position,
        "history": mentor.history,
        "schedule": schedule_info,
        "comment": mentor.comment,
        "graduation": mentor.graduation
    }

    return render_template("mentor_profile_view.html", mentor=mentor_data)

@app.route("/mentor_schedule", methods=["GET", "POST"])
def mentor_schedule():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('mentor_register'))

    schedules = Schedule.query.filter_by(mentor_id=mid).filter_by(is_active=True).all()

    response = []

    for schedule in schedules:
        schedule_data = {
            "sid": schedule.sid,
            "day": schedule.day,
            "date": schedule.date,
            "place": schedule.place
        }
        response.append(schedule_data)

    if request.method == "POST":
        data = request.form

        sid = str(uuid.uuid4())

        schedule = Schedule(
            sid=sid,
            day=data["day"],
            date=data["date"],
            place=data["place"],
            mentor_id=mid,
            created_at=datetime.datetime.now()
        )

        db.session.add(schedule)
        db.session.commit()

        flash("追加しました。")
        return redirect(request.url)

    return render_template("mentor_schedule.html", schedules=response)


@app.route("/mentor_schedule_delete/<sid>", methods=["GET", "POST"])
def mentor_schedule_delete(sid):
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('mentor_register'))

    schedule = Schedule.query.filter_by(sid=sid).first()
    schedule.is_active = False
    db.session.commit()

    flash("削除されました")

    return redirect(url_for('mentor_schedule'))


@app.route("/mentor_setting", methods=["GET", "POST"])
def mentor_setting():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました")
        return redirect(url_for('mentor_register'))

    mentor = Mentor.query.filter_by(mid=mid).first()

    if request.method == "DELETE":
        db.session.delete(mentor)
        db.session.commit()
        flash("削除されました")

        session["mid"] = ""

        response = make_response(jsonify(mentor, 200))
        return response

    return render_template("mentor_setting.html", data=mentor)


@app.route("/mentor_home", methods=["GET", "POST"])
def mentor_home():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました")
        return redirect(url_for('mentor_register'))

    page = request.args.get('page', 1, type=int)

    posts = Post.query.order_by(Post.created_at.desc()).paginate(page, 10, False)
    next_url = url_for('mentor_home', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('mentor_home', page=posts.prev_num) if posts.has_prev else None

    response = []
    posts = posts.items

    for post in posts:
        post_data = {
            "id":post.id,
            "pid": post.pid,
            "title": post.title[:18] + " ..",
            "text": post.text[:105] + "...",
            "created_at": post.created_at
        }
        response.append(post_data)

    return render_template("mentor_home.html", posts=response, next_url=next_url, prev_url=prev_url)


@app.route("/mentor_home/<pid>", methods=["GET", "POST"])
def mentor_home_pid(pid):
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました")
        return redirect(url_for('mentor_register'))

    post = Post.query.filter_by(pid=pid).first()
    response = Response.query.filter_by(post_id=pid).filter_by(mentor_id=mid).first()

    post_data = {
        "pid": post.pid,
        "title": post.title,
        "text": post.text,
        "response": response,
        "created_at": post.created_at
    }

    return render_template("mentor_home_pid.html", post=post_data)


@app.route("/mentor_response/<pid>", methods=["GET", "POST"])
def mentor_response(pid):
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました")
        return redirect(url_for('mentor_register'))

    response = Response.query.filter_by(post_id=pid).filter_by(mentor_id=mid).first()

    if response is None:

        response = Response(
            post_id=pid,
            mentor_id=mid,
            created_at=datetime.datetime.now()
        )

        db.session.add(response)
        db.session.commit()

        #userのIDが必要です。
        post = Post.query.filter_by(pid=pid).first()
        student = Student.query.filter_by(uid=post.student_id).first()
        mentor = Mentor.query.filter_by(mid=mid).first()
        
        if mentor.name is None:
            mentor.name = "指導者"

        #mentorの名前　ユーザーのemail
        msg = Message('{}さんから声をかけられました！'.format(mentor.name), recipients=[student.email])
        msg.html = "指導者からあなたの以下の投稿に対して声をかけられました。<br><br>"\
            "タイトル：{0}<br>本文：{1}<br><br>"\
            "今すぐPreshotにログインして指導の予約をしましょう！<br>https://preshot.app/register<br>(＊モバイル端末のみ対応)<br><br><br>"\
            "----------------------------<br>運営：team preshot<br>Email：preshot.info@gmail.com<br>HP：https://preshot.app/<br>----------------------------".format(post.title, post.text)
        #msg.html = msg_body + msg_invite + msg_info
        mail.send(msg)

        flash("就活生に声をかけました！")

    else:
        flash("すでに声をかけています")

    #flaskmailを呼ぶ


    return redirect(url_for('mentor_home'))


@app.route("/mentor_chat/<rid>", methods=["GET", "POST"])
def mentor_chat(rid):
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました")
        return redirect(url_for('mentor_register'))

    reservation = Reservation.query.filter_by(rid=rid).first()

    uid = reservation.student_id

    schedule = Schedule.query.filter_by(sid=reservation.schedule_id).first()
    student = Student.query.filter_by(uid=uid).first()
    if student is not None:
        session['student_email'] = student.email
        if schedule is not None:
            #name produce
            if student.email is not None:
                name = student.email.split("@")
                email = name[0][:-1]
                data = {
                    "date": schedule.date,
                    "day": schedule.day,
                    "place": schedule.place,
                    "rid": reservation.rid,
                    "name": email+"さん"
                }

    session['room'] = rid  # Set room as Reservation ID

    return render_template("mentor_chat.html", data=data)


@app.route("/mentor_chatlist", methods=["GET", "POST"])
def mentor_chatlist():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました")
        return redirect(url_for('mentor_register'))

    reservations = Reservation.query.filter_by(mentor_id=mid).all()
    chatlist = []

    for reservation in reservations:
        schedule = Schedule.query.filter_by(sid=reservation.schedule_id).first()
        student = Student.query.filter_by(uid=reservation.student_id).first()
        response = Response.query.filter_by(mentor_id = mid).first()
        email = ""
        if student is not None:
            if schedule is not None:
                #name produce
                if student.email is not None:
                    name = student.email.split("@")
                    email = name[0][:-1]

                chat_history = {
                    "date": schedule.date,
                    "day": schedule.day,
                    "place": schedule.place,
                    "rid": reservation.rid,
                    "name": email+"さん",
                    "created_at": reservation.created_at
                }

                chatlist.append(chat_history)

    chatlist.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template("mentor_chatlist.html", chatlist=chatlist)


# ----------------------------------------------------------------
# Delete or logout
# ----------------------------------------------------------------

@app.route('/logout')
def logout():
    session.pop('uid', None)
    return redirect(url_for('register'))


@app.route("/delete", methods=["GET", "DELETE"])
def delete():
    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました")
        return redirect(url_for('register'))

    student = Student.query.filter_by(uid=uid).first()
    db.session.delete(student)
    db.session.commit()

    session.pop('uid', None)

    flash("アカウントを削除しました")

    return redirect(url_for('register'))


@app.route("/mentor_delete", methods=["GET", "DELETE"])
def mentor_delete():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました")
        return redirect(url_for('mentor_register'))

    mentor = Mentor.query.filter_by(mid=mid).first()
    db.session.delete(mentor)
    db.session.commit()
    flash("アカウントを削除しました")

    session.pop('mid', None)

    return redirect(url_for('mentor_register'))



@app.route("/post_delete/<id>", methods=["GET", "DELETE"])
def post_delete(id):

    post = Post.query.filter_by(id=id).first()
    db.session.delete(post)
    db.session.commit()

    flash("投稿を削除しました")

    return redirect(url_for('register'))
