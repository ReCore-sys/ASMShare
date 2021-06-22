"""Bleeding edge features that probably don't work"""
import getpass
import json
import os
import random
import sqlite3
import sys
import threading
import time

from fuzzywuzzy import fuzz, process

db = sqlite3.connect("database.db")
cursor = db.cursor()
cursor.execute('SELECT * from filemapping')
res = cursor.fetchall()

cleanres = []
for x in res:
    v = []
    for z in x:
        v.append(str(z))
    v = " ".join(v)
    cleanres.append(v)
print("-" * 20)
print("Formatted data")
print("-" * 20)
print(cleanres)
print("-" * 20)
inp = input("> ")
suggestions = process.extract(inp, cleanres)
close = fuzz.token_sort_ratio(inp, suggestions[0])
if close > 0:
    print(list(suggestions))
print(close)
