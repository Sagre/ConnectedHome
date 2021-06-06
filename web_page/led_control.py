from flask import Flask, render_template, Blueprint, request

led_control_page = Blueprint('led_control_page', __name__, template_folder='templates')

led_control_callback = None

def set_callback(callback):
    global led_control_callback
    led_control_callback = callback

@led_control_page.route('/led_control')
def led_control():
    return render_template("led_control.html")

@led_control_page.route("/led_control_request/", methods=['POST'])
def control_request():
    #Moving forward code
    global led_control_callback
    if led_control_callback != None:
        led_control_callback(request.form)
    return render_template('led_control.html')

