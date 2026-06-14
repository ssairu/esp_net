from typing import List, Dict, Any
from .ImageBuilder import ImageBuilder
from .database import NetDatabase
from dataclasses import dataclass
from .Frag import Frag
from datetime import datetime
import cv2
import numpy as np
import time
import os
import threading


@dataclass
class Message:
    sender_id: int
    msg_id: int
    cor_id: int
    dest_id: int
    is_request: bool

    bools: List[bool]
    json_data: Dict[str, Any]
    text: str

    img_num: int
    frag_id: int

    save_time: datetime


class InfoStorage:
    def __init__(self, save_db=False):
        self.db = NetDatabase("netnode.db") if save_db else None
        self.save_db = save_db
        self.image_builder = ImageBuilder()
        self.info_dict = {}
        self.directory = ''
        self.lock = threading.Lock()
        self.info_lock = threading.Lock()

    def init_db(self, db_name="netnode.db"):
        self.db = NetDatabase(db_name)
        self.save_db = True

    def save_message(self, parsed_message_dict, save_db=False):
        mes = Message(
            parsed_message_dict["sender_id"],
            parsed_message_dict["msg_id"],
            parsed_message_dict["cor_id"],
            parsed_message_dict["dest_id"],
            parsed_message_dict["is_request"],
            parsed_message_dict["bools"],
            parsed_message_dict["json"],
            parsed_message_dict["text"],
            parsed_message_dict["image_num"],
            parsed_message_dict["fragment_id"],
            datetime.now(),
        )

        if (mes.sender_id, mes.msg_id) in self.info_dict:
            return

        image_id = None

        if parsed_message_dict.get("has_image"):
            if save_db or self.save_db:
                image_id = self.db.create_or_update_image(
                    sender_id=parsed_message_dict["sender_id"],
                    image_num=parsed_message_dict["image_num"],
                    total_fragments=parsed_message_dict.get("image_total_fragments"),
                    width=parsed_message_dict.get("image_width"),
                    height=parsed_message_dict.get("image_height")
                )

            # Добавляем фрагмент в ImageBuilder
            frag = Frag(
                parsed_message_dict["sender_id"],
                parsed_message_dict["image_num"],
                parsed_message_dict["fragment_id"],
                parsed_message_dict["image"]
            )
            with self.lock:
                self.image_builder.add_frag(
                    frag,
                    parsed_message_dict["image_total_fragments"],
                    (parsed_message_dict["image_width"],
                     parsed_message_dict["image_height"],
                     3)
                )
        else:
            print(f"(get_info_msg) sender_id: {mes.sender_id}, msg_id: {mes.msg_id}, time: {mes.save_time}")

        if save_db or self.save_db:
            try:
                self.db.save_message(mes, image_id=image_id)
            except Exception as e:
                print(f"Ошибка сохранения сообщения в БД: {e}")

        with self.info_lock:
            self.info_dict[(mes.sender_id, mes.msg_id)] = mes

    def get_image(self, sender_id, image_num):
        with self.lock:
            img = self.image_builder.get_img_by_ids(sender_id, image_num)
            if not img:
                print(f'изображение не найдено для sender_id: {sender_id}, image_num: {image_num}')
                return

            response = img.getimgdata(not_ready=True)
            if not response:
                return
            res = np.frombuffer(response, dtype=np.uint8).reshape(img.shape)
            return res, len(img.frags) * 100 / img.num_frags

    def get_last_sender_img(self, sender_id):
        with self.lock:
            imgs = self.image_builder.get_imgs_by_sender(sender_id)
            if imgs:
                return imgs[0]

    def _save_image(self, img, save_db=False):
        try:
            response = img.getimgdata(not_ready=True)
            if not response:
                return False

            res = np.frombuffer(response, dtype=np.uint8).reshape(img.shape)

            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(img.img_id + 1779826143))
            filename = f"{img.sender_id}_{timestamp}.jpg"
            filepath = os.path.join(self.directory, filename)

            cv2.imwrite(filepath, res)
            if save_db or self.save_db:
                self.db.update_image_after_save(
                    sender_id=img.sender_id,
                    image_num=img.img_id,
                    file_path=filepath
                )
            print(f"Изображение сохранено: {filepath}")
            return True

        except Exception as e:
            print(f"Ошибка сохранения изображения: {e}")
            return False

    def save_all_images(self, directory_to_save='', save_to_db: bool = False):
        if directory_to_save:
            self.directory = directory_to_save
            os.makedirs(self.directory, exist_ok=True)
            os.chdir(self.directory)

        with self.lock:
            count = 0
            for img in self.image_builder.images:
                if self._save_image(img, save_to_db):
                    count += 1
            print(f"Сохранено изображений: {count}")

    def save_all_sender_imgs(self, sender_id: int, directory_to_save='', save_to_db: bool = True):
        if directory_to_save:
            self.directory = directory_to_save
            os.makedirs(self.directory, exist_ok=True)
            os.chdir(self.directory)

        with self.lock:
            imgs = self.image_builder.get_imgs_by_sender(sender_id)
            count = 0
            for img in imgs:
                if self._save_image(img, save_to_db):
                    count += 1
            print(f"Сохранено изображений от sender_id={sender_id}: {count}")
    #
    # def save_all_images(self, directory_to_save=''):
    #     if directory_to_save:
    #         self.directory = directory_to_save
    #         os.chdir(self.directory)
    #     with self.lock:
    #         for img in self.image_builder.images:
    #             response = img.getimgdata(not_ready=True)
    #             if not response:
    #                 continue
    #             res = np.frombuffer(response, dtype=np.uint8).reshape(img.shape)
    #             filename = f'{img.sender_id}_{time.ctime(img.img_id + 1779826143)}_copy.jpg'
    #             print(f"save {filename} at {os.curdir}")
    #             cv2.imwrite(filename, res)
    #
    # def save_all_sender_imgs(self, sender_id, directory_to_save=''):
    #     if directory_to_save:
    #         self.directory = directory_to_save
    #         os.chdir(self.directory)
    #
    #     with self.lock:
    #         imgs = self.image_builder.get_imgs_by_sender(sender_id)
    #         for img in imgs:
    #             response = img.getimgdata(not_ready=True)
    #             if not response:
    #                 continue
    #             res = np.frombuffer(response, dtype=np.uint8).reshape(img.shape)
    #             filename = f'{img.sender_id}_{time.ctime(img.img_id + 1779826143)}_copy.jpg'
    #             print(f"save {filename} at {os.curdir}")
    #             cv2.imwrite(filename, res)
