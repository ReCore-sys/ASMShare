"""
READ ME YOU FOOL

Ok so here is where you will learn how to help me with this. This will assume 0 prior knowledge of how to code a website or how to use python.

We are using a nice bit of code called Flask to make our site. It runs on python (My language of choice) to make websites. Pretty much, it gets .html files and displays them. It also does a load of other funky stuff, but we will deal with that later.

So just some simple stuff first.
Anything in a line with a hash (#) is a comment. It does not affect the code in any way and is just used for explaining stuff.
Anything inside 3 quotation marks (Like this big lump of text) is also a comment. This is called a multi-line comment.
Nice and easy.

Now, that only matters for python files (a file ending in .py).
There are going to be 3 other types of files we will mostly be dealing with.
In .html files, a comment is anything inside a <!-- comment -->. These can be over multiple lines.
In .css files a comment can be created with /* comment */. Again, multiple lines are fine.
.js comments can either be // (Single line) or /* comment */ (Multi line)






"""
# //////////////////////////////////////////////////////////////////////////// #

# IMPORT EVERYTHING

# //////////////////////////////////////////////////////////////////////////// #

import getpass
import json
import os
import random
import sqlite3
import sys
import threading
import time
import urllib
from base64 import b64decode, b64encode
from http.server import HTTPServer, SimpleHTTPRequestHandler
from secrets import *

import flask
import requests
from db import init_db_command
from flask import *
from flask_htmlmin import HTMLMIN
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from loguru import logger as log
from oauthlib.oauth2 import WebApplicationClient
from user import User
from werkzeug.utils import secure_filename

# //////////////////////////////////////////////////////////////////////////// #

# IMPORT EVERYTHING

# //////////////////////////////////////////////////////////////////////////// #
# this gets the directory this script is in. Makes it much easier to transfer between systems.
filepath = os.path.abspath(os.path.dirname(__file__))


def startserve():
    httpd = HTTPServer(('localhost', 5001), SimpleHTTPRequestHandler)
    httpd.serve_forever()


"""
Ok cos chrome hates everyone, for some god forsaken reason you can't call an image from a local file system. It's shit I know.
My solution: Host a very basic HTTP server on the same address in a different thread and pull the images from there. Somehow that works
"""

some_thread = threading.Thread(target=startserve)
some_thread.start()

# //////////////////////////////////////////////////////////////////////////// #

# Flask config

# //////////////////////////////////////////////////////////////////////////// #


app = Flask(__name__)
app.config['MINIFY_HTML'] = True
app.config['UPLOAD_PATH'] = f"{filepath}/files/"
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

htmlmin = HTMLMIN(app)

login_manager = LoginManager()
login_manager.init_app(app)
# login_manager.login_view = 'login'
client = WebApplicationClient(GOOGLE_CLIENT_ID)
app.secret_key = appkey

# //////////////////////////////////////////////////////////////////////////// #

# SQL config

# //////////////////////////////////////////////////////////////////////////// #

try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass


db = sqlite3.connect("database.db")
cursor = db.cursor()

try:
    cursor.execute("CREATE TABLE filemapping (name TEXT, shortdesc TEXT, longdesc TEXT, uploader TEXT, subject TEXT, tags TEXT, time TIME);")
except:
    pass
db.commit()
db.close()

# //////////////////////////////////////////////////////////////////////////// #

# Varibles definition

# //////////////////////////////////////////////////////////////////////////// #

# region 404 errors
fourohfour = ["Welp. This is awkward",
              "Nice One",
              "This isn't great. In the meantime, drink some water",
              "THIS ERROR PAGE IS SPONSERED BY RAID SHADOW LEGENDS, ONE OF THE BIGGEST MOBILE ROLE PLAYING GAMES OF 2019 AND IT'S TOTALLY FREE!",
              "Real smooth",
              "Honestly, the home depot song is a banger",
              "Does anyone even read these?",
              "This isn't ideal",
              "So either you or I messed up and as the dude who made this thing, it's probably you",
              "Did you ever hear the story of Darth Plaguis the wise?",
              "Whoops",
              "What the gosh diddly darn heck did you do?",
              "Oopsy daises",
              "Get 404'd",
              "Ya done messed up",
              "GET OUT MY ROOM I'M PLAYING MINECRAFT",
              "Server hamster needs more vodka"
              ]

random.shuffle(fourohfour)


c = 0

# //////////////////////////////////////////////////////////////////////////// #

# Errors

# //////////////////////////////////////////////////////////////////////////// #


def notfoundmessage():
    global c
    message = fourohfour[c]
    c += 1
    if c == len(fourohfour):
        c = 0
    return message


@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html', message=notfoundmessage()), 404


@app.errorhandler(403)
def fourohthree(e):
    return render_template('errors/403.html'), 403


@app.route("/403")
def fourohthreepage():
    return render_template('errors/403.html')


