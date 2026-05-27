import serial
import cv2
import os
import numpy as np
import time
import threading
import json
from .Converter import Converter
from .InfoStorage import InfoStorage


class Listener:
    def __init__(self, listener_id, ser, message_callback=None, testing=False):
        self.testing = testing
        self.listener_id = listener_id
        self.ser = ser
        self.storage = InfoStorage()
        self.lock = threading.Lock()
        self.GETTING = False

    def get_frag(self, testing=False):
        start_flag = 0
        start_aim = '&$&'
        getting = self.GETTING

        while start_flag < 3:
            if self.ser.inWaiting() > 0:
                x = self.ser.read()
                with self.lock:
                    if not self.GETTING:
                        return
                try:
                    if str(x, 'utf-8') == start_aim[start_flag]:
                        start_flag += 1
                    else:
                        start_flag *= 0
                except UnicodeDecodeError:
                    print('в начале ошибка декодировки')
                    return

        if getting:
            c_main = Converter(4)
            c_small = Converter(2)
            c_byte = Converter(1)
            try:
                sender_id = c_main.bytes_to_int(self.ser.read(4))
                msg_id = c_main.bytes_to_int(self.ser.read(4))
                cor_id = c_main.bytes_to_int(self.ser.read(4))
                dest_id = c_main.bytes_to_int(self.ser.read(4))
                is_request, has_bools, has_json, has_text, has_image = c_byte.bytes_to_bools(self.ser.read(1))
            except UnicodeDecodeError:
                print('Ошибка получения фрагмента')
                return
            except ValueError:
                print('Ошибка расшифровки значений')
                return
            result = {
                "sender_id": sender_id,
                "msg_id": msg_id,
                "cor_id": cor_id,
                "dest_id": dest_id,
                "is_request": is_request,
                "has_bools": has_bools,
                "has_json": has_json,
                "has_text": has_text,
                "has_image": has_image,
                "bools": None,
                "json": None,
                "text": None,
                "image": None,
                "image_num": None,
                "fragment_id": None,
                "image_total_fragments": None,
                "image_width": None,
                "image_height": None,
            }
            if has_bools:
                try:
                    size_c_bytes = c_main.bytes_to_int(self.ser.read(4))
                    len_bools_bytes = c_main.bytes_to_int(self.ser.read(4))
                    bools_payload = self.ser.read(size=size_c_bytes)
                    bool_converter = Converter(size_c_bytes)
                    result["bools"] = bool_converter.bytes_to_bools(bools_payload)
                    if len(result["bools"]) != len_bools_bytes:
                        raise ValueError("May error in bools")
                except:
                    print("Ошибка в получении булевых значений")

            if has_json:
                try:
                    len_json = c_main.bytes_to_int(self.ser.read(4))
                    json_bytes = self.ser.read(size=len_json)
                    try:
                        result["json"] = json.loads(json_bytes.decode('utf-8'))
                    except Exception as e:
                        raise ValueError(f"JSON decode error: {e}")
                except:
                    print("Ошибка в получении JSON")

            if has_text:
                try:
                    len_text = c_main.bytes_to_int(self.ser.read(4))
                    text_bytes = self.ser.read(size=len_text)
                    result["text"] = text_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    print("Ошибка в получении текста")

            if has_image:
                try:
                    result["image_num"] = c_main.bytes_to_int(self.ser.read(4))
                    result["fragment_id"] = c_main.bytes_to_int(self.ser.read(4))
                    result["image_total_fragments"] = c_main.bytes_to_int(self.ser.read(4))
                    frag_size = c_main.bytes_to_int(self.ser.read(4))
                    result["image_width"] = c_small.bytes_to_int(self.ser.read(2))
                    result["image_height"] = c_small.bytes_to_int(self.ser.read(2))
                    result["image"] = self.ser.read(size=frag_size)
                except UnicodeDecodeError:
                    print('Ошибка получения изображения')
                    return

            ending = self.ser.read(3)

            end_aim = b'%@%'
            if not ending == end_aim:
                print('wrong not ending')
                return

            return result
        return

    def get_info(self, *, testing=False):
        print("-----------------------------------")
        # if directory_to_save:
        #     self.directory = directory_to_save
        #     os.chdir(self.directory)

        with self.lock:
            getting = self.GETTING

        while getting:
            res_frag = self.get_frag(testing=testing)
            if not res_frag:
                with self.lock:
                    getting = self.GETTING
                continue
            with self.lock:
                if res_frag["dest_id"] == 0 or res_frag["dest_id"] == self.listener_id:
                    self.storage.save_message(res_frag)

                getting = self.GETTING

