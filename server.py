import json
import os
import random
import re
import sqlite3
import sys
import threading
import time
from threading import Thread

from fuzzyfinder import fuzzyfinder
from loguru import logger as log

filepath = filepath = os.path.abspath(os.path.dirname(__file__))


@log.catch()
def core():
    db = sqlite3.connect("database.db")
    cursor = db.cursor()
    try:
        cursor.execute("CREATE TABLE files (id INTEGER, filename TEXT, tags TEXT, subject TEXT);")
    except:
        pass
    # inp = input("File name > ")
    cursor.execute("select filename from files")
    result = cursor.fetchall()
    files = []
    """for x in result:
        files.append(x[0])"""
    files = os.listdir(f"{filepath}/files/")
    prettyfiles = [x.split(".")[0] for x in files]
    try:
        prettyfiles.remove("")
    except:
        pass
    print(prettyfiles)
    search = input("File to find: ")
    suggestions = fuzzyfinder(search, prettyfiles)
    first = list(suggestions)[0]
    print(first)
    print(list(fuzzyfinder(first, files))[0])


corethread = Thread(target=core)
corethread.start()
