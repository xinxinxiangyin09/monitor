import os
import sys

from db_tools import Data

from flask import Flask, render_template, jsonify, Markup


app = Flask(__name__)

cert_path = os.path.join(sys.path[0], "certificate")
ssl_keys = (os.path.join(cert_path, "server.crt"), os.path.join(cert_path, "server.key"))


@app.template_filter()
def upper_(value):
    return value.upper()

app.add_template_filter(upper_)

@app.route("/")
@app.route("/index")
def index():
    data = Data().index_data()
    return render_template("index.html", data=data)

@app.route("/<host_id>")
def detail(host_id):
    data = Data().detail_data(host_id=host_id)
    return render_template("detail.html", data=data)