@app.errorhandler(406)
def fourohsix(e):
    return render_template('errors/406.html'), 406


@app.route("/406")
def fourohsixpage():
    return render_template('errors/406.html')


@app.errorhandler(500)
def fivehundred(e):
    return render_template('errors/500.html'), 500


@app.route("/500")
def fivehundredpage():
    return render_template('errors/500.html')


@app.route("/553")
def fivethreethreepage():
    return render_template('errors/553.html')


@app.errorhandler(408)
def fouroheight(e):
    return render_template('errors/408.html'), 408


@app.route("/408")
def fouroheightpage():
    return render_template('errors/408.html')


@app.errorhandler(400)
def fourhundred(e):
    return render_template('errors/400.html'), 400


@app.route("/400")
def fourhundredpage():
    return render_template('errors/400.html')

# //////////////////////////////////////////////////////////////////////////// #

# End errors

# //////////////////////////////////////////////////////////////////////////// #


def shred(d, n=2):
    """Custom function to split a dict into a list of dicts

     Parameters
     ----------
     d : dict
     The dictionary to split

     n : int
     How many dictionaries per chunk in the list

     Returns
     -------
     y: list
     The list cut into parts with n length

     Examples
     --------
     >>> shred({key1: result1, key2: result2, key3: result3, key4: result4}, 2)
     > [{key1: result1, key2: result2}, {key3: result3, key4: result4}]"""
    c = 0
    y = []
    g = {}
    for x in d:
        g[x] = d[x]
        c = c + 1
        if c == n:
            y.append(g)
            g = {}
            c = 0
    if g != {}:
        y.append(g)
    return y


imgfolder = r"""http://127.0.0.1:5001/static/file-images/"""

cards = {
    "example1": {"short": "short demo", "long": "A really long description that goes super in depth into what the assignment was on", "grade": "A+", "subject": "Demonstration", "image": f"{imgfolder}/img1.jpg"},
    "example2": {"short": "demo", "long": "long description of the demo", "grade": "B-", "subject": "Demonstration", "image": f"{imgfolder}/img2.jpg"},
    "example3": {"short": "demo", "long": "long description of the demo", "grade": "D+", "subject": "Demonstration", "image": f"{imgfolder}/img3.jpg"},
    "example4": {"short": "demo", "long": "long description of the demo", "grade": "C", "subject": "Demonstration", "image": f"{imgfolder}/img4.jpg"},
    "example5": {"short": "demo", "long": "long description of the demo", "grade": "B", "subject": "Demonstration", "image": f"{imgfolder}/img5.jpg"},
}


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route("/")
@log.catch
def index():
    """Main Page"""
    print(current_user)
    if current_user.is_authenticated:
        return render_template('index.html', redir="/home", logged=f"Logged In: {current_user.name}")
    else:
        return render_template('index.html', redir="/login", logged="Log in")


@app.route("/home")
@login_required
def home():
    """Home page for user"""
    return render_template('land.html', cards=shred(cards, 4))


@app.route('/items/<item>')
@login_required
def some_place_page(item):
    if item in cards:
        return render_template('cardview.html', card=cards[item])
    else:
        return render_template('errors/404.html', message=notfoundmessage()), 404


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# even i don't know what the next few bits do. google auth is a pain


@login_manager.unauthorized_handler
@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/callback")
@app.route('/upload/callback')
@app.route('/home/callback')
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    # Prepare and send a request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))
    # Now that you have tokens (yay) let's find and hit the URL
    # from Google that gives you the user's profile information,
    # including their Google profile image and email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    # You want to make sure their email is verified.
    # The user authenticated with Google, authorized your
    # app, and now you've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
        print("-" * 20)
        print(userinfo_response.json())
        print("-" * 20)
        if userinfo_response.json()["hd"] == "asms.sa.edu.au":
            user = User(
                id_=unique_id, name=users_name, email=users_email, profile_pic=picture
            )
            # Doesn't exist? Add it to the database.
            if not User.get(unique_id):
                User.create(unique_id, users_name, users_email, picture)
            login_user(user)
            return redirect(url_for("home"))
        else:
            return redirect(url_for("fivethreethreepage"))
    else:
        return "User email not available or not verified by Google.", 400


@app.route('/upload')
@login_required
def upload():
    return render_template("upload.html")


@app.route('/success', methods=['POST'])
def success():
    if request.method == 'POST':
        f = request.files['file']
        fname = urllib.parse.quote_plus(f.filename)
        form = request.form
        db = sqlite3.connect("database.db")
        cursor = db.cursor()
        cursor.execute(f'INSERT INTO filemapping VALUES (?, ?, ?, ?, ?, ?, time())',
                       (fname, form["short"], form["long"], current_user.name, form["subject"], form["tags"]))
        db.commit()
        db.close()
        f.save(f"{app.config['UPLOAD_PATH']}/{f.filename}")
        return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(ssl_context="adhoc")
