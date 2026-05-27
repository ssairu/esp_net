import time
import json
from typing import Optional, List, Dict, Any
from .Converter import Converter


class MessageEncoder:
    START = b"&$&"
    END = b"%@%"

    def __init__(self, sender_id: int):
        self.sender_id = sender_id

        self.c_main = Converter(4)
        self.c_small = Converter(2)
        self.c_byte = Converter(1)

        self._last_msg_id = 0

    def generate_msg_id(self) -> int:
        now_us = int(time.time() * 10) - 1779732182_0  # ~2020-01-01
        candidate = now_us & 0xFFFFFFFF
        if candidate <= self._last_msg_id:
            self._last_msg_id += 1
            return self._last_msg_id
        self._last_msg_id = candidate
        return candidate

    def encode(
        self,
        dest_id: int,
        bools: Optional[List[bool]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        image_data: Optional[bytes] = None,
        is_request: bool = False,
        img_num: int = 0,
        frag_id: int = 0,
        total_frags: int = 1,
        image_width: int = 0,
        image_height: int = 0,
        msg_id: Optional[int] = None,
        cor_id: int = 0,
    ) -> (bytes, int):
        if msg_id is None:
            msg_id = self.generate_msg_id()
        else:
            # если задан вручную — используем, но обновляем кэш
            self._last_msg_id = max(self._last_msg_id, msg_id)

        flags_byte = self.c_byte.bools_to_bytes([
            is_request,
            bools and len(bools) > 0,
            json_data is not None,
            text is not None and text,
            image_data is not None
        ])

        parts = []

        # 1. bools
        if bools and len(bools) > 0:
            size_c = max(1, (len(bools) + 5) // 8)
            bool_converter = Converter(size=size_c)  # минимум 2 байта + запас
            bools_bytes = bool_converter.bools_to_bytes(bools)
            len_bools = self.c_main.int_to_bytes(len(bools))
            size_c_bytes = self.c_main.int_to_bytes(size_c)
            parts.append(size_c_bytes + len_bools + bools_bytes)

        # 2. json
        if json_data is not None:
            json_str = json.dumps(json_data, ensure_ascii=False, separators=(',', ':'))
            json_bytes = json_str.encode('utf-8')
            len_json = self.c_main.int_to_bytes(len(json_bytes))
            parts.append(len_json + json_bytes)

        # 3. text
        if text:
            text_bytes = text.encode('utf-8')
            len_text = self.c_main.int_to_bytes(len(text_bytes))
            parts.append(len_text + text_bytes)

        # 4. image
        if image_data:
            img_header = (
                self.c_main.int_to_bytes(img_num) +
                self.c_main.int_to_bytes(frag_id) +
                self.c_main.int_to_bytes(total_frags) +
                self.c_main.int_to_bytes(len(image_data)) +
                self.c_small.int_to_bytes(image_width) +
                self.c_small.int_to_bytes(image_height)
            )
            parts.append(img_header)
            parts.append(image_data)

        payload = b''.join(parts)

        header = (
            self.START +
            self.c_main.int_to_bytes(self.sender_id) +
            self.c_main.int_to_bytes(msg_id) +
            self.c_main.int_to_bytes(cor_id) +
            self.c_main.int_to_bytes(dest_id) +
            flags_byte
        )

        return header + payload + self.END, msg_id


class MessageDecoder:
    START = b"&$&"
    END = b"%@%"

    def __init__(self):
        self.c_main = Converter(4)
        self.c_small = Converter(2)
        self.c_byte = Converter(1)

    def decode(self, data: bytes) -> dict:
        if not data.startswith(self.START) or not data.endswith(self.END):
            raise ValueError("Invalid message boundaries")

        body = data[len(self.START):-len(self.END)]

        min_header_len = 4 * self.c_main.size + self.c_byte.size
        if len(body) < min_header_len:
            raise ValueError("Message too short for header")

        offset = 0

        sender_id = self.c_main.bytes_to_int(body[offset:offset + self.c_main.size])
        offset += self.c_main.size

        msg_id = self.c_main.bytes_to_int(body[offset:offset + self.c_main.size])
        offset += self.c_main.size

        cor_id = self.c_main.bytes_to_int(body[offset:offset + self.c_main.size])
        offset += self.c_main.size

        dest_id = self.c_main.bytes_to_int(body[offset:offset + self.c_main.size])
        offset += self.c_main.size

        is_request, has_bools, has_json, has_text, has_image = self.c_byte.bytes_to_bools(body[offset:offset + self.c_byte.size])
        offset += self.c_byte.size

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

        # bools
        if result["has_bools"]:
            if offset + 2*self.c_main.size > len(body):
                raise ValueError("Not enough data for bools length")
            size_c_bytes = self.c_main.bytes_to_int(body[offset:offset + self.c_main.size])
            offset += self.c_main.size
            len_bools_bytes = self.c_main.bytes_to_int(body[offset:offset + self.c_main.size])
            offset += self.c_main.size

            if offset + size_c_bytes > len(body):
                raise ValueError("Not enough data for bools payload")
            bools_payload = body[offset:offset + size_c_bytes]
            offset += size_c_bytes

            bool_converter = Converter(size_c_bytes)
            result["bools"] = bool_converter.bytes_to_bools(bools_payload)
            if len(result["bools"]) != len_bools_bytes:
                raise ValueError("May error in bools")

        # json
        if result["has_json"]:
            if offset + self.c_main.size > len(body):
                raise ValueError("Not enough data for json length")
            len_json = self.c_main.bytes_to_int(body[offset:offset + self.c_main.size])
            offset += self.c_main.size

            if offset + len_json > len(body):
                raise ValueError("Not enough data for json")
            json_bytes = body[offset:offset + len_json]
            offset += len_json

            try:
                result["json"] = json.loads(json_bytes.decode('utf-8'))
            except Exception as e:
                raise ValueError(f"JSON decode error: {e}")

        # text
        if result["has_text"]:
            if offset + self.c_main.size > len(body):
                raise ValueError("Not enough data for text length")
            len_text = self.c_main.bytes_to_int(body[offset:offset + self.c_main.size])
            offset += self.c_main.size

            if offset + len_text > len(body):
                raise ValueError("Not enough data for text")
            text_bytes = body[offset:offset + len_text]
            offset += len_text

            try:
                result["text"] = text_bytes.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError("Text decode error (not valid UTF-8)")

        # image
        if result["has_image"]:
            need = (self.c_main.size * 4 +          # frag_size + total_size
                    self.c_small.size * 2)          # w + h
            if offset + need > len(body):
                raise ValueError("Not enough data for image fragment header")

            result["image_num"] = self.c_main.bytes_to_int(
                body[offset:offset + self.c_main.size])
            offset += self.c_main.size

            result["fragment_id"] = self.c_main.bytes_to_int(
                body[offset:offset + self.c_main.size])
            offset += self.c_main.size

            result["image_total_fragments"] = self.c_main.bytes_to_int(
                body[offset:offset + self.c_main.size])
            offset += self.c_main.size

            frag_size = self.c_main.bytes_to_int(
                body[offset:offset + self.c_main.size])
            offset += self.c_main.size

            result["image_width"] = self.c_small.bytes_to_int(
                body[offset:offset + self.c_small.size])
            offset += self.c_small.size

            result["image_height"] = self.c_small.bytes_to_int(
                body[offset:offset + self.c_small.size])
            offset += self.c_small.size

            if offset + frag_size > len(body):
                raise ValueError("Not enough data for image payload")

            result["image"] = body[offset:offset + frag_size]
            offset += frag_size  # конец

        if offset != len(body):
            raise ValueError(f"Extra {len(body)-offset} bytes after parsing")

        return result

