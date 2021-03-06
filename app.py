# //////////////////////////////////////////////////////////////////////////// #

# IMPORT EVERYTHING

# //////////////////////////////////////////////////////////////////////////// #
# Builtin imports
import functools
import random
import sqlite3
import string
import sys
import time
from datetime import datetime
from pathlib import Path
import shutil

# 3rd party imports
import requests
import ujson as json
from flask import *
from flask_compress import Compress
from flask_login import LoginManager, current_user, login_user, logout_user
from loguru import logger
from oauthlib.oauth2 import WebApplicationClient
from pdf2image import convert_from_path
from werkzeug import exceptions


# local imports
import scan  # A custom lib to scan files for danger. So you guys can't go find exploits, this will be hidden
import searchhelper
from secret_data import *
from user import User

# //////////////////////////////////////////////////////////////////////////// #

# IMPORT EVERYTHING

# //////////////////////////////////////////////////////////////////////////// #
# this gets the directory this script is in. Makes it much easier to transfer between systems.

filepath = os.path.abspath(os.path.dirname(__file__))

# Adds a logger to catch errors
logger.add(f"{filepath}/deeplogs.log", backtrace=False, enqueue=True, format=("="*20 + "\n"*5 +
                                                                              "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<blue>{line}</blue> - <level>{message}</level>"))


# //////////////////////////////////////////////////////////////////////////// #

# Flask config

# //////////////////////////////////////////////////////////////////////////// #

# Detects if we are running the actual version that others will be using
prod = (os.name == "posix")

app = Flask("ASMShare")
app.config['UPLOAD_PATH'] = f"{filepath}/files/"
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['MINIFY_HTML'] = True

login_manager = LoginManager()
login_manager.init_app(app)
client = WebApplicationClient(GOOGLE_CLIENT_ID)
app.secret_key = appkey
login_needed = True
compress = Compress()
app.config["COMPRESS_ALGORITHM"] = "br"
app.config["COMPRESS_BR_LEVEL"] = 11
Compress(app)

# //////////////////////////////////////////////////////////////////////////// #

# SQL config

# //////////////////////////////////////////////////////////////////////////// #

# Connect to the db file and try create a table. If the table exists already it just does nothing. If the file does not exist, it creates one then adds the table
db = sqlite3.connect("database.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS filemapping (name TEXT, shortdesc TEXT, longdesc TEXT, uploader TEXT, subject TEXT, tags TEXT, time TIME, score INT, veryshort TEXT, id INT);")
db.commit()
db.close()

# //////////////////////////////////////////////////////////////////////////// #

# Varibles definition

# //////////////////////////////////////////////////////////////////////////// #

# region 404 errors
fourohfour = ["Welp. This is awkward",
              "Nice One",
              "This isn't great. In the meantime, drink some water",
              "THIS ERROR PAGE IS SPONSORED BY RAID SHADOW LEGENDS, ONE OF THE BIGGEST MOBILE ROLE PLAYING GAMES OF 2019 AND IT'S TOTALLY FREE!",
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
              "Server hamster needs more vodka",
              "This isn't the url your looking for"
              ]

random.shuffle(fourohfour)

cached = {}

validids = []

# //////////////////////////////////////////////////////////////////////////// #

# Helper functions

# //////////////////////////////////////////////////////////////////////////// #


@logger.catch
def convert_bytes(num):
    """convert_bytes
\n
Turns a bytecount into a nicely readable string

    Parameters
    ----------
    num : int
        Number of bytes to evaluate

    Returns
    -------
    str
        Human readable string
    """

    step_unit = 1024

    for x in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < step_unit:
            return f"{round(num)} {x}"
        num /= step_unit


@logger.catch
def log(message, level=2):
    """log\n
    Writes the input to the log file to

    Parameters
    ----------
    message : str
        The message to log to the file
    level : int, optional
        What level of logging to use, by default 2
    """
    with open(f"{filepath}/logs.log", mode="a") as f:
        f.write(
            f"\n{(datetime.now()).strftime('%d/%m/%Y- %I:%M:%S %p')}: {message}")


