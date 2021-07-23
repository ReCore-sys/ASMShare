# //////////////////////////////////////////////////////////////////////////// #

# IMPORT EVERYTHING

# //////////////////////////////////////////////////////////////////////////// #

import json
import os
import random
import sqlite3
import sys
import threading
import time
import urllib
from base64 import b64decode, b64encode
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

import flask
import requests
import searchhelper
from db import init_db_command
from flask import *
from flask_htmlmin import HTMLMIN
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from fuzzywuzzy import fuzz, process
from oauthlib.oauth2 import WebApplicationClient
from pdf2image import convert_from_bytes, convert_from_path
from secret_data import *
from user import User
from werkzeug.utils import secure_filename

# //////////////////////////////////////////////////////////////////////////// #

# IMPORT EVERYTHING

# //////////////////////////////////////////////////////////////////////////// #
# this gets the directory this script is in. Makes it much easier to transfer between systems.
filepath = os.path.abspath(os.path.dirname(__file__))

# //////////////////////////////////////////////////////////////////////////// #

# Flask config

# //////////////////////////////////////////////////////////////////////////// #


app = Flask(__name__)
app.config['UPLOAD_PATH'] = f"{filepath}/files/"
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

login_manager = LoginManager()
login_manager.init_app(app)
client = WebApplicationClient(GOOGLE_CLIENT_ID)
app.secret_key = appkey

# //////////////////////////////////////////////////////////////////////////// #

# SQL config

# //////////////////////////////////////////////////////////////////////////// #


db = sqlite3.connect("database.db")
cursor = db.cursor()

try:
    # try create the database if it does not exist
    cursor.execute("CREATE TABLE filemapping (name TEXT, shortdesc TEXT, longdesc TEXT, uploader TEXT, subject TEXT, tags TEXT, time TIME, score INT, veryshort TEXT, id INT);")
except:
    # looks like it does exist
    pass


db.commit()
db.close()

# Naive database setup
try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

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

cached = {}

# //////////////////////////////////////////////////////////////////////////// #

# Helper functions

# //////////////////////////////////////////////////////////////////////////// #


def log(message, level=2):
    """Logs input to a file

     Parameters
     ----------
     message : str
     The message to log

     Level : int
     What level of logging to use
     """
    with open(f"{filepath}/logs", mode="a") as f:
        f.write(f"\n{(datetime.now()).strftime('%d/%m/%Y- %I:%M:%S %p')}: {message}")


def notfoundmessage():
    """Loops through the list of 404 messages"""
    global c
    message = fourohfour[c]
    c += 1
    if c == len(fourohfour):
        c = 0
    return message


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


# //////////////////////////////////////////////////////////////////////////// #

# Errors

# //////////////////////////////////////////////////////////////////////////// #


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

# Function to get the thumbnail for a file type

# //////////////////////////////////////////////////////////////////////////// #


def findfileicon(filename):
    """File icon finder

     Parameters
     ----------
     File name : str
     The name of the file to get the icon for

     Returns
     -------
     path to icon: str
     Path to the icon to use

     Examples
     --------
     >>> file.docx
     > ../static/file-images/docx.jpg"""

    ext = filename.split(".")[len(filename.split(".")) - 1]
    # if the file is an image, just use the image
    if ext in ["jpg", "png", "jpeg", "gif", "svg", "webp", "bmp"]:
        # I would just return the path to the file, but noooooooo, flask has to be special, so instead we clone it to the directory with the rest of the stuff
        # First we check if the file is already there cos why not
        if (filename) not in os.listdir(f"{filepath}/static/file-images/images"):
            # Copy the binary data and save to f the variable f
            with open(f"{filepath}/files/{filename}", "rb") as f:
                data = f.read()
            # Now go write f to a new file with the same name in the static directory
            with open(f"{filepath}/static/file-images/images/{filename}", "wb") as f:
                f.write(data)
        # Now return the path to the new file
        fileicon = r"""../static/file-images/images/""" + filename
    # if it is a video, use this format
    elif ext in ["mov", "mkv", "mp4"]:
        fileicon = r"""../static/file-images/video.jpg"""
    # now this is funky. If the file is a pdf, create and show a preview of the file
    elif ext in ["mp3", "ogg", "wav"]:
        fileicon = r"""../static/file-images/audio.jpg"""
    elif ext in ["pdf"]:
        # Stick it inside a try cos someone is gunna upload a .exe after renaming it to a .pdf (Duncan I'm looking at you)
        try:
            # only create a preview if it does not exist
            if (filename + ".jpg") not in os.listdir(f"{filepath}/static/file-images/pdfs"):
                convert_from_path(f'{filepath}/files/{filename}', output_folder=f"{filepath}/static/file-images/pdfs",
                                  fmt="jpeg", single_file=True, output_file=filename)
            fileicon = r"""../static/file-images/pdfs/""" + filename + ".jpg"
        # if the library nopes out, just keep going and use the normal pdf icon
        except:
            pass
    else:
        # if it fits into none of the above catagories, search for a jpg named the file type (docx.jpg, txt.jpg, ect)
        if (ext + ".jpg") in os.listdir(f"{filepath}/static/file-images"):
            fileicon = r"""../static/file-images/""" + ext + ".jpg"
        else:
            # if it still can't find it, use a unknown icon
            fileicon = r"""../static/file-images/unknown.jpg"""
    return fileicon


