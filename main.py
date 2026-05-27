from py_apps.InfoStorage import InfoStorage
from py_apps.MainMessage import MessageEncoder, MessageDecoder
from py_apps.NetNode import NetNode

e = MessageEncoder(1)
mes = e.encode(0, bools=[True, True, False, True, False], text="hello.jpeg")
print(mes)

d = MessageDecoder()
print(d.decode(mes[0]))

n = NetNode(1)
n.start_conn("/dev/ttyUSB0")
n.send_image("/home/user/img_predicted.jpg")