@logger.catch
def notfoundmessage():
    """notfoundmessage\n
    Gets a message to display on the 404 page.

    Returns
    -------
    str
        The message to use
    """
    # Check if the variable choices exists. If not, create it. Pylance has a stroke if I use global vars so I have to do this
    # to stop my IDE yelling slurs at me
    if 'choices' not in locals():
        choices = random.choices(fourohfour, k=5)
    if len(choices) > 0:
        msg = choices[-1]
    else:
        choices = random.choices(fourohfour, k=5)
        msg = choices[-1]
    choices.pop(-1)
    return msg


@logger.catch
def shred(d, n=2):
    """shred\n
    Cuts a dict into a list of n sized dicts

    Parameters
    ----------
    d : dict
        The dict to cut
    n : int, optional
        Size of each chunk, by default 2

    Returns
    -------
    list
        List of dicts
    """
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


@logger.catch
def updatestats(type=None):
    """updatestats\n
    Adds 1 to the specified stat

    Parameters
    ----------
    type : str, optional
        What stat to modify, by default None
    """
    create_stats()
    db = sqlite3.connect("database.db")
    cursor = db.cursor()
    cursor.execute("select * from stats")
    if type == None:
        print("No stat specified")
    else:
        if type == "logins":
            cursor.execute("update stats set logins = logins + 1")
        elif type == "downloads":
            cursor.execute("update stats set downloads = downloads + 1")
        db.commit()
        db.close()


@logger.catch
def findfileicon(filename):
    """findfileicon\n
    Gets an icon for each type of file

    Parameters
    ----------
    filename : str
        The name of the file to get a file

    Returns
    -------
    str
        Path to image to use for the file
    """

    ext = filename.split(".")[-1]
    # if the file is an image, just use the image
    if ext in ["jpg", "png", "jpeg", "gif", "svg", "webp", "bmp"] and prod:
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
        # only create a preview if it does not exist
        if not prod:
            fileicon = r"""../static/file-images/pdf.jpg"""
        else:
            if (filename + ".jpg") not in os.listdir(f"{filepath}/static/file-images/pdfs"):
                convert_from_path(f'{filepath}/files/{filename}', output_folder=f"{filepath}/static/file-images/pdfs",
                                  fmt="jpeg", single_file=True, output_file=filename)
            fileicon = r"""../static/file-images/pdfs/""" + filename + ".jpg"
        # if the library nopes out, just keep going and use the normal pdf icon
    else:
        # if it fits into none of the above catagories, search for a jpg named the file type (docx.jpg, txt.jpg, ect)
        if (ext + ".jpg") in os.listdir(f"{filepath}/static/file-images"):
            fileicon = r"""../static/file-images/""" + ext + ".jpg"
        else:
            # if it still can't find it, use a unknown icon
            fileicon = r"""../static/file-images/unknown.jpg"""
    return fileicon


@logger.catch
def getname(email=None):
    """getname\n
    Gets the first name of the user

    Returns
    -------
    str
        The name to use for the person
    """

    db = sqlite3.connect("sqlite_db")
    cursor = db.cursor()
    if email == None:
        email = current_user.email
    cursor.execute("Select name from user where email = ?", (email, ))
    res = cursor.fetchone()
    if res != None:
        namebyemail = res[0]

    with open("names.json", "r") as names:
        names = json.load(names)
        db.commit()
        db.close()
        if email in names:
            return names[email]
        elif "namebyemail" in locals():
            return namebyemail
        else:
            return email


cards = {}
imgfolder = r"""../static/file-images/"""


