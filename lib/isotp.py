"""
ISO-TP (ISO 15765-2) Protocol Implementation

Handles single-frame and multi-frame CAN message transmission/reception
with flow control as per ISO 15765-2 standard.

Frame Types:
- Single Frame (SF):  PCI = 0x0N where N = data length (0-7 bytes)
- First Frame (FF):   PCI = 0x1N LL where NLL = total data length (8-4095 bytes)
- Consecutive Frame (CF): PCI = 0x2N where N = sequence number (0-15, wraps)
- Flow Control (FC): PCI = 0x30-0x32 (Continue/Wait/Overflow)
"""

import can
import time
import threading
from enum import Enum
from typing import Optional, List, Callable
from dataclasses import dataclass


class FrameType(Enum):
    """ISO-TP frame types"""
    SINGLE_FRAME = 0x00
    FIRST_FRAME = 0x10
    CONSECUTIVE_FRAME = 0x20
    FLOW_CONTROL = 0x30


class FlowStatus(Enum):
    """Flow control status values"""
    CONTINUE_TO_SEND = 0x00  # CTS
    WAIT = 0x01
    OVERFLOW = 0x02


@dataclass
class ISOTPConfig:
    """ISO-TP configuration parameters"""
    stmin: int = 0  # Minimum separation time between consecutive frames (ms)
    block_size: int = 0  # Number of CF frames before requiring FC (0 = no limit)
    timeout_ms: int = 1000  # Timeout for receiving frames (ms)
    padding: bool = True  # Pad frames to 8 bytes

class ISOTPFrame:
    """Base class for ISO-TP frames"""

    @staticmethod
    def parse(data: bytes) -> tuple[FrameType, bytes]:
        """Parse CAN data and return frame type and payload"""
        if len(data) == 0:
            raise ValueError("Empty frame data")

        pci_byte = data[0]
        frame_type_nibble = pci_byte & 0xF0

        if frame_type_nibble == 0x00:  # Single Frame
            length = pci_byte & 0x0F
            return (FrameType.SINGLE_FRAME, data[1:1+length])

        elif frame_type_nibble == 0x10:  # First Frame
            # Length is 12 bits: 4 bits from first byte, 8 bits from second byte
            length = ((pci_byte & 0x0F) << 8) | data[1]
            return (FrameType.FIRST_FRAME, data[2:])

        elif frame_type_nibble == 0x20:  # Consecutive Frame
            seq_num = pci_byte & 0x0F
            return (FrameType.CONSECUTIVE_FRAME, data[1:])

        elif frame_type_nibble == 0x30:  # Flow Control
            flow_status = pci_byte & 0x0F
            return (FrameType.FLOW_CONTROL, data[1:3])  # block_size, STmin

        else:
            raise ValueError(f"Unknown frame type: 0x{pci_byte:02X}")

    @staticmethod
    def create_single_frame(data: bytes, padding: bool = True) -> bytes:
        """Create single frame (data length must be ≤7 bytes)"""
        if len(data) > 7:
            raise ValueError(f"Single frame data too long: {len(data)} bytes")

        pci = 0x00 | len(data)
        frame = bytes([pci]) + data

        if padding and len(frame) < 8:
            frame += bytes([0x00] * (8 - len(frame)))

        return frame

    @staticmethod
    def create_first_frame(total_length: int, data: bytes, padding: bool = True) -> bytes:
        """Create first frame (total_length is full payload length)"""
        if total_length > 4095:
            raise ValueError(f"Payload too long for ISO-TP: {total_length} bytes")

        # PCI: 0x1N LL where N+LL = 12-bit length
        pci_high = 0x10 | ((total_length >> 8) & 0x0F)
        pci_low = total_length & 0xFF

        frame = bytes([pci_high, pci_low]) + data[:6]  # 6 bytes of data in FF

        if padding and len(frame) < 8:
            frame += bytes([0x00] * (8 - len(frame)))

        return frame

    @staticmethod
    def create_consecutive_frame(seq_num: int, data: bytes, padding: bool = True) -> bytes:
        """Create consecutive frame (seq_num wraps 0-15)"""
        pci = 0x20 | (seq_num & 0x0F)
        frame = bytes([pci]) + data[:7]  # 7 bytes of data in CF

        if padding and len(frame) < 8:
            frame += bytes([0x00] * (8 - len(frame)))

        return frame

    @staticmethod
    def create_flow_control(flow_status: FlowStatus, block_size: int = 0,
                          stmin: int = 0, padding: bool = True) -> bytes:
        """Create flow control frame"""
        pci = 0x30 | flow_status.value
        frame = bytes([pci, block_size & 0xFF, stmin & 0xFF])

        if padding and len(frame) < 8:
            frame += bytes([0x00] * (8 - len(frame)))

        return frame


