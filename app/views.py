import datetime
import os
import uuid

from PIL import Image
from flask import request, redirect, session, jsonify, render_template, make_response, url_for, abort, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

from app import app, socketio

UPLOAD_FOLDER = '/static/img'
GET_FOLDER = '/static/img-get'
PHYSICAL_ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS_PER_PAGE = 10

# app.config.from_object("config.DevelopmentConfig")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SECRET_KEY"] = "superSecret"
app.config["UPLOAD_FOLDER"] = PHYSICAL_ROOT + UPLOAD_FOLDER
app.config["GET_FOLDER"] = PHYSICAL_ROOT + GET_FOLDER
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ["PNG", "JPG", "JPEG"]

# see the img folder
# file_list = os.listdir( app.config['UPLOAD_FOLDER'] )

app.debug = True
db = SQLAlchemy(app)

# Define Models

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime())


class Mentor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mid = db.Column(db.String(80), nullable=False, unique=True)
    name = db.Column(db.String(80), unique=True)
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
    date = db.Column(db.String(80), nullable=False) #think it as time
    place = db.Column(db.String(80), nullable=False)
    mentor_id = db.Column(db.String(80), nullable=False)
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


# ----------------------------------------------------------------
# db.drop_all()
# db.create_all()
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


# ----------------------------------------------------------------
# Student API
# ----------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/test", methods=["GET"])
def test():
    mentors = Mentor.query.all()

    return render_template("test.html", mentors=mentors)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form

        student = Student.query.filter_by(email=data["email"]).first()

        if student is None:

            uid = str(uuid.uuid4())
            session['uid'] = uid

            newuser = Student(
                email=data["email"],
                uid=uid,
                password=data["password"],
                created_at=datetime.datetime.now()
            )

            db.session.add(newuser)
            db.session.commit()
            flash("Created")
            return redirect(url_for('setting'))

        else:
            if student.password == data["password"]:
                session['uid'] = student.uid

                flash("Logged in")
                return redirect(url_for('mypost'))

            else:
                # "password is wrong"
                flash("Wrong password")
                return redirect(request.url)

    return render_template("register.html")


@app.route("/setting", methods=["GET", "DELETE"])
def setting():
    uid = session.get('uid')
    if uid is None:
        flash("Session is no longer available")
        return redirect(url_for('register'))

    student = Student.query.filter_by(uid=uid).first()

    return render_template("setting.html", data=student)


@app.route('/mypost', methods=["GET"])
def mypost():
    uid = session.get('uid')
    if uid is None:
        flash("Session is no longer available")
        return redirect(url_for('register'))

    try:
        posts = Post.query.filter_by(student_id=uid).all()

        response = []

        for post in posts:
            post_data = {
                "pid": post.pid,
                "title": post.title,
                "text": post.text,
                "created_at": post.created_at
            }
            response.append(post_data)

    except FileNotFoundError:
        abort(404)

    return render_template("mypost.html", posts=response)


@app.route("/mypost/<pid>", methods=["GET"])
def eachpost(pid):
    uid = session.get('uid')
    if uid is None:
        flash("Session is no longer available")
        return redirect(url_for('register'))

    post = Post.query.filter_by(pid=pid).first()
    responses = Response.query.filter_by(post_id=pid).all()

    mentor_info = []

    for response in responses:
        mentor = Mentor.query.filter_by(mid=response.mentor_id).first()
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
        flash("Session is no longer available")
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
            flash("Posted")

            return redirect(url_for('mypost'))

    return render_template("post.html")


@app.route("/select_mentor/<mid>", methods=["GET", "POST"])
def select_mentor(mid):
    # need to call the Schedule too
    uid = session.get('uid')
    if uid is None:
        flash("Session is no longer available")
        return redirect(url_for('register'))

    # Need it for making reservation post
    session['mentor_id'] = mid

    mentor = Mentor.query.filter_by(mid=mid).first()
    schedules = Schedule.query.filter_by(mentor_id=mid).all()

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

    if uid is None or mid is None:
        return redirect(url_for('register'))

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

    flash("登録しました")

    # return redirect(url_for('mypost'))

    mentor = Mentor.query.filter_by(mid=mid).first()
    schedule = Schedule.query.filter_by(sid=sid).first()

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
        flash("Session is no longer available")
        return redirect(url_for('register'))

    #TASK for you
    #if the message is being posted this catches and post
    if request.method == "POST":
        data = request.form

        is_mentor = False

        chat = Chat(
            reservation_id=rid,
            is_mentor=is_mentor,
            message=data["text"],
            created_at=datetime.datetime.now()
        )

        db.session.add(chat)
        db.session.commit()

        return redirect(request.url)

    page = request.args.get('page', 1, type=int)
    reservation = Reservation.query.filter_by(rid=rid).first()
    c = Chat.query.filter_by(reservation_id=rid)\
        .order_by(Chat.created_at.desc())\
        .paginate(page, 25, False)

    #loop to divide the messages grouped by if its is_mentor is false or not
    messages = c.items

    mid = reservation.mentor_id

    schedule = Schedule.query.filter_by(sid=reservation.schedule_id).first()
    mentor = Mentor.query.filter_by(mid=mid).first()

    data = {
            "date": schedule.date,
            "day": schedule.day,
            "place": schedule.place,
            "rid": reservation.rid,
            "mentor_name": mentor.name,
            "messages": messages
        }


    if page is not None: # If ?page=<int>, send data as JSON instead
        print('TODO')
        #TODO: need to implement the JSON rendering

    return render_template("chat.html", data = data)


