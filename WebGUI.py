from flask import Flask
from web_page.home import home_page
from web_page.power_control import power_control_page
from web_page.power_control import set_callback as power_control_set_callback
from web_page.led_control import led_control_page
from web_page.led_control import set_callback as led_control_set_callback

from Communication import Comm

class WebGui:

    flask_app = None
    comm = None

    def power_control_callback(self, request_form):
        comm_dict = {}
        comm_dict["id"] = request_form["id"]
        comm_dict["val"] = request_form["req"]
        try:
            self.comm.publish("power_request", comm_dict)
        except Exception as err:
            print(err)


    def led_control_callback(self, request_form):

        comm_dict = {}
        comm_dict["id"] = request_form["id"]
        comm_dict["val"] = request_form["req"]
        try:
            self.comm.publish("led_request", comm_dict)
        except Exception as err:
            print(err)

    def run(self):
        self.flask_app.run(debug = True)


    def __init__(self, name):
        self.comm = Comm("WebGUI")
        while not self.comm.is_connected():
            pass

        self.flask_app = Flask(name)
        self.flask_app.register_blueprint(home_page)
        self.flask_app.register_blueprint(power_control_page)
        power_control_set_callback(self.power_control_callback)
        self.flask_app.register_blueprint(led_control_page)
        led_control_set_callback(self.led_control_callback)

        self.flask_app.static_folder = "web_page/static"

if __name__ == "__main__":
    gui = WebGui("WebControl")
    gui.run()