@logger.catch
def compileimages():
    """compileimages\n
    Recompile the image dict
    """
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
        cards[x[9]]["uploader"] = getname(x[3])
        # subject is added
        cards[x[9]]["subject"] = x[4]
        # tags
        if x[5] == None:
            cards[x[9]]["tags"] = "None"
        else:
            cards[x[9]]["tags"] = x[5].split(",")
        cards[x[9]]["date"] = x[6]
        cards[x[9]]["score"] = x[7]
        # uses the above function to get/create an image for the thumbnail
        cards[x[9]]["image"] = findfileicon(x[9])
        # Shorter short description
        cards[x[9]]["veryshort"] = x[8]
    db.close()


compileimages()

stats = {}


@logger.catch
def create_stats():
    """create_stats\n
    Pulls stats from the db
    """
    db = sqlite3.connect("database.db")
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(1) FROM filemapping;")
    stats["uploads"] = cursor.fetchone()[0]
    db.close()

    db = sqlite3.connect("sqlite_db")
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(1) FROM user;")
    stats["users"] = cursor.fetchone()[0]
    db.close()

    rec = 0
    paths = [f"{filepath}/files", f"{filepath}/static/file-images/images",
             f"{filepath}/static/file-images/pdfs"]
    for x in paths:
        root_directory = Path(x)
        b = sum(f.stat().st_size for f in root_directory.glob(
            '**/*') if f.is_file())
        rec += b
    stats["size"] = convert_bytes(rec).split(" ")

    db = sqlite3.connect("database.db")
    cursor = db.cursor()
    cursor.execute("SELECT logins FROM stats;")
    stats["logins"] = cursor.fetchone()[0]
    db.close()

    tags = json.load(open(f"{filepath}/tags.json"))
    top = max(tags.items(), key=lambda k: k[1])
    stats["toptag"] = top[0]


create_stats()


@logger.catch
def is_admin():
    """is_admin\n
    Checks if the user is admin or in the admins file

    Returns
    -------
    bool
        Whether or not they are an admin
    """
    if any(i.isdigit() for i in current_user.email) and current_user.email not in admins:
        return False
    else:
        return True


def updateall():
    """updateall\n
    Updates all dictionaries
    """
    create_stats()
    compileimages()

# //////////////////////////////////////////////////////////////////////////// #

# Errors

# //////////////////////////////////////////////////////////////////////////// #


@app.errorhandler(404)
@logger.catch
def not_found(e):
    return render_template('errors/404.html', message=notfoundmessage()), 404


@app.errorhandler(403)
@logger.catch
def fourohthree(e):
    return render_template('errors/403.html'), 403


@app.route("/403")
@logger.catch
def fourohthreepage():
    return render_template('errors/403.html')


@app.errorhandler(406)
@logger.catch
def fourohsix(e):
    return render_template('errors/406.html'), 406


@app.route("/406")
@logger.catch
def fourohsixpage():
    return render_template('errors/406.html')


@app.errorhandler(500)
@logger.catch
def fivehundred(e):
    return render_template('errors/500.html'), 500


@app.route("/500")
@logger.catch
def fivehundredpage():
    return render_template('errors/500.html')


@app.route("/553")
@logger.catch
def fivethreethreepage():
    return render_template('errors/553.html')


@app.errorhandler(408)
@logger.catch
def fouroheight(e):
    return render_template('errors/408.html'), 408


@app.route("/408")
@logger.catch
def fouroheightpage():
    return render_template('errors/408.html')


@app.errorhandler(400)
@logger.catch
def fourhundred(e):
    return render_template('errors/400.html'), 400


@app.route("/400")
@logger.catch
def fourhundredpage():
    return render_template('errors/400.html')


@app.errorhandler(413)
@logger.catch
def fouronethree(e):
    return render_template('errors/413.html'), 413


@app.route("/413")
@logger.catch
def fouronethreepage():
    return render_template('errors/413.html')


@app.errorhandler(429)
@logger.catch
def fourytwentynine(e):
    return render_template('errors/413.html'), 413


@app.route("/429")
@logger.catch
def fourytwentyninepage():
    return render_template('errors/429.html')

# //////////////////////////////////////////////////////////////////////////// #

# Login based black magic

# //////////////////////////////////////////////////////////////////////////// #


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

