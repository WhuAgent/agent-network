import signal
from os import _exit
from agent_network.constant import network


def signal_handler(sig, frame):
    network.release()
    _exit(0)


signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # kill
