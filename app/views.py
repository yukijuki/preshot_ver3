from app import app
from flask import Flask, request, redirect, session, send_from_directory, jsonify, render_template, make_response, url_for, abort, flash
from flask_sqlalchemy import SQLAlchemy
import datetime, os, secrets
from werkzeug.utils import secure_filename
from PIL import Image
import uuid 

UPLOAD_FOLDER = '/static/img'
GET_FOLDER = '/static/img-get'
PHISICAL_ROOT = os.path.dirname( os.path.abspath( __file__ ) )

# app.config.from_object("config.DevelopmentConfig")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SECRET_KEY"] = "superSecret"
app.config["UPLOAD_FOLDER"] = PHISICAL_ROOT + UPLOAD_FOLDER
app.config["GET_FOLDER"] = PHISICAL_ROOT + GET_FOLDER
app.config["ALLOWED_IMAGE_EXTENSIONS"] = ["PNG", "JPG", "JPEG"]

#see the img folder
#file_list = os.listdir( app.config['UPLOAD_FOLDER'] )

app.debug = True
db = SQLAlchemy(app)
# Define Models

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.Integer, default=0)
    posts = db.relationship('Post', backref='student', lazy=True) #one to many relationship
    reservations = db.relationship('Reservation', backref='student', lazy=True) #one to many relationship
    created_at = db.Column(db.DateTime())
    updated_at = db.Column(db.DateTime())

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
    position = db.Column(db.String(80))
    graduation = db.Column(db.Integer)
    comment = db.Column(db.String(255))
    schedules = db.relationship('Schedule', backref='mentor', lazy=True) #one to many relationship
    # reservations = db.relationship('Reservation', backref='student', lazy=True) #one to many relationship
    created_at = db.Column(db.DateTime())
    updated_at = db.Column(db.DateTime())

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sid = db.Column(db.String(80), nullable=False, unique=True)
    day = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(80), nullable=False)
    place = db.Column(db.String(80), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    created_at = db.Column(db.DateTime())
    updated_at = db.Column(db.DateTime())

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.String(80), nullable=False, unique=True)
    title = db.Column(db.String(80), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    response = db.relationship('Response', backref='post', lazy=True) #one to many relationship
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    created_at = db.Column(db.DateTime())
    updated_at = db.Column(db.DateTime())

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, nullable=False) #gotta change it to one to one relationship
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime())
    updated_at = db.Column(db.DateTime())

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rid = db.Column(db.String(80), nullable=False, unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    schedule_id = db.Column(db.String(80), nullable=False, unique=True)
    post_id = db.Column(db.String(80), nullable=False, unique=True)
    created_at = db.Column(db.DateTime())
    updated_at = db.Column(db.DateTime())

#----------------------------------------------------------------
#db.drop_all()
#db.create_all()
#----------------------------------------------------------------
#Functions for images

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

#----------------------------------------------------------------
#Student API
#----------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form

        """
        data = {
            "email":"Str",
            "password" = 6,
        }
        """

        student = Student.query.filter_by(email=data["email"]).first()

        if student is None:

            uid = str(uuid.uuid4())
            session['uid'] = uid

            newuser = Student(
            email = data["email"], 
            uid = uid,
            password = data["password"], 
            created_at=datetime.datetime.now()
            )

            db.session.add(newuser)
            db.session.commit()
            
            flash("登録しました")
            return redirect(url_for('setting'))
        
        else:
            if student.password == data["password"]:
                session['uid'] = student.uid

                flash("ログインしました")
                return redirect(url_for('mypost'))

            else:  
                #"password is wrong"
                flash("パスワードが違います")
                return redirect(request.url)

    return render_template("register.html")

@app.route("/setting", methods=["GET", "DELETE"])
def setting():

    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    student = Student.query.filter_by(uid=uid).first()

    if request.method == "DELETE":
        print("here")
        db.session.delete(student)
        db.session.commit()
        flash("削除されました。")

        session["uid"] = ""

        response = make_response(jsonify(data, 200))
        return response

    return render_template("setting.html", data = student)

@app.route('/mypost', methods=["GET"])
def mypost():

    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))
    
    try:        
        posts = Post.query.filter_by(student_id=uid).all()

        response = []

        for post in posts:
            post_data = {}
            post_data["id"] = post.id
            post_data["title"] = post.title
            post_data["text"] = post.text
            post_data["created_at"] = post.created_at
            response.append(post_data)

    except FileNotFoundError:
        abort(404)

    return render_template("mypost.html", posts = response)

@app.route("/mypost/<pid>", methods=["GET"])
def eachpost(pid):

    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    try:        
        post = Post.query.filter_by(id=pid).first()
        response = Response.query.filter_by(post_id=pid).all()
        
        post_data = {}
        post_data["id"] = post.id
        post_data["title"] = post.title
        post_data["text"] = post.text
        post_data["response"] = response
        post_data["created_at"] = post.created_at
        
    except FileNotFoundError:
        abort(404)
        flash("バグを運営に報告してください")

    return render_template('eachpost.html', post=post_data)