@socketio.on('message')


@app.route("/chatlist", methods=["GET", "POST"])
def chatlist():
    # need to call the Schedule too
    uid = session.get('uid')
    if uid is None:
        flash("Session is no longer available")
        return redirect(url_for('register'))

    reservations = Reservation.query.filter_by(student_id=uid).all()

    chatlist = []

    for reservation in reservations:
        schedule = Schedule.query.filter_by(sid=reservation.schedule_id).first()
        mentor = Mentor.query.filter_by(mid=reservation.mentor_id).first()

        chat_history = {
            "date": schedule.date,
            "day": schedule.day,
            "place": schedule.place,
            "rid": reservation.rid,
            "filename": 'static/img-get/' + mentor.filename,
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

        mentor = Mentor.query.filter_by(email=data["email"]).first()

        if mentor is None:

            mid = str(uuid.uuid4())
            sid = str(uuid.uuid4())

            session['mid'] = mid

            mentor = Mentor(
                email=data["email"],
                mid=mid,
                password=data["password"],
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
            flash("登録しました")
            return redirect(url_for('mentor_profile'))

        else:
            if mentor.password == data["password"]:
                session['mid'] = mentor.mid

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
        return redirect(url_for('register'))

    if request.method == "POST":
        filename = ""

        if request.form:

            data = request.form.to_dict()

            if request.files["image"]:
                image = request.files["image"]

                if image.filename == "":
                    flash("Image must have a name")
                    return redirect(request.url)

                if not allowed_image(image.filename):
                    flash("PNG, JPG, JPEGを選んでください")
                    return redirect(request.url)
                else:
                    filename = secure_filename(image.filename)
                    emp_file = Mentor.query.filter_by(filename=filename).first()
                    if emp_file:
                        flash("ファイル名を変更してください")
                        return redirect(request.url)

                    image.save(os.path.join(app.config["UPLOAD_FOLDER"], image.filename))

                    img = Image.open(os.path.join(app.config["UPLOAD_FOLDER"], image.filename))
                    img = crop_max_square(img)
                    img_resize_lanczos = img.resize((350, 350), Image.LANCZOS)
                    img_resize_lanczos.save(os.path.join(app.config["GET_FOLDER"], image.filename))

            mentor = Mentor.query.filter_by(mid=mid).first()

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

            flash("プロフィールを更新されました")

            return redirect(url_for('mentor_home'))

    return render_template("mentor_profile.html")


@app.route("/mentor_schedule", methods=["GET", "POST"])
def mentor_schedule():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    schedules = Schedule.query.filter_by(mentor_id=mid).all()

    response = []

    for schedule in schedules:
        schedule_data = {}
        schedule_data["sid"] = schedule.sid
        schedule_data["day"] = schedule.day
        schedule_data["date"] = schedule.date
        schedule_data["place"] = schedule.place
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


@app.route("/mentor_schedule_delete/<sid>", methods=["GET", "DELETE"])
def mentor_schedule_delete(sid):
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    schedule = Schedule.query.filter_by(sid=sid).first()
    db.session.delete(schedule)
    db.session.commit()

    flash("deleted")

    return redirect(url_for('mentor_schedule'))


@app.route("/mentor_setting", methods=["GET", "POST"])
def mentor_setting():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    mentor = Mentor.query.filter_by(mid=mid).first()

    if request.method == "DELETE":
        db.session.delete(mentor)
        db.session.commit()
        flash("削除されました。")

        session["mid"] = ""

        response = make_response(jsonify(mentor, 200))
        return response

    return render_template("mentor_setting.html", data=mentor)


@app.route("/mentor_home", methods=["GET", "POST"])
def mentor_home():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    page = request.args.get('page', 1, type=int)

    posts = Post.query.paginate(page, 10, False)
    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None

    response = []
    posts = posts.items

    for post in posts:
        post_data = {
            "pid": post.pid,
            "title": post.title,
            "text": post.text,
            "created_at": post.created_at
        }
        response.append(post_data)

    return render_template("mentor_home.html", posts=response, next_url=next_url, prev_url=prev_url)


@app.route("/mentor_home/<pid>", methods=["GET", "POST"])
def mentor_home_pid(pid):
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    post = Post.query.filter_by(pid=pid).first()
    response = Response.query.filter_by(post_id=pid).all()

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
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    response = Response.query.filter_by(post_id=pid).filter_by(mentor_id=mid).first()

    if response is None:

        response = Response(
            post_id=pid,
            mentor_id=mid,
            created_at=datetime.datetime.now()
        )

        db.session.add(response)
        db.session.commit()

        flash("追加しました。")

    else:
        flash("U already reacted")

    return redirect(url_for('mentor_home'))


@app.route("/mentor_chat/<rid>", methods=["GET", "POST"])
def mentor_chat(rid):
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    return render_template("mentor_chat.html")


@app.route("/mentor_chatlist", methods=["GET", "POST"])
def mentor_chatlist():
    return render_template("mentor_chatlist.html")


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
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    student = Student.query.filter_by(uid=uid).first()
    db.session.delete(student)
    db.session.commit()

    session.pop('uid', None)

    flash("deleted")

    return redirect(url_for('register'))


@app.route("/mentor_delete", methods=["GET", "DELETE"])
def mentor_delete():
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    mentor = Mentor.query.filter_by(mid=mid).first()
    db.session.delete(mentor)
    db.session.commit()
    flash("deleted")

    session.pop('mid', None)

    return redirect(url_for('mentor_register'))