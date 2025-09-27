from datetime import datetime
from typing import Dict, Any

class QingpingDevice:
    """Qingping device representation."""
    
    def __init__(self, handler, addr: str) -> None:
        self.handler = handler
        self.addr = addr
        self.data = None
        self.sensors_created = False
        self.sensor_entities = {}
        self.last_update = None

    def update_from_mqtt(self, data: Dict[str, Any]) -> None:
        """Update device data from MQTT message."""
        self.data = data
        self.last_update = datetime.now()
        
        if not self.sensors_created:
            self.create_sensors()
        
        self.update_sensors()

    def create_sensors(self):
        """Create Home Assistant sensors for this device."""
        device_name = f"Qingping {self.addr}"
        device_id = f"qingping_{self.addr.lower()}"
        
        device_config = {
            "identifiers": [f"qingping_{self.addr}"],
            "name": device_name,
            "manufacturer": "Qingping",
            "model": "Qingping Sensor",
        }
        
        sensors = [
            {
                "entity_id": f"sensor.{device_id}_temperature",
                "name": f"{device_name} Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "key": "temperature"
            },
            {
                "entity_id": f"sensor.{device_id}_humidity", 
                "name": f"{device_name} Humidity",
                "device_class": "humidity",
                "unit_of_measurement": "%",
                "key": "humidity"
            },
            {
                "entity_id": f"sensor.{device_id}_co2",
                "name": f"{device_name} CO2",
                "device_class": "carbon_dioxide", 
                "unit_of_measurement": "ppm",
                "key": "co2_ppm"
            },
            {
                "entity_id": f"sensor.{device_id}_battery",
                "name": f"{device_name} Battery",
                "device_class": "battery",
                "unit_of_measurement": "%",
                "key": "battery"
            }
        ]
        
        for sensor in sensors:
            self.handler.set_state(
                sensor["entity_id"],
                state="unknown",
                attributes={
                    "friendly_name": sensor["name"],
                    "device_class": sensor["device_class"],
                    "unit_of_measurement": sensor["unit_of_measurement"],
                    "device": device_config
                }
            )
            self.sensor_entities[sensor["key"]] = sensor["entity_id"]
        
        self.sensors_created = True
        self.handler.log(f"Created sensors for Qingping device {self.addr}")

    def update_sensors(self):
        """Update sensor values in Home Assistant."""
        if not self.data or 'sensor' not in self.data:
            return
            
        sensor_data = self.data['sensor']
        
        for key, entity_id in self.sensor_entities.items():
            if key in sensor_data and sensor_data[key] is not None:
                value = sensor_data[key]
                
                if key in ['temperature', 'humidity']:
                    value = round(value, 1)
                
                self.handler.set_state(
                    entity_id,
                    state=value,
                    attributes={
                        "friendly_name": f"Qingping {self.addr} {key.title()}",
                        "device_class": key,
                        "unit_of_measurement": self.get_unit(key),
                        "last_updated": self.last_update.isoformat() if self.last_update else datetime.now().isoformat()
                    }
                )

    def get_unit(self, key: str) -> str:
        units = {
            'temperature': '°C',
            'humidity': '%',
            'co2_ppm': 'ppm',
            'battery': '%'
        }
        return units.get(key, '')

    def __str__(self):
        if self.data and 'sensor' in self.data:
            sensor = self.data['sensor']
            return f"Qingping {self.addr} - Temp: {sensor.get('temperature', 0):.1f}°C, Humidity: {sensor.get('humidity', 0):.1f}%, CO2: {sensor.get('co2_ppm', 0)}ppm, Battery: {sensor.get('battery', 0)}%"
        return f"Qingping {self.addr} - No data"
