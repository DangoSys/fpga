"""Load and byte-verify a complete Toy/OpenSBI/Linux payload in DDR.

Reset BTN0 and wait for LED0 (DDR calibration). Requires pyserial.
Example: python host/load.py --port COM5 build/board-software/fw_payload.bin
"""
import argparse
import binascii
import hashlib
from pathlib import Path
import struct
import sys
import time


def frame(op, sequence, address, length, data=b""):
    body=struct.pack("<BBIH",op,sequence,address,length)+data
    return b"\xa5\x5a"+body+struct.pack("<H",binascii.crc_hqx(body,0xffff))


class Loader:
    def __init__(self,port):
        self.port=port
        self.sequence=0

    def read_exact(self,count):
        data=bytearray()
        deadline=time.monotonic()+5
        while len(data)<count and time.monotonic()<deadline:
            data.extend(self.port.read(count-len(data)))
        if len(data)!=count:raise TimeoutError("Reply timeout; confirm LED0, reset BTN0, retry")
        return bytes(data)

    def request(self,op,address=0,length=0,data=b""):
        seq=self.sequence
        self.sequence=(seq+1)&255
        self.port.write(frame(op,seq,address,length,data));self.port.flush()
        header=self.read_exact(7)
        if header[:4]!=bytes((0x5a,0xa5,op|128,seq)):raise ValueError("Response header/sequence mismatch")
        size=struct.unpack_from("<H",header,5)[0]
        if size>256:raise ValueError("Invalid response size")
        payload=self.read_exact(size)
        checksum=struct.unpack("<H",self.read_exact(2))[0]
        if checksum!=binascii.crc_hqx(header[2:]+payload,0xffff):raise ValueError("Response CRC mismatch")
        if header[4]:raise RuntimeError(f"Loader rejected request: status={header[4]}")
        return payload


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",required=True)
    p.add_argument("binary",type=Path)
    p.add_argument("--baud",type=int,default=1000000)
    p.add_argument("--console-seconds",type=float,default=120)
    p.add_argument("--transcript",type=Path,default=Path("toy-console.log"))
    p.add_argument("--check-linux",action="store_true",help="Run the existing Linux system check after the shell prompt")
    args=p.parse_args()
    import serial
    data=args.binary.read_bytes()
    if not 0<len(data)<=268435456:raise ValueError("Payload must fit 256 MiB DDR, linked at 0x80000000")
    with serial.Serial(args.port,args.baud,timeout=.1,write_timeout=5,rtscts=False,dsrdtr=False) as port:
        port.reset_input_buffer()
        loader=Loader(port)
        info=loader.request(4)
        if len(info)!=12 or info[:4]!=b"TA7\x02":raise ValueError("Expected Toy DDR loader protocol v2")
        capacity,clock=struct.unpack_from("<II",info,4)
        if len(data)>capacity:raise ValueError("Image exceeds reported DDR capacity")
        print(f"DDR {capacity} bytes, core {clock} Hz, payload SHA256 {hashlib.sha256(data).hexdigest()}")
        started=time.monotonic()
        for offset in range(0,len(data),256):
            chunk=data[offset:offset+256]
            loader.request(1,0x80000000+offset,len(chunk),chunk)
            if loader.request(2,0x80000000+offset,len(chunk))!=chunk:
                raise RuntimeError(f"DDR readback mismatch at {offset:#x}; CPU remains reset")
            if offset%65536==0:print(f"Verified {offset+len(chunk)}/{len(data)} bytes",flush=True)
        loader.request(3,0x80000000)
        print(f"Full readback passed; CPU started after {time.monotonic()-started:.1f}s. Console:")
        deadline=time.monotonic()+args.console_seconds
        console=bytearray()
        command_sent=False
        linux_passed=False
        checks=(b"PASS VM_COPY_ON_WRITE",b"PASS VM_PAGE_PROTECTION",b"PASS FP64_PROCESS_CONTEXT",
                b"PASS LINUX_TIMER",b"PASS LINUX_SYSTEM_CHECK")
        with args.transcript.open("wb") as log:
            while time.monotonic()<deadline:
                block=port.read(4096)
                if block:
                    console.extend(block)
                    log.write(block);log.flush()
                    sys.stdout.write(block.decode("utf-8",errors="replace"));sys.stdout.flush()
                    if args.check_linux and not command_sent and b"~ # " in console:
                        # One short command fits the tested 256-byte receive FIFO.
                        port.write(b"/root/linux_system_check-linux\n");port.flush()
                        command_sent=True
                    if command_sent and all(marker in console for marker in checks):
                        linux_passed=True
                        break
        print(f"\nSaved console to {args.transcript}")
        if args.check_linux and not linux_passed:
            raise RuntimeError("Linux acceptance markers missing; inspect the saved console")


if __name__=="__main__":
    main()