class ISOTPSender:
    """Handles ISO-TP message transmission with multi-frame support"""

    def __init__(self, bus: can.Bus, tx_id: int, rx_id: int, config: Optional[ISOTPConfig] = None):
        """
        Initialize ISO-TP sender

        Args:
            bus: CAN bus instance
            tx_id: CAN ID for sending
            rx_id: CAN ID for receiving flow control
            config: ISO-TP configuration
        """
        self.bus = bus
        self.tx_id = tx_id
        self.rx_id = rx_id
        self.config = config or ISOTPConfig()

    def send(self, payload: bytes) -> bool:
        """
        Send payload using ISO-TP protocol

        Returns True on success, False on failure
        """
        if len(payload) <= 7:
            # Single frame
            return self._send_single_frame(payload)
        else:
            # Multi-frame
            return self._send_multi_frame(payload)

    def _send_single_frame(self, payload: bytes) -> bool:
        """Send single frame message"""
        try:
            frame_data = ISOTPFrame.create_single_frame(payload, self.config.padding)
            msg = can.Message(
                arbitration_id=self.tx_id,
                data=frame_data,
                is_extended_id=False
            )
            self.bus.send(msg)
            return True
        except Exception as e:
            print(f"[ISO-TP] Error sending single frame: {e}")
            return False

    def _send_multi_frame(self, payload: bytes) -> bool:
        """Send multi-frame message with flow control"""
        try:
            # Send first frame
            ff_data = ISOTPFrame.create_first_frame(len(payload), payload[:6], self.config.padding)
            msg = can.Message(
                arbitration_id=self.tx_id,
                data=ff_data,
                is_extended_id=False
            )
            self.bus.send(msg)

            # Wait for flow control
            fc_received = self._wait_for_flow_control()
            if not fc_received:
                print("[ISO-TP] No flow control received")
                return False

            # Send consecutive frames
            remaining = payload[6:]
            seq_num = 1
            offset = 0

            while offset < len(remaining):
                chunk = remaining[offset:offset+7]
                cf_data = ISOTPFrame.create_consecutive_frame(seq_num, chunk, self.config.padding)

                msg = can.Message(
                    arbitration_id=self.tx_id,
                    data=cf_data,
                    is_extended_id=False
                )
                self.bus.send(msg)

                # Increment sequence number (wraps at 16)
                seq_num = (seq_num + 1) % 16
                offset += 7

                # Apply separation time
                if self.config.stmin > 0:
                    time.sleep(self.config.stmin / 1000.0)

            return True

        except Exception as e:
            print(f"[ISO-TP] Error sending multi-frame: {e}")
            return False

    def _wait_for_flow_control(self) -> bool:
        """Wait for flow control frame"""
        start_time = time.time()
        timeout = self.config.timeout_ms / 1000.0

        while time.time() - start_time < timeout:
            msg = self.bus.recv(timeout=0.1)

            if msg and msg.arbitration_id == self.rx_id:
                try:
                    frame_type, data = ISOTPFrame.parse(bytes(msg.data))

                    if frame_type == FrameType.FLOW_CONTROL:
                        flow_status = data[0] if len(data) > 0 else FlowStatus.CONTINUE_TO_SEND.value

                        if flow_status == FlowStatus.CONTINUE_TO_SEND.value:
                            return True
                        elif flow_status == FlowStatus.WAIT.value:
                            continue  # Keep waiting
                        else:  # Overflow
                            print("[ISO-TP] Flow control overflow")
                            return False

                except Exception as e:
                    print(f"[ISO-TP] Error parsing flow control: {e}")
                    continue

        return False


