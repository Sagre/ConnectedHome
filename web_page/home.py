from flask import Flask, render_template, Blueprint

home_page = Blueprint('home_page', __name__, template_folder='templates')

@home_page.route('/')
def home():
    return render_template("home.html")

@home_page.route('/about')
def about():
    return render_template("about.html")

