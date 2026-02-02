#!/usr/bin/env python3
"""
ELM327 Emulator for Mock OBD-II System

Emulates an ELM327 Bluetooth adapter over TCP socket.
Bridges between ELM327 AT commands and raw CAN (vcan0).
Allows testing OBD-II apps against the mock ECU.

Usage:
    python elm327_emulator.py [--host HOST] [--port PORT]

Connect your app to: <server-ip>:35000
"""

import socket
import threading
import time
import can
import argparse
from typing import Optional
from lib.isotp import ISOTPHandler, ISOTPConfig


class ELM327Emulator:
    """ELM327 adapter emulator that bridges to CAN bus"""

    # ELM327 protocol parameters
    VERSION = "ELM327 v1.5"
    DEVICE_ID = "MockOBD"

    # CAN IDs for OBD-II
    REQUEST_ID = 0x7E0
    RESPONSE_ID = 0x7E8

    def __init__(self, can_interface='vcan0'):
        self.can_interface = can_interface
        self.bus: Optional[can.Bus] = None
        self.isotp: Optional[ISOTPHandler] = None
        self.protocol = "6"  # ISO 15765-4 CAN (11 bit ID, 500 kbaud)
        self.echo_on = True
        self.headers_on = False
        self.spaces_on = True
        self.linefeed_on = True
        self.timeout = 2.0  # Response timeout in seconds (increased for multi-frame)

    def connect_can(self):
        """Connect to CAN bus"""
        try:
            self.bus = can.Bus(interface='socketcan', channel=self.can_interface)
            self.isotp = ISOTPHandler(self.bus, self.REQUEST_ID, self.RESPONSE_ID, ISOTPConfig())
            print(f"[ELM327] Connected to {self.can_interface} with ISO-TP multi-frame support")
            return True
        except Exception as e:
            print(f"[ELM327] Failed to connect to CAN: {e}")
            return False

    def disconnect_can(self):
        """Disconnect from CAN bus"""
        if self.bus:
            self.bus.shutdown()
            self.bus = None

    def format_response(self, text: str) -> str:
        """Format response with proper line endings"""
        if self.linefeed_on:
            return text + "\r\n"
        else:
            return text + "\r"

    def process_at_command(self, cmd: str) -> str:
        """Process ELM327 AT command and return response"""
        cmd = cmd.strip().upper()

        # Device info commands
        if cmd == "ATZ":  # Reset
            self.echo_on = True
            self.headers_on = False
            self.spaces_on = True
            return self.format_response(f"{self.VERSION}\r\n>")

        elif cmd == "AT@1":  # Device description
            return self.format_response(self.DEVICE_ID)

        elif cmd == "ATI":  # Version ID
            return self.format_response(self.VERSION)

        # Echo control
        elif cmd == "ATE0":
            self.echo_on = False
            return self.format_response("OK")

        elif cmd == "ATE1":
            self.echo_on = True
            return self.format_response("OK")

        # Linefeed control
        elif cmd == "ATL0":
            self.linefeed_on = False
            return self.format_response("OK")

        elif cmd == "ATL1":
            self.linefeed_on = True
            return self.format_response("OK")

        # Spaces control
        elif cmd == "ATS0":
            self.spaces_on = False
            return self.format_response("OK")

        elif cmd == "ATS1":
            self.spaces_on = True
            return self.format_response("OK")

        # Headers control
        elif cmd == "ATH0":
            self.headers_on = False
            return self.format_response("OK")

        elif cmd == "ATH1":
            self.headers_on = True
            return self.format_response("OK")

        # Protocol selection
        elif cmd.startswith("ATSP"):
            self.protocol = cmd[4:] if len(cmd) > 4 else "6"
            return self.format_response("OK")

        elif cmd == "ATTP":  # Try protocol (auto)
            return self.format_response("OK")

        elif cmd == "ATDP":  # Describe protocol
            return self.format_response(f"AUTO, ISO 15765-4 (CAN 11/500)")

        # Memory/settings
        elif cmd == "ATAT0" or cmd == "ATAT1" or cmd == "ATAT2":  # Adaptive timing
            return self.format_response("OK")

        elif cmd.startswith("ATST"):  # Set timeout
            return self.format_response("OK")

        elif cmd == "ATWS":  # Warm start
            return self.format_response("OK")

        # Default for unknown AT commands
        elif cmd.startswith("AT"):
            return self.format_response("OK")

        else:
            return self.format_response("?")

    def send_obd_request(self, obd_bytes: bytes) -> Optional[str]:
        """Send OBD request over CAN and wait for response (handles multi-frame)"""
        if not self.bus or not self.isotp:
            return None

        try:
            # Send request using ISO-TP (handles multi-frame automatically)
            success = self.isotp.send(obd_bytes)
            if not success:
                return self.format_response("BUS ERROR")

            # Wait for response (may be multi-frame)
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                msg = self.bus.recv(timeout=0.1)

                if msg and msg.arbitration_id == self.RESPONSE_ID:
                    # Use ISO-TP to receive (handles multi-frame reassembly)
                    payload = self.isotp.receive_frame(msg)

                    if payload is not None:
                        # Complete message received
                        return self.format_can_response(msg.arbitration_id, payload)
                    # else: waiting for more frames, continue loop

            # Timeout
            return self.format_response("NO DATA")

        except Exception as e:
            print(f"[ELM327] Error sending request: {e}")
            return self.format_response("BUS ERROR")

    def format_can_response(self, can_id: int, payload: bytes) -> str:
        """Format CAN response as ELM327 string"""
        hex_bytes = [f"{b:02X}" for b in payload]

        if self.headers_on:
            header = f"{can_id:03X}"
            if self.spaces_on:
                return self.format_response(f"{header} {' '.join(hex_bytes)}")
            else:
                return self.format_response(f"{header}{''.join(hex_bytes)}")
        else:
            if self.spaces_on:
                return self.format_response(' '.join(hex_bytes))
            else:
                return self.format_response(''.join(hex_bytes))

    def process_obd_command(self, cmd: str) -> str:
        """Process OBD-II request (hex string like '01 0C')"""
        try:
            # Remove spaces and convert hex string to bytes
            hex_str = cmd.strip().replace(' ', '')
            obd_bytes = bytes.fromhex(hex_str)

            # Send request and get response
            response = self.send_obd_request(obd_bytes)
            if response:
                return response
            else:
                return self.format_response("NO DATA")

        except ValueError:
            return self.format_response("?")
        except Exception as e:
            print(f"[ELM327] Error processing OBD command: {e}")
            return self.format_response("ERROR")

    def handle_client(self, conn: socket.socket, addr):
        """Handle client connection"""
        print(f"[ELM327] Client connected: {addr}")

        # Send initial prompt
        conn.sendall(b"ELM327 v1.5\r\n\r\n>")

        buffer = ""

        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break

                buffer += data.decode('ascii', errors='ignore')

                # Process commands line by line
                while '\r' in buffer or '\n' in buffer:
                    # Split on first CR or LF
                    if '\r' in buffer:
                        line, buffer = buffer.split('\r', 1)
                    else:
                        line, buffer = buffer.split('\n', 1)

                    # Remove leading newline if present
                    buffer = buffer.lstrip('\n')

                    if not line.strip():
                        conn.sendall(b">")
                        continue

                    # Echo command if enabled
                    if self.echo_on:
                        conn.sendall((line + "\r").encode())

                    # Process command
                    if line.upper().startswith("AT"):
                        response = self.process_at_command(line)
                    else:
                        response = self.process_obd_command(line)

                    # Send response
                    conn.sendall(response.encode())

                    # Send prompt
                    conn.sendall(b">")

        except Exception as e:
            print(f"[ELM327] Client error: {e}")

        finally:
            conn.close()
            print(f"[ELM327] Client disconnected: {addr}")


def main():
    parser = argparse.ArgumentParser(description='ELM327 OBD-II Adapter Emulator')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=35000, help='Port to listen on (default: 35000)')
    parser.add_argument('--can-interface', default='vcan0', help='CAN interface (default: vcan0)')
    args = parser.parse_args()

    emulator = ELM327Emulator(can_interface=args.can_interface)

    # Connect to CAN bus
    if not emulator.connect_can():
        print("Failed to connect to CAN bus. Exiting.")
        return

    # Create TCP server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(5)

    print(f"[ELM327] Listening on {args.host}:{args.port}")
    print(f"[ELM327] Configure your app to connect to: {args.host}:{args.port}")
    print("[ELM327] Press Ctrl+C to stop")

    try:
        while True:
            conn, addr = server.accept()
            # Handle each client in a separate thread
            client_thread = threading.Thread(target=emulator.handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()

    except KeyboardInterrupt:
        print("\n[ELM327] Shutting down...")

    finally:
        server.close()
        emulator.disconnect_can()


if __name__ == '__main__':
    main()
