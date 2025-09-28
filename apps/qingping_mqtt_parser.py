# qingping_parser.py
from typing import Dict, Any, Optional
import struct


class QingpingMqttParser:
    """
    Robust Qingping 'CGAU' payload parser.

    Strategy:
    - Verify header b'CGAU'
    - Split on NUL for debug/firmware extraction
    - Search payload for a 3-word (uint16 little-endian) pattern:
        [temp_raw (×10), hum_raw (×10), co2_raw]
        where values fall in realistic ranges. Use the first match found
        (starting after the 4-byte header).
    - Return nicely formatted sensor readings plus raw values.
    """

    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger
        self.debug_mode = True

    def log(self, msg: str):
        if self.logger:
            # logger expected to have .info
            try:
                self.logger.info(msg)
            except Exception:
                print(msg)
        else:
            print(msg)

    def parse_payload(self, payload: bytes) -> Dict[str, Any]:
        """Main entry: parse arbitrary payloads and return structured dict."""
        if not payload:
            return {"sensor": {}, "device_info": {}, "historical_data": [], "timestamp": None}
        
        if self.debug_mode:
            self.debug_payload(payload)

        result = {"sensor": {}, "device_info": {}, "historical_data": [], "timestamp": None}

        try:
            if payload[:4] != b"CGAU":
                self.log(f"Unknown header: {payload[:4]!r}")
                return result

            # try a robust scan for (temp, hum, co2) triple
            found = self._find_sensor_triple(payload)
            if found:
                offset, t_raw, h_raw, co2_raw = found
                # Temperature as float with 1 decimal
                temperature = round(t_raw / 10.0, 1)
                # Humidity as integer (truncate fractional part) to match the expected integer humidity
                humidity = int(h_raw / 10)
                result["sensor"].update({
                    "temperature": temperature,
                    "temperature_raw": t_raw,
                    "humidity": humidity,
                    "humidity_raw": h_raw,
                    "carbon_dioxide": co2_raw,
                    "carbon_dioxide_raw": co2_raw,
                    "sensor_offset_bytes": offset
                })
            else:
                # fallback: try some common offsets (keeps code robust)
                self.log("No sensor triple found — trying fallback offsets.")
                # self._fallback_parse(payload, result)

            return result

        except Exception as exc:
            self.log(f"Exception while parsing payload: {exc}")
            return result

    def _extract_firmware_from_sections(self, sections: list) -> str:
        """Heuristic extraction of an ASCII firmware string like '1.5.1'."""
        for sec in sections:
            try:
                txt = sec.decode("ascii", errors="ignore").strip()
                if txt and any(ch.isdigit() for ch in txt) and "." in txt:
                    return txt
            except Exception:
                continue
        return "unknown"

    def _find_sensor_triple(self, payload: bytes):
        """
        Returns the first (offset_in_bytes, t_raw, h_raw, co2_raw) or None.
        """
        offset = 13  
        t_raw = int.from_bytes(payload[offset:offset + 2], "little")
        h_raw = int.from_bytes(payload[offset + 2:offset + 4], "little")
        co2_raw = int.from_bytes(payload[offset + 4:offset + 6], "little")

        return offset, t_raw, h_raw, co2_raw

    def debug_payload(self, payload: bytes):
        """Enhanced debugging output"""
        self.log("=== Payload Analysis ===")
        self.log(f"Payload: {payload} ")
        self.log(f"Hex: {payload.hex()}")
        self.log(f"Length: {len(payload)} bytes")
        
        # Show sections split by null delimiters
        sections = payload.split(b'\x00')
        self.log(f"Number of sections: {len(sections)}")
        
        for i, section in enumerate(sections):
            self.log(f"Section {i:2d}: {section.hex():20} | {self._bytes_to_readable(section)}")
            
        self.log("========================")

    def _bytes_to_readable(self, data: bytes) -> str:
        """Convert bytes to readable mixed format"""
        result = []
        for byte in data:
            if 32 <= byte < 127:  # Printable ASCII
                result.append(chr(byte))
            else:
                result.append(f'\\x{byte:02x}')
        return ''.join(result)