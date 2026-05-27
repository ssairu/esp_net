import time
from py_apps.NetNode import NetNode

n = NetNode(2)
n.start_conn("/dev/ttyUSB0")
# n.start_listen()
# time.sleep(2)
n.send_info(bools=[True, True, False, True, False], text="attention")
