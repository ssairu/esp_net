import time
import os
from py_apps.NetNode import NetNode


folder_path = "/home/user/code/esp_net/примеры"
n = NetNode(1)
n.start_conn("/dev/ttyUSB0")
n.start_listen()

msg_img_dict = {}

for root, dirs, files in os.walk(folder_path):
    for file in files:
        time.sleep(0.5)
        if file.lower().split(".")[-1] in ("png", "jpeg", "jpg"):
            msg_id = n.send_info(text="attention")
            if msg_id > -1:
                msg_img_dict[msg_id] = os.path.join(root, file)

index = -1
while True:
    time.sleep(2.5)
    need_imges = []
    with n.listener.storage.info_lock:
        for i, mes in enumerate(n.listener.storage.info_dict.values()):
            print(i, index, mes.is_request, mes.cor_id, msg_img_dict)
            if i > index and mes.is_request and mes.cor_id in msg_img_dict:
                need_imges.append((msg_img_dict[mes.cor_id], mes.sender_id))
                index = i
    print(need_imges)
    for p in need_imges:
        n.send_image(p[0], dest_id=p[1])