cards = {}
imgfolder = r"""../static/file-images/"""

# //////////////////////////////////////////////////////////////////////////// #

# Recompiles the cards (Call whenever db gets updated)

# //////////////////////////////////////////////////////////////////////////// #


def compileimages():
    """Turns the sql entry for each file into a dictionary so the site can display it"""
    global cards
    cards = {}
    db = sqlite3.connect("database.db")
    cursor = db.cursor()
    cursor.execute('SELECT * from filemapping')
    # loops through all the entries in the db then adds the specified type to the dict
    for x in cursor.fetchall():
        # creates the dict entry for the file
        cards[x[9]] = {}
        # Data structure is fun (No it's not please help me)
        cards[x[9]]["name"] = x[0]
        # adds the short description
        cards[x[9]]["short"] = x[1]
        # adds the long description
        cards[x[9]]["long"] = x[2]
        # adds uploader's name
        cards[x[9]]["uploader"] = x[3]
        # subject is added
        cards[x[9]]["subject"] = x[4]
        # tags
        cards[x[9]]["tags"] = x[5].split(",")
        cards[x[9]]["date"] = x[6]
        cards[x[9]]["score"] = x[7]
        # uses the above function to get/create an image for the thumbnail
        cards[x[9]]["image"] = findfileicon(x[9])
        # Shorter short description
        cards[x[9]]["veryshort"] = x[8]
    db.close()


compileimages()


# This is just unholy magic
def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


# Even god does not know what this bit does
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# //////////////////////////////////////////////////////////////////////////// #

# Page functions

# //////////////////////////////////////////////////////////////////////////// #


# Main page. If the user is logged in, shows that on the login button and the user's name
@app.route("/")
def index():
    """Main Page"""
    if current_user.is_authenticated:
        return render_template('index.html', redir="/home", logged=f"Logged In: {current_user.name}")
    else:
        return render_template('index.html', redir="/login", logged="Log in")


# This will be the main page for logged in users. Will show the exemplars
@app.route("/home", methods=["GET", "POST"])
@login_required
def home():
    """Home page for user"""
    if request.method == "GET":
        return render_template('land.html', cards=shred(cards, 4))
    elif request.method == "POST":
        query = request.form["query"]
        return redirect(url_for('search', query=query))


@app.route("/rickroll")
def rickroll():
    return render_template('rickroll.html')


@app.route("/feedback")
def feedback():
    return render_template('feedback.html')

# A full screen view of the examplars


@app.route('/items/<item>')
def fullcard(item):
    taglist = cards[item]["tags"]
    if item in cards:
        return render_template('cardview.html', card=cards[item], download=item, taglist=taglist)
    else:
        return render_template('errors/404.html', message=notfoundmessage()), 404


# No real use but meh
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/logs")
def logs():
    if any(i.isdigit() for i in current_user.email) and current_user.email not in admins:
        return redirect(url_for("fourohthreepage"))
    else:
        with open(f'{filepath}/logs', 'r') as f:
            return render_template('logs.html', logfile=f.readlines())


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


# ALL of the callbacks
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
        if "@asms.sa.edu.au" in users_email:
            user = User(
                id_=unique_id, name=users_name, email=users_email, profile_pic=picture
            )
            # Doesn't exist? Add it to the database.
            if not User.get(unique_id):
                User.create(unique_id, users_name, users_email, picture)
            login_user(user)
            log(f"User {current_user.name} {userinfo_response.json()['family_name']} has logged in")
            print(f"usr: {current_user.email}")
            hold = random.randint(1, 10000)
            if hold == 1:
                # has a 1 in 10000 chance to rickroll the user on login
                return redirect(url_for("rickroll"))
            else:
                return redirect(url_for("home"))
        else:
            return redirect(url_for("fivethreethreepage"))
    else:
        return "User email not available or not verified by Google.", 400


# Page where you upload your files
@app.route('/upload')
# @login_required
def upload():
    # Retrieves the tags from a file
    tagfile = json.load(open(f"{filepath}/tags.json", "r"))
    # Sorts the tags by their usage
    tagsdict = {k: v for k, v in sorted(tagfile.items(), key=lambda item: item[1], reverse=True)}
    # Turns them into a list of keys
    tags = [x for x in tagsdict]
    return render_template("upload.html", tags=tags)


