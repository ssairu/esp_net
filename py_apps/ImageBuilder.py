class Imgforbuilder:
    def __init__(self, sender_id, img_id, num_frags, shape):
        self.img_id = img_id
        self.sender_id = sender_id
        self.frags = []
        self.num_frags = num_frags
        self.ready = False
        self.shape = shape

    def __eq__(self, other):
        return (self.img_id == other.img_id and
                self.sender_id == other.sender_id)

    def eq_frag(self, frag):
        return (self.img_id == frag.img_id and
                self.sender_id == frag.sender_id)

    def add_frag(self, frag):
        if self.ready:
            print('cannot add frag because all frags have been got')
            return False
        for x in self.frags:
            if frag.id == x.id:
                print('the same frag tried to add')
                return False
        self.frags += [frag]
        if self.isready():
            self.ready = True
        return True

    def isready(self):
        return len(self.frags) == self.num_frags

    def sort_frags(self):
        N = len(self.frags)
        for i in range(N - 1):
            for j in range(N - 1 - i):
                if self.frags[j].id > self.frags[j + 1].id:
                    self.frags[j], self.frags[j + 1] = self.frags[j + 1], self.frags[j]

    def rgb565_to_rgb888_bytes(self, input_bytes, width, height, endian='big'):
        """
        Преобразует байтовую строку RGB565 в байтовую строку RGB888.
        :param input_bytes: bytes, входной буфер RGB565 (2 байта на пиксель)
        :param width: ширина изображения в пикселях
        :param height: высота изображения в пикселях
        :param endian: порядок байтов ('big' или 'little') для RGB565
        :return: bytes, выходной буфер RGB888 (3 байта на пиксель)
        """
        if len(input_bytes) != width * height * 2:
            input_bytes = input_bytes[:width * height * 2]

        output_bytes = bytearray(width * height * 3)

        for i in range(width * height):
            # Читаем 2 байта пикселя
            offset = i * 2
            if endian == 'big':
                pixel = (input_bytes[offset] << 8) | input_bytes[offset + 1]
            else:
                pixel = (input_bytes[offset + 1] << 8) | input_bytes[offset]

            # Извлекаем R, G, B
            r = (pixel >> 11) & 0x1F  # 5 бит красного (0–31)
            g = (pixel >> 5) & 0x3F  # 6 бит зелёного (0–63)
            b = pixel & 0x1F  # 5 бит синего (0–31)

            # Масштабируем в 8 бит
            r = (r * 255) // 31  # 0–31 → 0–255
            g = (g * 255) // 63  # 0–63 → 0–255
            b = (b * 255) // 31  # 0–31 → 0–255

            # Записываем в выходной буфер
            output_offset = i * 3
            output_bytes[output_offset] = b
            output_bytes[output_offset + 1] = g
            output_bytes[output_offset + 2] = r

        return bytes(output_bytes)

    def getimgdata(self, not_ready=False):
        if not self.isready():
            if not_ready:
                self.sort_frags()
                data = b''
                k = 0
                for i in range(self.num_frags):
                    if k < len(self.frags) and self.frags[k].id == i:
                        data += self.frags[k].data
                        k += 1
                    else:
                        data += b'\1' * self.frags[0].size
                data = data[: self.shape[0] * self.shape[1] * 3]
                if len(data) // self.shape[0] // self.shape[1] == 2:
                    data = self.rgb565_to_rgb888_bytes(data, self.shape[0], self.shape[1])
                return data
            else:
                print('cannot get img because it is not full')
                return
        else:
            self.sort_frags()
            data = b''
            for f in self.frags:
                data += f.data
            if len(data) // self.shape[0] // self.shape[1] == 2:
                data = self.rgb565_to_rgb888_bytes(data, self.shape[0], self.shape[1])
            return data


class ImageBuilder:
    def __init__(self):
        self.images = []

    def img_in_load(self, frag):
        for x in self.images:
            if x.eq_frag(frag) and not x.isready():
                return True
        return False

    def img_is_ready(self, frag):
        for x in self.images:
            if x.eq_frag(frag) and x.isready():
                return True
        return False

    def get_img_pos(self, frag):
        res = -1
        for i in range(len(self.images)):
            if self.images[i].eq_frag(frag):
                res = i
        return res

    def add_frag(self, frag, num_fragments, img_shape):
        if not self.img_in_load(frag) and not self.img_is_ready(frag):
            self.images += [Imgforbuilder(frag.sender_id, frag.img_id, num_fragments, img_shape)]
            print("add Image " + str(frag.img_id) + "to builder")
            print("Frag added " + str(frag.id) + "\nfrags:")
            print(len(self.images[-1].frags))

        ipos = self.get_img_pos(frag)
        self.images[ipos].add_frag(frag)
        print(str(frag.id+1) + " / " + str(self.images[ipos].num_frags) + "total(" + str(len(self.images[ipos].frags)) + ")", end="\r")
        if frag.id + 1 == self.images[ipos].num_frags:
            print("\n")

    def get_img_by_frag(self, frag):
        ipos = self.get_img_pos(frag)
        return self.images[ipos] if ipos >= 0 else None

    def get_img_by_ids(self, sender_id, img_num):
        for x in self.images:
            if x.sender_id == sender_id and x.img_id == img_num:
                return x

    def get_imgs_by_sender(self, sender_id):
        res = []
        for x in self.images:
            if x.sender_id == sender_id:
                res.append(x)

        res.sort(key=lambda x: -x.img_id)
        return res