class ISOTPReceiver:
    """Handles ISO-TP message reception with multi-frame reassembly"""

    def __init__(self, bus: can.Bus, tx_id: int, rx_id: int, config: Optional[ISOTPConfig] = None):
        """
        Initialize ISO-TP receiver

        Args:
            bus: CAN bus instance
            tx_id: CAN ID for sending flow control
            rx_id: CAN ID for receiving
            config: ISO-TP configuration
        """
        self.bus = bus
        self.tx_id = tx_id
        self.rx_id = rx_id
        self.config = config or ISOTPConfig()

        # Multi-frame reception state
        self.receiving = False
        self.expected_length = 0
        self.received_data = bytearray()
        self.next_seq_num = 1
        self.last_frame_time = 0

    def receive_frame(self, msg: can.Message) -> Optional[bytes]:
        """
        Process incoming CAN frame

        Returns:
            Complete payload if message is complete, None if waiting for more frames
        """
        if msg.arbitration_id != self.rx_id:
            return None

        try:
            frame_type, data = ISOTPFrame.parse(bytes(msg.data))

            if frame_type == FrameType.SINGLE_FRAME:
                return self._handle_single_frame(data)

            elif frame_type == FrameType.FIRST_FRAME:
                return self._handle_first_frame(data, bytes(msg.data))

            elif frame_type == FrameType.CONSECUTIVE_FRAME:
                return self._handle_consecutive_frame(data, bytes(msg.data))

            else:
                return None

        except Exception as e:
            print(f"[ISO-TP] Error receiving frame: {e}")
            self._reset_reception()
            return None

    def _handle_single_frame(self, data: bytes) -> bytes:
        """Handle single frame reception"""
        self._reset_reception()
        return data

    def _handle_first_frame(self, data: bytes, raw_frame: bytes) -> Optional[bytes]:
        """Handle first frame reception"""
        # Extract total length from PCI bytes
        pci_high = raw_frame[0]
        pci_low = raw_frame[1]
        self.expected_length = ((pci_high & 0x0F) << 8) | pci_low

        # Store first 6 bytes of data
        self.received_data = bytearray(data[:6])
        self.next_seq_num = 1
        self.receiving = True
        self.last_frame_time = time.time()

        # Send flow control
        self._send_flow_control(FlowStatus.CONTINUE_TO_SEND)

        return None  # Waiting for more frames

    def _handle_consecutive_frame(self, data: bytes, raw_frame: bytes) -> Optional[bytes]:
        """Handle consecutive frame reception"""
        if not self.receiving:
            return None

        # Check timeout
        if time.time() - self.last_frame_time > self.config.timeout_ms / 1000.0:
            print("[ISO-TP] Reception timeout")
            self._reset_reception()
            return None

        # Check sequence number
        seq_num = raw_frame[0] & 0x0F
        if seq_num != self.next_seq_num:
            print(f"[ISO-TP] Sequence error: expected {self.next_seq_num}, got {seq_num}")
            self._reset_reception()
            return None

        # Add data
        remaining = self.expected_length - len(self.received_data)
        chunk_size = min(7, remaining)
        self.received_data.extend(data[:chunk_size])

        # Update state
        self.next_seq_num = (self.next_seq_num + 1) % 16
        self.last_frame_time = time.time()

        # Check if complete
        if len(self.received_data) >= self.expected_length:
            payload = bytes(self.received_data[:self.expected_length])
            self._reset_reception()
            return payload

        return None  # Waiting for more frames

    def _send_flow_control(self, flow_status: FlowStatus):
        """Send flow control frame"""
        try:
            fc_data = ISOTPFrame.create_flow_control(
                flow_status,
                self.config.block_size,
                self.config.stmin,
                self.config.padding
            )
            msg = can.Message(
                arbitration_id=self.tx_id,
                data=fc_data,
                is_extended_id=False
            )
            self.bus.send(msg)
        except Exception as e:
            print(f"[ISO-TP] Error sending flow control: {e}")

    def _reset_reception(self):
        """Reset multi-frame reception state"""
        self.receiving = False
        self.expected_length = 0
        self.received_data = bytearray()
        self.next_seq_num = 1
        self.last_frame_time = 0


class ISOTPHandler:
    """Combined ISO-TP sender and receiver for bidirectional communication"""

    def __init__(self, bus: can.Bus, tx_id: int, rx_id: int, config: Optional[ISOTPConfig] = None):
        """
        Initialize ISO-TP handler

        Args:
            bus: CAN bus instance
            tx_id: CAN ID for transmission
            rx_id: CAN ID for reception
            config: ISO-TP configuration
        """
        self.sender = ISOTPSender(bus, tx_id, rx_id, config)
        self.receiver = ISOTPReceiver(bus, tx_id, rx_id, config)

    def send(self, payload: bytes) -> bool:
        """Send payload using ISO-TP protocol"""
        return self.sender.send(payload)

    def receive_frame(self, msg: can.Message) -> Optional[bytes]:
        """Process incoming frame and return complete payload if ready"""
        return self.receiver.receive_frame(msg)

    def is_receiving(self) -> bool:
        """Check if currently receiving a multi-frame message"""
        return self.receiver.receiving
