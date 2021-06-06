# Wrapper around paho mqtt using configparser for an easy configurable communication
# Author: Daniel Habering <daniel@habering.de>

import configparser
import json
from paho.mqtt import client as mqtt_client

class Comm:
    client = None
    connected = False
    topics = {}
    subscriptions = {}

    # Returns current connection status to broker
    def is_connected(self):
        return self.connected

    # Callback for mqtt, when client hast connected to broker
    def on_connect(self, client, userdata, flags, rc):
        self.connected = True

    # Callback for mqtt, when connection to broker has been lost
    # Reset connected flag
    def on_disconnect(self, userdata, rc):
        self.connected = False
        print("Connection to broker failed. Errorcode: " + str(rc))

    # Callback for mqtt, when any message has been received
    def on_message(self, client, userdata, msg):
        # Check if callback is available for received topic
        if msg.topic not in self.subscriptions:
            return

        # Message should be a valid json string, try to parse to dict
        try:
            msg_dict = json.loads(str(msg.payload.decode()))
        except json.decoder.JSONDecodeError as decode_error:
            print("Received invalid JSON string: " + str(msg.payload) + " with error " + str(decode_error))
            return

        # Pass dict to stored callback function
        self.subscriptions[msg.topic]["callback"](msg_dict)

    # Callback for mqtt, when subscription to a topic has been successfull
    def on_subscribe(self, client, userdata, mid, granted_qos):
        # Check for a pending subscription for this topic
        for topic, subscription in self.subscriptions.items():
            if subscription["mid"] == mid:
                # Update subscription status
                subscription["subscribed"] = True

    # To be called if a new subscription should be created. Upon successfull subscription, the passed callback will be called
    # for any message recieved on said topic
    # The provided topicId has to match an entry in the provided communication config
    def subscribe(self, topicId, callback):
        # Check if topicID is known from communication config
        if topicId not in self.topics:
            raise Exception("Topic " + str(topicId) + " can not be found under [Topics] in the provided config file")
        topic_string = self.topics[topicId]

        # Check if client is connected to broker
        if not self.connected:
            raise Exception("MQTT is not connected to broker, failed to subscribe to " + str(topic_string))

        # Subscribe to topic
        (result, mid) = self.client.subscribe(topic_string)
        if result != mqtt_client.MQTT_ERR_SUCCESS:
            raise Exception("Failed to subscribe to " + str(topic_string) + " with error " + str(result))

        # Store callback and subscription mid
        self.subscriptions[topic_string] = {"callback": callback, "mid": mid, "subscribed": False}

    # To be called to publish a msg to a given topicID
    # The provided topicId has to match an entry in the provided communication config
    # The msg has to be a valid JSON string or a dictionary
    def publish(self, topicId, msg):
        # Check if topic is known
        if topicId not in self.topics:
            raise Exception("Topic " + str(topicId) + " can not be found under [Topics] in the provided config file")
        topic_string = self.topics[topicId]

        # Check if client is connected to broker
        if not self.connected:
            raise Exception("MQTT is not connected to broker, failed to publish to topic")

        # Create json string from msg
        msg_string = ""
        if type(msg) is dict:
            # Create json string from dict
            msg_string = json.dumps(msg)
        elif type(msg) is str:
            # Check if msg is a valid json string
            try:
                json.loads(msg)
            except ValueError as error:
                print("Can only publish valid json strings: " + str(error))
                return
            msg_string = msg
        else:
            raise Exception("Comm.publish only takes dict or str")

        # Publish message on topic
        self.client.publish(topic_string, msg_string)

    # Read Broker config from config file
    def readBrokerConfigField(self, config, field):
        result = config["Broker"][field]

        if not result:
            raise Exception("Config file needs to contain a " + str(field) + " field under section [Broker]")

        return result

    def __init__(self, client_id, configfile = "cfg/comm.cfg"):
        config = configparser.ConfigParser()
        config.read(configfile)

        broker_ip = str(self.readBrokerConfigField(config, "ip"))
        broker_port = int(self.readBrokerConfigField(config, "port"))
        broker_username = str(self.readBrokerConfigField(config, "username"))
        broker_pw = str(self.readBrokerConfigField(config, "password"))

        if "Topics" not in config:
            raise Exception("Config file needs collection of topics under a section called [Topics]")

        for topic_id in config["Topics"]:
            self.topics[topic_id] = config["Topics"][topic_id]

        self.client = mqtt_client.Client(client_id)
        self.client.username_pw_set(broker_username, broker_pw)
        self.client.on_connect = self.on_connect
        #self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe

        try:
            self.client.connect(broker_ip, broker_port)
        except ConnectionRefusedError as err:
            raise Exception("Failed to connect to broker. Check that broker is running under " + str(broker_ip) + str(broker_port) + " and that username and pw are correct")

        self.client.loop_start()