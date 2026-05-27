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
n.add_commands["request_image"] = request_image
n.add_commands["request_info"] = request_info
n.add_commands["print_attention"] = print_attention

n.start_conn("/dev/ttyUSB0")

attention_messages = []
n.add_params["attention_messages"] = attention_messages
n.start_listen()

n.start_interactive()

index = -1
while True:
    time.sleep(1)
    with n.listener.storage.info_lock:
        for i, mes in enumerate(n.listener.storage.info_dict.values()):
            if i > index:
                if mes.text == "attention":
                    attention_messages.append(mes)
                if mes.json_data:
                    print(f"get object ({mes.msg_id}): {mes.json_data}")
                index = i
