from flask import Flask, render_template, Blueprint, request

power_control_page = Blueprint('power_control_page', __name__, template_folder='templates')

power_control_callback = None

def set_callback(callback):
    global power_control_callback
    power_control_callback = callback

@power_control_page.route('/power_control')
def power_control():
    return render_template("power_control.html")

@power_control_page.route("/power_control_request/", methods=['POST'])
def control_request():
    #Moving forward code
    global power_control_callback
    if power_control_callback != None:
        power_control_callback(request.form)
    return render_template('power_control.html')

