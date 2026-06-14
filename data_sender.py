import time
import os
from py_apps.NetNode import NetNode

folder_path = "/home/user/code/esp_net/examples"
n = NetNode(1)
n.start_conn("/dev/ttyUSB1")
n.start_listen()
n.start_interactive()

msg_img_dict = {}

def send_attention_for_image(net_node, fn, msg_img_dict):
    if os.path.isfile(fn):
        msg_id = net_node.send_info(text="attention")
        if msg_id > -1:
            msg_img_dict[msg_id] = fn


n.add_commands["att"] = send_attention_for_image
n.add_params["msg_img_dict"] = msg_img_dict



for root, dirs, files in os.walk(folder_path):
    for file in files:
        time.sleep(0.5)
        if file.lower().split(".")[-1] in ("png", "jpeg", "jpg"):
            msg_id = n.send_info(text="attention", is_request=True, max_attempts=2)
            if msg_id > -1:
                msg_img_dict[msg_id] = os.path.join(root, file)

index = -1
while True:
    time.sleep(2.5)
    need_imges = []
    with n.listener.storage.info_lock:
        for i, mes in enumerate(n.listener.storage.info_dict.values()):
            if i > index:
                if mes.is_request:
                    if mes.text == "image" and mes.cor_id in msg_img_dict:
                        print(f"image_request for {mes.cor_id}")
                        need_imges.append((msg_img_dict[mes.cor_id], mes.sender_id, None))
                    elif mes.text == "info" and mes.cor_id in msg_img_dict:
                        print(f"info_request for {mes.cor_id}")
                        n.send_info(
                            json={
                                "request_att": mes.json_data["num_att"],
                                "filepath": msg_img_dict[mes.cor_id],
                                "time": str(time.time()),
                                "geo": {"lat": 45.123, "lon": 60.123}
                            },
                            bools=[False, False, False, True, True, True, False, False, False]
                        )
                    elif mes.json_data and mes.bools:
                        path_id_dict = {v: n.sender.get_img_id(v) for v in msg_img_dict.values()}
                        for p, id_p in path_id_dict.items():
                            if mes.json_data.get("i") == id_p:
                                need_imges.append((p, mes.sender_id, mes.bools))
                index = i
    if need_imges:
        print(need_imges)
    for p in need_imges:
        n.send_image(p[0], dest_id=p[1], frags_mask=p[2])