# Even god does not know what this bit does


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


def improved_login(func):
    """improved_login\n
    Custom login Manager

    Parameters
    ----------
    func : function
        The page to attach to and check if user is logged in

    Returns
    -------
    func
        The page to send them to (either the page they were trying to visit or the login page)
    """
    @functools.wraps(func)
    def page():
        if current_user.is_authenticated:
            return func()
        else:
            res = make_response(redirect(url_for("login")))
            if func.__name__ == "entry":
                res.set_cookie("return-page", "home", 60 * 5)
            else:
                res.set_cookie("return-page", func.__name__, 60 * 5)
            return res
    return page

    # //////////////////////////////////////////////////////////////////////////// #

    # Page functions

    # //////////////////////////////////////////////////////////////////////////// #

    # Main page. If the user is logged in, shows that on the login button and the user's name


@app.route("/")
@logger.catch
def entry():
    """Main Page"""
    if current_user.is_authenticated:
        return render_template('index.html', redir="/home", logged=f"Logged In: {getname()}")
    else:
        return render_template('index.html', redir="/home", logged="Log in")

# This will be the main page for logged in users. Will show the exemplars


@app.route("/home", methods=["GET", "POST"])
@logger.catch
@improved_login
def home():
    """Home page for user"""
    updateall()
    if request.method == "GET":
        return render_template('land.html', stats=stats)
    elif request.method == "POST":
        query = request.form["query"]
        return redirect(url_for('search', query=query))


@app.route("/rickroll")
@logger.catch
def rickroll():
    """:)"""
    return render_template('rickroll.html')


@app.route("/mobile")
@logger.catch
def mobile():
    """:)"""
    return render_template('mobile.html')


@app.route("/info")
@logger.catch
def info():
    """:)"""
    return render_template('info.html')


@app.route("/errors")
@logger.catch
def errors():
    """:)"""
    return render_template('errorsexaplained.html')


@app.route("/error")
@logger.catch
def error():
    """A page that only exists to raise a 500 error"""
    a = 10
    b = 0
    a/b


@app.route("/feedback")
@logger.catch
def feedback():
    "Feedback form"
    return render_template('feedback.html')

# A full screen view of the examplars


@app.route('/items/<item>')
@logger.catch
def fullcard(item):
    "Fullscreen display of an item"
    taglist = cards[item]["tags"]
    if item in cards:
        return render_template('cardview.html', card=cards[item], download=item, taglist=taglist)
    else:
        return redirect(url_for("not_found", message=notfoundmessage())), 404


@app.route("/logout")
@logger.catch
@improved_login
def logout():
    "Logs the user out"
    updateall()
    logout_user()
    return redirect(url_for("entry"))


@app.route("/logs")
@logger.catch
@improved_login
def logs():
    "A page to show the logs"
    if is_admin():
        with open(f'{filepath}/logs.log', 'r') as f:
            return render_template('logs.html', logfile=f.readlines())
    else:
        return redirect(url_for("fourohthreepage"))


@app.route("/deeplogs")
@logger.catch
@improved_login
def deeplogs():
    "A page to show the deeplogs"
    if is_admin():
        with open(f'{filepath}/deeplogs.log', 'r') as f:
            return render_template('deeplogs.html', logfile=f.read())
    else:
        return redirect(url_for("fourohthreepage"))


@app.route("/change", methods=["POST", "GET"])
@logger.catch
@improved_login
def changename():
    "Page that allows you to change your name"
    updateall()
    if request.method == "GET":
        return render_template('change.html')
    elif request.method == "POST":
        rename = request.form["name"]
        log(f"User {current_user.email} changed their name to {rename} (was {getname()})")
        with open(f"{filepath}/names.json") as j:
            j = json.load(j)
            if rename == "clear":
                j.pop(current_user.email)
            else:
                j[current_user.email] = rename
            json.dump(j, open(f"{filepath}/names.json", "w"))
        return redirect(url_for("home"))

# even i don't know what the next few bits do. google auth is a pain


