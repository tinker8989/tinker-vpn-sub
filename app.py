import os
from flask import Flask, Response

app = Flask(name)
BASE_DIR = os.path.dirname(os.path.abspath(file))

def load_file(name):
    path = os.path.join(BASE_DIR, name)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def make_response(content, title):
    res = Response(content, mimetype="text/plain")
    res.headers["Profile-Title"] = title
    res.headers["Profile-Update-Interval"] = "3600"
    return res

@app.route("/standard")
def standard():
    return make_response(load_file("standard.txt"), "Tinker VPN Standard")

@app.route("/premium")
def premium():
    return make_response(load_file("premium.txt"), "Tinker VPN Premium")

@app.route("/family")
def family():
    return make_response(load_file("family.txt"), "Tinker VPN Family")

@app.route("/")
def home():
    return "Tinker VPN OK"

if name == "main":
    app.run(host="0.0.0.0", port=3000)