@app.route("/post", methods=["POST"])
def post():

    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    if request.method == "POST":
        if request.form:
            data = request.form

            pid = str(uuid.uuid4())

            post = Post(
            title = data["title"],
            pid = pid,
            text = data["text"],
            student_id = uid,
            created_at=datetime.datetime.now()
            )

            db.session.add(post)
            db.session.commit()
            flash("投稿されました。")

            return redirect(url_for('mypost'))

    return render_template("post.html")

@app.route("/select_mentor/<mid>", methods=["GET", "POST"])
def select_mentor(mid):
    
    # need to call the Schedule too
    mentor = Mentor.query.filter_by(mid=mid).first()
    


    return render_template("select_mentor.html", data = mentor)

@app.route("/reservation/<sid>", methods=["GET", "POST"])
def reservation(sid):
    return render_template("reservation.html")



#----------------------------------------------------------------
#Mentor API
#----------------------------------------------------------------

@app.route("/mentor_register", methods=["GET", "POST"])
def mentor_register():

    if request.method == "POST":
        data = request.form

        mentor = Mentor.query.filter_by(email=data["email"]).first()

        if mentor is None:

            mid = str(uuid.uuid4())
            session['mid'] = mid

            mentor = Mentor(
            email = data["email"], 
            mid = mid,
            password = data["password"], 
            created_at=datetime.datetime.now()
            )
            db.session.add(mentor)
            db.session.commit()
            flash("登録しました")
            return redirect(url_for('mentor_profile'))
        
        else:
            if mentor.password == data["password"]:
                print(mentor.mid)
                session['mid'] = mentor.mid

                flash("ログインしました")
                return redirect(url_for('mentor_profile'))

            else:  
                #"password is wrong"
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
        if request.form:

            data = request.form
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
                
                if filename == "":
                    filename = mentor.filename

                if data["university"] == '':
                    data["university"] = mentor.university

                if data["faculty"] == '':
                    data["faculty"] = mentor.faculty
                
                if data["firm"] == "":
                    data["firm"] = mentor.firm

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
                mentor.comment = data["comment"]
                mentor.updated_at = datetime.datetime.now()
                db.session.commit()

                flash("プロフィールを更新されました")

                return redirect(request.url)
    return render_template("mentor_profile.html")

@app.route("/mentor_schedule", methods=["GET", "POST"])
def mentor_schedule():

    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))
    
    if request.method == "POST":
        data = request.form

        schedule = Schedule(
        day = data["day"], 
        date = data["date"],
        place = data["place"], 
        mentor_id = mid,
        created_at = datetime.datetime.now()
        )

        db.session.add(mentor)
        db.session.commit()

        flash("追加しました。")
        return redirect(url_for('mentor_profile'))
        
    return render_template("mentor_schedule.html")

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

        response = make_response(jsonify(data, 200))
        return response


    return render_template("mentor_setting.html", data = mentor)

@app.route("/mentor_home", methods=["GET", "POST"])
def mentor_home():

    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))
    
    posts = Post.query.all()

    response = []

    for post in posts:
        post_data = {}
        post_data["id"] = post.pid
        post_data["title"] = post.title
        post_data["text"] = post.text
        post_data["created_at"] = post.created_at
        response.append(post_data)    

    return render_template("mentor_home.html", posts = response)

@app.route("/mentor_home/<pid>", methods=["GET", "POST"])
def mentor_home_pid(pid):

    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))
    
    post = Post.query.filter_by(pid=pid).first()
    response = Response.query.filter_by(post_id=pid).all()
        
    post_data = {}
    post_data["id"] = post.pid
    post_data["title"] = post.title
    post_data["text"] = post.text
    post_data["response"] = response
    post_data["created_at"] = post.created_at

    return render_template("mentor_home_pid.html", post = post_data)

@app.route("/mentor_response/<pid>", methods=["GET", "POST"])
def mentor_response(pid):

    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    response = Response.query.filter_by(post_id = pid).filter_by(mentor_id = mid).first()
    
    if response is None:
        response = Response(
        post_id = pid,
        mentor_id = mid,
        created_at = datetime.datetime.now()
        )

        db.session.add(response)
        db.session.commit()

        flash("追加しました。")

    else:
        flash("U already reacted")

    return redirect(url_for('mentor_home'))


#----------------------------------------------------------------
#For both
#----------------------------------------------------------------

@app.route('/logout')
def logout():
    session.pop('uid', None)
    return redirect(url_for('register'))

@app.route("/delete", methods=['POST', "GET", "DELETE"])
def delete():
    mid = session.get('mid')
    mid = session.get('mid')
    if mid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    mentor = Mentor.query.filter_by(id=id).first()
    db.session.delete(mentor)
    db.session.commit()
    flash("deleted")

    return redirect(url_for('mentor_home'))