# If the upload goes well, send it here to actually be stored
@app.route('/success', methods=['POST'])
def success():
    # Oh boy, this one is gunna be a pain to explain

    # We assume the request will be a GET request. If not, idk. I'll deal with that later
    if request.method == 'POST':
        # Assign the file to the variable f. I'm not sure what data type this is, but I assume binary
        f = request.files['file']

        # Split the name at the last . to get the file extension. This is to make sure we ignore any other .'s in tha name
        ext = (f.filename).split(".")[len((f.filename).split(".")) - 1]
        form = request.form

        # get the short description and name from the form, then assign them to their own variables. I should probs do it with the rest but eh
        short = form["short"]
        fname = form["name"]

        # If the short description if over 35 characters, only add the first 32 and then add a "..." on the end
        if len(short) > 35:
            veryshort = "".join([short[:32]]) + "..."
        else:

            # If the short description is not, leave it as it is
            veryshort = short

        # Honestly I don't know why I have this. So far it hasn't caused any issues so I'll leave it
        if len([fname, form["short"], form["long"], current_user.name, form["subject"], form["tags"]]) == 6:

            # SQL stuff
            db = sqlite3.connect("database.db")
            cursor = db.cursor()

            # get all the ids from the database
            cursor.execute("select id from filemapping")

            # add em to a list
            usedids = [x[0] for x in cursor.fetchall()]

            # Create a random 6 digit number to assign to the upload
            tryid = random.randint(int("1" + ("0" * 5)), int("9" * 6))

            # If the id is already in the database, try again
            while tryid in usedids:
                tryid = random.randint(int("1" + ("0" * 5)), int("9" * 6))
            # Now we do some funky stuff with tags
            tags = json.loads(form["tags"])
            print(tags)
            # max of 5 tags. You can enter more, but they won't show up
            tags = [x["value"].replace(" ", "-") for x in tags][:5]

            prettytags = ",".join(tags)

            # Add all the stuff the the database
            cursor.execute(f'INSERT INTO filemapping VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)',
                           (fname, short, form["long"], current_user.name, form["subject"], prettytags, ((datetime.now()).strftime('%d/%m/%Y')), veryshort, f"{tryid}.{ext}"))
            db.commit()
            db.close()

            # This bit just pulls apart the list into it's indvidual tags, then takes apart the tag, putting it back together but only with alphanumetic characters or hyphens
            tags = [x for x in [ch.lower() for ch in tags if ch.isalnum() or "-"]]
            # Opens a json file to store the tag frequency
            tagfile = json.load(open(f"{filepath}/tags.json", "r"))
            # Loops though all the tags
            for x in tags:
                # If the tag already exists in the json file, just add 1 to it's frequency
                if x in tagfile:
                    tagfile[x] = tagfile[x] + 1
                # Otherwise just set the frequency to 1
                else:
                    tagfile[x] = 1
            json.dump(tagfile, open(f"{filepath}/tags.json", "w"))

            # Save the file in the folder
            f.save(f"{app.config['UPLOAD_PATH']}/{tryid}.{ext}")

            # Log the upload
            log(f"User {current_user.name} has uploaded '{fname}' ({tryid})")

            # Reload the image cache to account for the new uploads
            compileimages()
    else:
        return redirect(url_for("fourohsixpage"))
    # Head back home
    return redirect(url_for("home"))


@app.route("/search/")
def emptysearch():
    return render_template("search.html", query="")


@app.route("/search/<query>")
def search(query):
    global cached
    query = query.strip()
    # Here we cache the results of a search
    if query in cached:
        # If the query is in the cache, use the cached version
        results = cached[query]
        print("Using cache for ", query)
    # If not, toast the cpu
    else:
        # So I wrote a custom function here to evaluate and order the options. I imported it from another file so go check out the searchhelper.py (https://github.com/ReCore-sys/ASMShare/blob/main/searchhelper.py) file to see how it works
        results = searchhelper.search(cards, query)
        # Store the result
        cached[query] = results
        print("Not using cache for ", query)
    # If the cache's size is over 750MB, remove the last item in the cache. Keep going until the size is under 750MB
    while sys.getsizeof(cached) > 786432000:
        k = cached.keys()
        cached.pop(k[len(x) - 1])
    if len(query) > 30:
        query = query[:27] + "..."
    return render_template("search.html", results=results, query=query)


@app.route('/download/<filename>', methods=['GET', 'POST'])
@login_required
def download(filename):
    log(f"{current_user.name} has downloaded {filename}")
    path = f"{filepath}/files/{filename}"
    return send_file(path, as_attachment=True)


# //////////////////////////////////////////////////////////////////////////// #

# If we run the file directly, start a server

# //////////////////////////////////////////////////////////////////////////// #


if __name__ == "__main__":
    # Checks if the ssl cert files exist. If they don't, fall back to a testing cert
    if os.path.isfile(r"/etc/letsencrypt/live/asmshare.xyz/fullchain.pem") and os.path.isfile(r"/etc/letsencrypt/live/asmshare.xyz/privkey.pem"):
        app.run(ssl_context=("/etc/letsencrypt/live/asmshare.xyz/fullchain.pem", "/etc/letsencrypt/live/asmshare.xyz/privkey.pem"),  # Tries to find the actual good ssl cert
                host="0.0.0.0",  # Listen on all available ips
                port=443
                )
    else:
        app.run(ssl_context="adhoc",  # If the good one fails, use a testing one
                host="0.0.0.0",  # Listen on all ips
                port=5000
                )
