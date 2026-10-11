"""Observe autonomous Flash/Linux startup, including an optional USB power cycle."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
import time

CHECKS = (
    b"PASS VM_COPY_ON_WRITE",
    b"PASS VM_PAGE_PROTECTION",
    b"PASS FP64_PROCESS_CONTEXT",
    b"PASS LINUX_TIMER",
    b"PASS LINUX_SYSTEM_CHECK",
)


class Observer:
    def __init__(self, port, transcript, timeout=600, require_disconnect=False):
        self.port = port
        self.transcript = Path(transcript)
        self.timeout = timeout
        self.require_disconnect = require_disconnect
        self.result = None
        self.disconnections = 0
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        import serial

        deadline = time.monotonic() + self.timeout
        started = time.monotonic()
        active = not self.require_disconnect
        data = bytearray()
        sent = False
        connection = None
        self.transcript.parent.mkdir(parents=True, exist_ok=True)
        with self.transcript.open("wb") as log:
            try:
                while time.monotonic() < deadline and not self.stop.is_set():
                    try:
                        if connection is None:
                            connection = serial.Serial(
                                self.port,
                                1000000,
                                timeout=0.1,
                                write_timeout=5,
                                rtscts=False,
                                dsrdtr=False,
                            )
                            connection.reset_input_buffer()
                            self.ready.set()
                        chunk = connection.read(max(1, connection.in_waiting))
                        if not chunk:
                            continue
                        log.write(chunk)
                        log.flush()
                        if not active:
                            continue
                        data.extend(chunk)
                        if b"FAIL FLASH_BOOT" in data or b"Kernel panic" in data:
                            raise RuntimeError(
                                "Flash startup or Linux failed; inspect the UART log"
                            )
                        if (
                            not sent
                            and b"PASS FLASH_PAYLOAD_CRC" in data
                            and b"OpenSBI" in data
                            and b"~ # " in data
                        ):
                            connection.write(
                                b"/root/linux_system_check-linux; echo FLASH_LINUX_RC:$?\n"
                            )
                            connection.flush()
                            sent = True
                            print("FLASH_LINUX_CHECK_SENT", flush=True)
                        if (
                            sent
                            and re.search(rb"(?:^|\n)FLASH_LINUX_RC:0\r*\n", data)
                            and all(m in data for m in CHECKS)
                        ):
                            self.result = dict(
                                result="PASS_FLASH_LINUX",
                                checks=[m.decode() for m in CHECKS],
                                exit_status=0,
                                usb_disconnections=self.disconnections,
                                disconnect_required=self.require_disconnect,
                                elapsed_seconds=round(time.monotonic() - started, 3),
                                recorded_at=datetime.now(timezone.utc).isoformat(),
                                port=self.port,
                                transcript=str(self.transcript),
                            )
                            print("PASS FLASH_LINUX_UART_CHECKS", flush=True)
                            break
                    except (serial.SerialException, OSError):
                        if connection is not None:
                            connection.close()
                            connection = None
                            self.disconnections += 1
                            active = True
                            data.clear()
                            sent = False
                            log.write(b"\nOBSERVER_USB_DISCONNECTED\n")
                            log.flush()
                            print("OBSERVER_USB_DISCONNECTED", flush=True)
                        self.stop.wait(0.2)
                if self.result is None:
                    raise TimeoutError(
                        "No complete autonomous Flash/Linux pass before the timeout"
                    )
            except Exception as error:
                self.result = dict(
                    result="FAILED",
                    error=str(error),
                    usb_disconnections=self.disconnections,
                    port=self.port,
                )
            finally:
                if connection is not None:
                    connection.close()
        self.transcript.with_suffix(".json").write_text(
            json.dumps(self.result, indent=2) + "\n"
        )

    def start(self):
        self.thread.start()
        if not self.ready.wait(timeout=5):
            self.stop.set()
            self.thread.join(timeout=6)
            raise RuntimeError(f"Could not open UART {self.port}; observer not armed")

    def finish(self):
        self.thread.join()
        if not self.result or self.result["result"] != "PASS_FLASH_LINUX":
            raise RuntimeError(self.result)
        return self.result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--transcript", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument(
        "--require-disconnect",
        action="store_true",
        help="Ignore the current session; wait for USB removal and a new boot",
    )
    args = p.parse_args()
    watcher = Observer(
        args.port, args.transcript, args.timeout, args.require_disconnect
    )
    watcher.start()
    print("OBSERVER_ARMED", flush=True)
    print(json.dumps(watcher.finish(), indent=2))


if __name__ == "__main__":
    main()
