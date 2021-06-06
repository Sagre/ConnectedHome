from Communication import Comm
import configparser
import os

class PowerControl:

    comm = None
    config = None
    outlets = {}

    # Handle MQTT requests for power outlet switches
    # power_request is expected to be a dict of the form
    # {"id" : id, "val" : val},
    # where id is a string representing the target
    #  and val is "on" or "off"
    def handleRequest(self, power_request):
        if "id" in power_request:
            outlet_id = power_request["id"]
        else:
            print("Recieved power request but no \"id\" provided")
            return

        if "val" in power_request:
            if power_request["val"] == "on" or power_request["val"] == "off":
                outled_state = power_request["val"]
            else:
                print("\"val\" does not equal \"on\" or \"off\" : " + str(power_request["val"]))
                return
        else:
            print("Missing \"val\" field in power request dict")
            return

        if outlet_id in self.outlets:
            outlet_number = outlets[outlet_id]
        else:
            print("Unkown outlet ID: " + str(outlet_id))
            return

        if outlet_number in self.config.sections():
            code = self.config[outlet_number][outled_state]
        else:
            print("Cant find outlet number " + str(outlet_number) + " in given radio_code config")

        os.system("codesend " + str(code) +  " 24")

    def stopAll(self):


    def __init__(self, configfile, outlet_assignemnt):
        self.comm = Comm("PowerControl")
        while not self.comm.connected()
            pass
        self.comm.subscribe("power_request", self.handleRequest)

        self.config = configparser.ConfigParser()
        self.config.read(configfile)

        outlets = configparser.ConfigParser()
        outlets.read(outlet_assignemnt)
        for sec in outlets.sections():
            for key in outlets[sec]:
                self.outlets[key] = outlets[sec][key]



if __name__ == "__main__":
    pc = PowerControl("cfg/radio_codes.cfg", "cfg/outlets.cfg")
    print('Press Ctrl-C to quit.')
    try:
        while True:
            time.sleep(100)
            pass
    except KeyboardInterrupt:
        pc.stopAll()
