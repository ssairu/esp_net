import time
from py_apps.NetNode import NetNode


def print_attention(net_node, attention_messages):
    for i, m in enumerate(attention_messages):
        print(f"{i}) sender_id: {m.sender_id}, msg_id: {m.msg_id}, save_time: {m.save_time}")


def request_image(net_node, attention_messages, num_att):
    if -1 < int(num_att) < len(attention_messages):
        m = attention_messages[int(num_att)]
        msg_id = net_node.send_info(dest_id=m.sender_id, cor_id=m.msg_id, is_request=True, text="image")
        print("request send")


def request_image_add(net_node, s_id, i_id):
    image_obj = net_node.listener.storage.image_builder.get_img_by_ids(int(s_id), int(i_id))
    if image_obj and not image_obj.isready():
        frags_mask = [True] * image_obj.num_frags
        for f in image_obj.frags:
            frags_mask[f.id] = False

        msg_id = net_node.send_info(
            dest_id=int(s_id),
            cor_id=0,
            is_request=True,
            bools=frags_mask,
            json={"i": int(i_id)}
        )
        print(f"request for add frags for image {i_id} send")


def request_info(net_node, attention_messages, num_att):
    if -1 < int(num_att) < len(attention_messages):
        m = attention_messages[int(num_att)]
        msg_id = net_node.send_info(
            dest_id=m.sender_id,
            cor_id=m.msg_id,
            is_request=True,
            text="info",
            json={"num_att": num_att}
        )
        print("request send")



n = NetNode(2)
n.add_commands["rim"] = request_image
n.add_commands["rin"] = request_info
n.add_commands["print_attention"] = print_attention
n.add_commands["rima"] = request_image_add

n.start_conn("/dev/ttyUSB0")
n.listener.storage.init_db()

attention_messages = []
n.add_params["attention_messages"] = attention_messages
n.start_listen()

n.start_interactive()
index = -1
images_times = {}

while True:
    time.sleep(1)
    with n.listener.storage.info_lock:
        for i, mes in enumerate(n.listener.storage.info_dict.values()):
            if i > index:
                if mes.text == "attention":
                    attention_messages.append(mes)
                if mes.json_data:
                    print(f"get object ({mes.msg_id}): {mes.json_data}")
                if mes.img_num:
                    images_times[(mes.sender_id, mes.img_num)] = time.time()
                    # print(images_times)
                index = i

