from collections import defaultdict
import serial
import cv2
import time
from .Converter import Converter
from .Frag import Frag
from .MainMessage import MessageEncoder


class Image:
    def __init__(self, data, shape, sender_id, img_id, max_size_frag=1700, fire_check=False, fire=False):
        self.id = img_id
        self.sender_id = sender_id
        self.fire_check = fire_check
        self.fire = fire
        self.max_size_frag = max_size_frag
        self.shape = shape
        if len(data) % self.max_size_frag == 0:
            self.num_frags = len(data) // self.max_size_frag
        else:
            self.num_frags = len(data) // self.max_size_frag + 1

        frags = []
        for i in range(self.num_frags):
            sizef = self.max_size_frag
            if i == self.num_frags - 1:
                sizef = len(data) - i * self.max_size_frag
            fragx = Frag(self.sender_id, self.id, i, data[i * self.max_size_frag: i * self.max_size_frag + sizef])
            frags += [fragx]
        self.frags = frags

    def tobytesFrags(self, dest_id=0, msg_id=None):
        bfrags = []
        for x in self.frags:
            me = MessageEncoder(self.sender_id)
            fragx, _ = me.encode(
                dest_id=dest_id,
                image_data=x.data,
                is_request=False,
                img_num=self.id,
                frag_id=x.id,
                total_frags=self.num_frags,
                image_width=self.shape[0],
                image_height=self.shape[1],
                msg_id=msg_id
            )
            bfrags.append(fragx)
        return bfrags


class Sender:
    crit_size = 50
    seed = int(time.time()) - 1779826143

    def __init__(self, sender_id, ser, default_speed=3000, default_max_frag_size=3000, testing=False):
        self.testing = testing
        self.sender_id = sender_id
        self.default_speed = default_speed
        self.default_max_frag_size = default_max_frag_size
        self.ser = ser
        self.img_num = int(time.time()) - 1779826143
        self.img_id_path_dict = defaultdict(int)

    def get_img_id(self, path=None):
        if not path:
            t = int(time.time()) - 1779826143
            self.img_num = t if t > self.img_num else self.img_num + 1
            return self.img_num
        elif path not in self.img_id_path_dict:
            t = int(time.time()) - 1779826143
            self.img_num = t if t > self.img_num else self.img_num + 1
            self.img_id_path_dict[path] = self.img_num
        return self.img_id_path_dict[path]

    def set_speed_default(self, speed):
        self.default_speed = speed

    def set_max_frag_size_default(self, size):
        self.default_max_frag_size = size

    def send_image_file(self, path, dest_id=0, msg_id=None, speed=None, max_frag_size=None) -> int:
        # Load the Image using OpenCV
        img = cv2.imread(path)
        return self.send_frame(
            img,
            dest_id=dest_id,
            msg_id=msg_id,
            path=path,
            speed=speed,
            max_frag_size=max_frag_size
        )

    def send_frame(self, img, dest_id=0, msg_id=None, path=None, speed=None, max_frag_size=None) -> int:
        if not speed:
            speed = self.default_speed
        if not max_frag_size:
            max_frag_size = self.default_max_frag_size

        img_id = self.get_img_id(path)
        if self.testing:
            print(f"Изображение \" {path} + \"")
            print(f"ID: {img_id}")
            print(f"Размер Ш*В*Г: {img.shape}")

        image = Image(img.tobytes(), img.shape, self.sender_id, img_id, max_frag_size)
        devided_image = image.tobytesFrags(dest_id=dest_id, msg_id=msg_id)
        counter = 0
        num_frags = len(devided_image)
        for x in devided_image:
            print(f"send_img {img_id}: {counter + 1} / {num_frags}", end="\r")
            counter += 1

            x1 = x.replace(b'\x00', b'\x01')
            if len(x1) % Sender.crit_size == 0:
                num = len(x1) // Sender.crit_size
            else:
                num = len(x1) // Sender.crit_size + 1

            sleep = Sender.crit_size / speed
            for i in range(num - 1):
                self.ser.write(x1[i * Sender.crit_size: (i + 1) * Sender.crit_size])
                time.sleep(sleep)

            self.ser.write(x1[(num - 1) * Sender.crit_size:])
        print("\n")

        return 0

    def send_info(self, text=None, bools=None, jsonify_object=None, dest_id=0, msg_id=None, cor_id=0, speed=None, is_request=False):
        if not speed:
            speed = self.default_speed

        me = MessageEncoder(self.sender_id)
        try:
            mes, msg_id = me.encode(
                dest_id=dest_id,
                is_request=is_request,
                msg_id=msg_id,
                cor_id=cor_id,
                bools=bools,
                json_data=jsonify_object,
                text=text
            )
        except Exception as e:
            print(f"cant encode error: {e}")
            return -1

        print(f"send message {msg_id}")

        num = len(mes) // Sender.crit_size + (0 if len(mes) % Sender.crit_size == 0 else 1)

        sleep = Sender.crit_size / speed
        for i in range(num - 1):
            self.ser.write(mes[i * Sender.crit_size: (i + 1) * Sender.crit_size])
            time.sleep(sleep)

        self.ser.write(mes[(num - 1) * Sender.crit_size:])
        return msg_id