@login_manager.unauthorized_handler
@app.route("/login")
@logger.catch
def login():
    "Either send you to the login handler or logs you in with dummy data"
    if login_needed:
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
    # If the login_needed var is off, use a dummy account
    else:
        unique_id = u"0"
        users_email = "test1234@asms.sa.edu.au"
        picture = "https://cdn4.iconfinder.com/data/icons/ionicons/512/icon-ios7-gear-512.png"
        users_name = "Test User"
        user = User(
            id_=unique_id, name=users_name, email=users_email, profile_pic=picture
        )
        # Doesn't exist? Add it to the database.
        if not User.get(unique_id):
            User.create(unique_id, users_name, users_email, picture)
        login_user(user)
        if request.cookies.get("return-page") == None or request.cookies.get("return-page") == "None":
            return redirect(url_for("home"))
        else:
            return redirect(url_for(request.cookies.get("return-page")))

# ALL of the callbacks


@app.route("/login/callback")
@app.route('/upload/callback')
@app.route('/home/callback')
@logger.catch
def callback():
    "Blasphemy"
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
            log(
                f"User {getname()} {userinfo_response.json()['family_name']} has logged in")
            print(f"usr: {current_user.email}")
            hold = random.randint(1, 10000)
            if hold == 1:
                # has a 1 in 10000 chance to rickroll the user on login
                return redirect(url_for("rickroll"))
            else:
                updatestats("logins")
                if request.cookies.get("return-page") == None or request.cookies.get("return-page") == "None":
                    return redirect(url_for("home"))
                else:
                    return redirect(url_for(request.cookies.get("return-page")))
        else:
            return redirect(url_for("fivethreethreepage"))
    else:
        return "User email not available or not verified by Google.", 400

# Page where you upload your files


@app.route('/upload')
@logger.catch
@improved_login
def upload():
    # TODO: Fix this bit. It causes error randomly. Dunno why
    checkid = (''.join(random.choice(string.ascii_letters) for i in range(30)))
    # validids.append(checkid)
    "The upload page"
    # Retrieves the tags from a file
    tagfile = json.load(open(f"{filepath}/tags.json", "r"))
    # Sorts the tags by their usage
    tagsdict = {k: v for k, v in sorted(
        tagfile.items(), key=lambda item: item[1], reverse=True)}
    # Turns them into a list of keys
    tags = list(tagsdict.keys())
    req = True
    return render_template("upload.html", tags=tags, req=req, checkid=checkid, banned=banned)

# If the upload goes well, send it here to actually be stored


