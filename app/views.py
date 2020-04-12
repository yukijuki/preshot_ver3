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
    name = db.Column(db.String(80), nullable=False)
    filename = db.Column(db.String(255), nullable=False, unique=True, default="default.jpg")
    university = db.Column(db.String(80), nullable=False)
    faculty = db.Column(db.String(80), nullable=False)
    firm = db.Column(db.String(80), nullable=False)
    position = db.Column(db.String(80), nullable=False)
    graduation = db.Column(db.Integer, default=0, nullable=False)
    comment = db.Column(db.String(255), nullable=False)
    schedules = db.relationship('Schedule', backref='mentor', lazy=True) #one to many relationship
    # reservations = db.relationship('Reservation', backref='student', lazy=True) #one to many relationship
    created_at = db.Column(db.DateTime())
    updated_at = db.Column(db.DateTime())

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(80), nullable=False)
    place = db.Column(db.String(80), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    created_at = db.Column(db.DateTime())
    updated_at = db.Column(db.DateTime())

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    # mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    mentor_id = db.Column(db.Integer, nullable=False) #gotta change it to one to one relationship
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    day = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime())
    place = db.Column(db.String(80), nullable=False)
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
#Routes

@app.route("/")
def index():
    return render_template("register.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form
        if data["email"] == "":
            print("email absent")
            return redirect(url_for('register'))

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
            return redirect(url_for('profile', uid=uid))
        
        else:
            if student.password == data["password"]:
                session['uid'] = student.uid

                flash("ログインしました")
                return redirect(url_for('home', uid=student.uid))

            else:  
                #"password is wrong"
                flash("パスワードが違います")
                return redirect(request.url)
    return render_template("register.html")

@app.route("/profile/<uid>", methods=["GET", "DELETE"])
def profile(uid):

    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    student = Student.query.filter_by(uid=uid).first()

    if  request.method == "DELETE":
        db.session.delete(student)
        db.session.commit()
        flash("削除されました。")

        session["uid"] = ""

        response = make_response(jsonify(data, 200))
        return response

    return render_template("profile.html", data = student)

@app.route('/home/<uid>', methods=["GET"])
def home(uid):

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

    return render_template("home.html", posts = response)

@app.route("/mypost/<post_id>", methods=["GET"])
def mypost(post_id):

    uid = session.get('uid')
    if uid is None:
        flash("セッションが切れました。")
        return redirect(url_for('register'))

    try:        
        post = Post.query.filter_by(post_id=post_id).first()
        
        post_data = {}
        post_data["id"] = post.id
        post_data["title"] = post.title
        post_data["text"] = post.text
        post_data["response"] = post.response
        post_data["created_at"] = post.created_at
        
    except FileNotFoundError:
        abort(404)
        flash("バグを運営に報告してください")

    return render_template('mypost.html', post=post_data)



@app.route("/upload", methods=["GET", "POST"])
def upload():

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
                emp_file = Employee.query.filter_by(filename=filename).first()
                if emp_file:
                    flash("ファイル名を変更してください")
                    return redirect(request.url)

                image.save(os.path.join(app.config["UPLOAD_FOLDER"], image.filename))

                img = Image.open(os.path.join(app.config["UPLOAD_FOLDER"], image.filename))
                img = crop_max_square(img)
                img_resize_lanczos = img.resize((350, 350), Image.LANCZOS)
                img_resize_lanczos.save(os.path.join(app.config["GET_FOLDER"], image.filename))
                print(filename)

                employee = Employee(
                name = data["name"],
                filename = filename,
                link = data["link"],
                faculty = data["faculty"],
                firm = data["firm"],
                industry = data["industry"],
                position = data["position"],
                lab = data["lab"],
                club = data["club"],
                ask_clicks = 0
                )

                db.session.add(employee)
                db.session.commit()
                flash("Image saved")

            return redirect(request.url)
    return render_template("upload.html")


@app.route('/logout')
def logout():
    session.pop('uid', None)
    return redirect(url_for('register'))

@app.route("/delete/<id>", methods=['POST', "GET", "DELETE"])
def employee_delete(id):
    email = session.get('Email')
    if email == "admin@gmail.com":
        print(email)
    else:
        flash("adminに入ってください")
        return redirect(url_for('register'))

    b = Employee.query.filter_by(id=id).first()
    db.session.delete(b)
    db.session.commit()
    flash("deleted")

    return render_template("admin.html")