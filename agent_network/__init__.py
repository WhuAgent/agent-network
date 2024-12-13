from agent_network.main import network
import signal
from posix import _exit


def signal_handler(sig, frame):
    network.release()
    _exit(0)


signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # kill