@app.route('/success', methods=['POST'])
@logger.catch
def success():
    "A page that you get sent to when you upload something"
    # Oh boy, this one is gunna be a pain to explain

    # We assume the request will be a GET request. If not, idk. I'll deal with that later
    if request.method == 'POST':
        # Assign the file to the variable f. I'm not sure what data type this is, but I assume binary
        try:
            f = request.files['file']
        except exceptions.RequestEntityTooLarge:
            return abort(413)

        # Split the name at the last . to get the file extension. This is to make sure we ignore any other .'s in tha name
        ext = (f.filename).split(".")[-1]

        # Check if the attached upload ID is valid. If not, 429 them.
        form = request.form
        """
        if form["check"] not in validids:
            abort(429)
        else:
            # Remove the ID if it works
            validids.remove(form["check"])
        """

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
        if len([fname, form["short"], form["long"], getname(), form["subject"], form["tags"]]) == 6:

            # SQL stuff
            db = sqlite3.connect("database.db")
            cursor = db.cursor()

            # get all the ids from the database
            cursor.execute("select id from filemapping")

            # add em to a list
            usedids = [int(x[0].split(".")[0]) for x in cursor.fetchall()]
            # If the idlist is empty, create the first id (0)
            if usedids == []:
                tryid = 0
            else:
                # Get the largest id and add one
                tryid = max(usedids) + 1

            # If for some reason it already exists, try again
            while tryid in usedids:
                tryid = max(usedids) + 1
            # Save the file in the folder
            f.save(f"{app.config['UPLOAD_PATH']}/{tryid}.{ext}")
            scanres = scan.check(f"{app.config['UPLOAD_PATH']}/{tryid}.{ext}")
            if scanres[0]:
                if len(form["tags"]) > 0:
                    # Now we do some funky stuff with tags
                    tags = json.loads(form["tags"])
                    # max of 5 tags. You can enter more, but they won't show up
                    tags = [x["value"].replace(" ", "-") for x in tags[:5]]

                    prettytags = ",".join(tags)

                    # This bit just pulls apart the list into it's indvidual tags, then takes apart the tag, putting it back together but only with alphanumetic characters or hyphens
                    tags = [x for x in [ch.lower()
                                        for ch in tags if ch.isalnum() or "-"]]
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
                else:
                    prettytags = None

                # Add all the stuff the the database
                cursor.execute(f'INSERT INTO filemapping VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)',
                               (fname, short, form["long"], current_user.email, form["subject"], prettytags, ((datetime.now()).strftime('%d/%m/%Y')), veryshort, f"{tryid}.{ext}"))

                # Log the upload
                log(f"User {getname()} has uploaded '{fname}' ({tryid})")
                db.commit()
                db.close()
            else:
                log(
                    f"User {getname()} has tried to upload '{fname}' ({tryid}) but it was caught by the scanner ({scanres[1]})")
                shutil.move(f"{app.config['UPLOAD_PATH']}/{tryid}.{ext}",
                            f"{filepath}/quarantine/{tryid}.{ext}_")
            # Reload the image cache to account for the new uploads
            updateall()

    else:
        return redirect(url_for("fourohsixpage"))
    # Head back home
    if not prod:
        time.sleep(3)
    updateall()
    return redirect(url_for("home"))


@app.route("/search/")
@logger.catch
def emptysearch():
    "If there is no search query, show this"
    return render_template("search.html", query="")


@app.route("/search/<query>")
@logger.catch
def search(query):
    "Shows searched stuff"
    global cards
    compileimages()
    query = query.strip()  # So I wrote a custom function here to evaluate and order the options. I imported it from another file so go check out the searchhelper.py (https://github.com/ReCore-sys/ASMShare/blob/main/searchhelper.py) file to see how it works
    results = searchhelper.search(cards, query)
    if len(query) > 30:
        query = query[:27] + "..."
    return render_template("search.html", results=results, query=query)


@app.route('/download/<filename>')
def download(filename):
    "Download a file. Requires you to log in first"
    if filename in os.listdir(f"{filepath}/files"):
        path = f"{filepath}/files/{filename}"
        updatestats("downloads")
        return send_file(path, as_attachment=True)
    else:
        return redirect(url_for("not_found"))

# //////////////////////////////////////////////////////////////////////////// #

# If we run the file directly, start a server

# //////////////////////////////////////////////////////////////////////////// #


if __name__ == "__main__":

    # Checks if the ssl cert files exist. If they don't, fall back to a testing cert
    if os.path.isfile(r"/etc/letsencrypt/live/asmshare.xyz/fullchain.pem") and os.path.isfile(r"/etc/letsencrypt/live/asmshare.xyz/privkey.pem"):
        # Use gnunicorn to run the server if we are on prod. For some god forsaken reason, if I don't add the --preload, stuff breaks and refuses to work.
        if prod == False:
            raise Warning(
                "WARNING\nNot running on the correct OS, but you somehow have the right cert files. How? TBH your prod var is probably broken")
        os.system(
            f"gunicorn -c {filepath}/wsgi-config.py app:app --preload")

    else:
        if prod:
            raise Warning(
                "WARNING\nRunning on the correct server, but the cert files cannot be found, so using the fallback one")
        app.run(ssl_context="adhoc",  # If the good one fails, use a testing one
                host="0.0.0.0",  # Listen on all ips
                port=5000
                )
