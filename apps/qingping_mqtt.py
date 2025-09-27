import appdaemon.plugins.hass.hassapi as hass
import paho.mqtt.client as mqtt
import threading
from qingping_mqtt_parser import QingpingMqttParser
from qingping_device import QingpingDevice

class QingpingMQTT(hass.Hass):
    def initialize(self):
        self.devices = {}
        self.log("Starting Qingping MQTT parser with corrected parsing")
        
        self.parser = QingpingMqttParser(logger=self)

        mqtt_host = self.args.get("mqtt_host", "core-mosquitto")
        mqtt_port = self.args.get("mqtt_port", 1883)
        mqtt_username = self.args.get("mqtt_username")
        mqtt_password = self.args.get("mqtt_password")
        mqtt_topic = self.args.get("mqtt_topic", "qingping/+/up")

        self.log(f"Connecting to MQTT broker at {mqtt_host}:{mqtt_port}, topic: {mqtt_topic}")

        self.mqtt_client = mqtt.Client()
        if mqtt_username and mqtt_password:
            self.mqtt_client.username_pw_set(mqtt_username, mqtt_password)
            self.log("MQTT authentication credentials set")

        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        self.thread = threading.Thread(
            target=self.mqtt_loop, args=(mqtt_host, mqtt_port)
        )
        self.thread.daemon = True
        self.thread.start()
    
    def mqtt_loop(self, mqtt_host, mqtt_port):
        try:
            self.mqtt_client.connect(mqtt_host, mqtt_port, 60)
            self.mqtt_client.loop_forever()
        except Exception as e:
            self.log(f"MQTT error: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log("Successfully connected to MQTT broker")
            topic = self.args.get("mqtt_topic", "qingping/+/up")
            client.subscribe(topic)
        else:
            self.log(f"Failed to connect to MQTT broker with code: {rc}")
            
    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload
            
            self.log(f"Received MQTT message from {msg.topic}")

            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 2:
                addr = topic_parts[1]
            else:
                addr = "unknown"
            
            parsed_data = self.parser.parse_payload(payload)
            
            self.log(f"Parsed data for {addr}: {parsed_data}")

            if addr not in self.devices:
                self.devices[addr] = QingpingDevice(self, addr)
                self.log(f"Created new Qingping device: {addr}")
            
            self.devices[addr].update_from_mqtt(parsed_data)
            self.log(f"Updated device {addr}")

        except Exception as e:
            self.log(f"Error processing MQTT message: {e}")

    def terminate(self):
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.disconnect()
        self.log("Qingping MQTT parser stopped")