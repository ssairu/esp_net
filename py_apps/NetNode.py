import inspect

from .Listener import Listener
from .Sender import Sender
import serial
import threading
import time
import numpy as np
import sys
import copy


class NetNode:
    def __init__(self, node_id, testing=False):
        self.testing = testing
        self.node_id = node_id
        self.request_dict = {}
        self.port = None
        self.ser = None
        self.lock = threading.Lock()
        self.request_lock = threading.Lock()
        self.listener = None
        self.sender = None
        self.thread_do_commands = None
        self.thread_get_commands = None
        self.thread_get_messages = None
        self.commands = []
        self.add_commands = {}  # str: function
        self.add_params = {}

    def start_conn(self, port, baudrate=115200):
        self.port = port
        self.ser = serial.Serial(self.port)
        self.ser.baudrate = baudrate
        self.listener = Listener(self.node_id, self.ser)
        self.sender = Sender(self.node_id, self.ser)
        return True, None

    def stop_conn(self):
        self.ser.close()

    def update_conn(self, new_port=None, new_baudrate=115200):
        self.stop_conn()
        self.start_conn(new_port, new_baudrate)

    def start_listen(self):
        if self.listener.ser:
            if self.thread_get_messages is not None and self.thread_get_messages.is_alive():
                print('\n reading already started \n')
            else:
                with self.listener.lock:
                    self.listener.GETTING = True
                self.thread_get_messages = threading.Thread(target=self.listener.get_info, kwargs={'testing': True})
                self.thread_get_messages.start()

    def stop_listen(self):
        with self.listener.lock:
            self.listener.GETTING = False
        self.thread_get_messages.join()
        print('\n\n reading stopped \n\n')

    def send_image(self, path, dest_id=0, msg_id=None, speed=None, max_frag_size=None, frags_mask=None):
        return self.sender.send_image_file(path, dest_id, msg_id, speed, max_frag_size, frags_mask)

    def send_info(self, text=None, bools=None, json=None, dest_id=0, msg_id=None, cor_id=0, speed=None, is_request=False, max_attempts=1, retry_time=10):
        msg_id = self.sender.send_info(text, bools, json, dest_id, msg_id, cor_id, speed, is_request)
        msg_info = ((text, bools, json, dest_id, msg_id, cor_id, speed, is_request), max_attempts, retry_time)
        if is_request:
            with self.request_lock:
                self.request_dict[msg_id] = time.time(), 1, msg_info
        return msg_id

    def get_commands(self):
        while True:
            command = sys.stdin.readline().strip()
            command, params = command.split("+")[0], command.split("+")[1:] if len(command.split("+")) > 1 else []
            params = {x.split(":")[0]: x.split(":")[1] for x in params}
            print(f"\nget command: '{command}' with params {params}\n")
            with self.lock:  # Блокируем доступ к общему ресурсу commands
                self.commands.append((command, params))

    def worker(self, command):
        if command[0] in ('stop_listen', 'stol'):
            self.stop_listen()

        elif command[0] in ('start_listen', 'stal'):
            self.start_listen()

        elif command[0] in ('save_images', 'si'):
            self.listener.storage.save_all_images()

        elif command[0] in self.add_commands.keys():
            print(f"start {command}")
            valid_params = {}
            func = self.add_commands[command[0]]
            signature = inspect.signature(func)
            for p in signature.parameters.keys():
                if p == "net_node":
                    valid_params["net_node"] = self
                elif p in self.add_params:
                    valid_params[p] = self.add_params[p]
                elif p in command[1]:
                    valid_params[p] = command[1][p]
                else:
                    print(f"не найден параметр {p}")
                    return
            func(**valid_params)
            print(f"good end {command}")

    def do_commands(self):
        index = -1
        while True:
            time.sleep(0.5)
            for m_id, (last_time, made_attempts, (msg_info, max_attempts, retry_time)) in copy.deepcopy(self.request_dict).items():
                with self.request_lock:
                    if last_time + retry_time < time.time() and made_attempts < max_attempts:
                        print("retry: ", end="")
                        msg_id = self.sender.send_info(*msg_info)
                        self.request_dict[msg_id] = time.time(), made_attempts+1, (msg_info, max_attempts, retry_time)
                    elif last_time + retry_time < time.time() and made_attempts >= max_attempts:
                        if m_id in self.request_dict:
                            del self.request_dict[m_id]
                            print(f"ERROR: Can't reach any request answer for msg_id: {m_id}; attempts: {made_attempts}")
                    if m_id in [x.cor_id for x in self.listener.storage.info_dict.values()]:
                        if m_id in self.request_dict:
                            del self.request_dict[m_id]
                            print(f"get ok for msg_id: {m_id}")

            for i, x in enumerate(self.listener.storage.info_dict.values()):
                if i > index and x.is_request:
                    print(f"send ok for msg_id: {x.msg_id}")
                    self.sender.send_info(dest_id=x.sender_id, cor_id=x.msg_id)
                    index = i

            with self.lock:
                if len(self.commands) == 0:
                    continue

            while self.commands:
                with self.lock:
                    command = self.commands[0]
                self.worker(command)
                with self.lock:
                    self.commands = self.commands[1:]

    def start_interactive(self):
        self.thread_do_commands = threading.Thread(target=self.do_commands)
        self.thread_do_commands.start()

        self.thread_get_commands = threading.Thread(target=self.get_commands)
        self.thread_get_commands.start()



