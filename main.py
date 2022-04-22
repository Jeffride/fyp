import imp
from flask import render_template
from flask_login import login_required
from flask import Flask,render_template,request,url_for
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import LoginManager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegistrationForm,LoginForm
from flask import redirect
from flask_mysqldb import MySQL
from  flask_login import LoginManager, login_user, logout_user
from flask import flash
import pandas as pd
from predictions import personalised_ranking, predict_missing_pairscores, selectedMovies

login_manager = LoginManager()

SECRET_KEY = os.urandom(32)



#SETTING UP SQLALCHEMY CONNECTION
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydb.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#SETTING UP MYSQL DB CONNECTION
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'xmasbarnicleant;l0ps'
app.config['MYSQL_DB'] = 'ai'

 
mysql = MySQL(app)

login_manager.init_app(app)

class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(50), index=True, unique=True)
  password_hash = db.Column(db.String(150))
  joined_at = db.Column(db.DateTime(), default = datetime.utcnow, index = True)

  def set_password(self, password):
        self.password_hash = generate_password_hash(password)

  def check_password(self,password):
      return check_password_hash(self.password_hash,password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route("/")
def index():
    cursor = mysql.connection.cursor()
    #FLUSH THE USER CURRENT CHOICES TABLE ON WEB APP START UP
    cursor.execute('''DROP TABLE IF EXISTS ai.movie_choices''')
    mysql.connection.commit()
    cursor.close()

    cursor = mysql.connection.cursor()
    cursor.execute('''CREATE TABLE ai.movie_choices(userId int,movie_id1 int,movie_id2 int,choice int)''')
    mysql.connection.commit()
    cursor.close()

    return render_template("index.html")

@app.route("/main", methods = ['POST','GET'])
@login_required
def main():
    if request.method == 'GET':
        #GENERATES TWO MOVIE IMAGE IDS
        cursor = mysql.connection.cursor()
        cursor.execute('''
         SELECT imdbId,movieId FROM ai.train_set ORDER BY RAND() LIMIT 2  ''')
        mysql.connection.commit()
        result = cursor.fetchall()
        cursor.close()

        m1 = str(result[0][1])
        i1 = str(result[0][0])
        
        m2 = str(result[1][1])
        i2 = str(result[1][0])

        return render_template("main.html",m1=i1,m2=i2,m1id=m1,m2id=m2)
    if request.method == 'POST':
        
        movie_id1 = request.form['movieid1']
        movie_id2 = request.form['movieid2']
        choice = request.form['choice']
        cursor = mysql.connection.cursor()
        cursor.execute('''INSERT INTO ai.movie_choices VALUES(%s,%s,%s,%s)''',('1',movie_id1,movie_id2,choice))
        mysql.connection.commit()
        cursor.close()
        return redirect('/main')

@app.route("/cineplex")
@login_required
def predictions():

    #USER PROFILE
    cursor = mysql.connection.cursor()
    cursor.execute('''
    SELECT * FROM ai.movie_choices''')
    mysql.connection.commit()
    df = pd.DataFrame(cursor.fetchall())
    #TEST SET
    test = pd.read_csv('./datasets/test_set.csv')
    #TRAIN SET
    pairwise_data = pd.read_csv('./datasets/train_set.csv')

    rs = predict_missing_pairscores(df,test,pairwise_data)
    
    #get selected preferences and add them to ranking table
    cursor = mysql.connection.cursor()
    cursor.execute('''
    SELECT * from ai.movie_choices''')
    mysql.connection.commit()

    return render_template("cineplex.html",r = rs[0])

@app.route("/ranking")
@login_required
def ranking():
    cursor = mysql.connection.cursor()
    cursor.execute('''
    SELECT * FROM ai.movie_choices''')
    mysql.connection.commit()
    df = pd.DataFrame(cursor.fetchall())
    movs = selectedMovies(df.values)

    #TRAIN SET
    trainset = pd.read_csv('./datasets/train_set.csv')
    r = personalised_ranking(df, movs, trainset)
    return render_template("predictions.html",rank = r)
    
#LOGIN & REGISTRATION
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username = form.username.data).first()
        if user is not None and user.check_password(form.password.data):
            login_user(user)
            next = request.args.get("next")
            return redirect(next or url_for('main'))
        flash('Invalid username or Password.')    
    return render_template('login.html', form=form)

@app.route('/register', methods = ['POST','GET'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username =form.username.data)
        username = form.username.data
        #CHECKING IF USER ALREADY EXISTS 
        cursor = mysql.connection.cursor()
        cursor.execute('''
        select *  from pythonlogin.accounts 
        where username = '%s'
        '''%(username))
        mysql.connection.commit()
        if cursor.fetchone() == '':
            user.set_password(form.password1.data)
            db.session.add(user)
            db.session.commit()
        else:
            flash('User already exists')
            return render_template('register.html',msg = 'user already exists',form=form)
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))

#This diplays the 404 not found page
@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404
