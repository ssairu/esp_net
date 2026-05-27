class Converter:
    def __init__(self, size=4):
        self.size = size

    def int_to_bytes(self, num):
        res = b''
        for i in range(self.size):
            ost = num % 255 + 1
            res = ost.to_bytes(1, "big") + res
            num = num // 255
        return res

    def bytes_to_int(self, bint):
        mem = memoryview(bint)
        res = 0
        power = 1
        for i in range(self.size):
            res += (mem[self.size - i - 1] - 1) * power
            power *= 255
        return res

    def bools_to_bytes(self, bools):
        if len(bools) > 8 * self.size - 2:
            print("cannot convert bools to bytes, please use bigger base")
            return
        res = 1 << len(bools)
        for i in range(len(bools)):
            if bools[i]:
                res = res | (1 << i)

        return self.int_to_bytes(res)

    def bytes_to_bools(self, bbools):
        x = self.bytes_to_int(bbools)
        start = self.size * 8 - 1
        check = False
        res = ()

        while start >= 0:
            if check:
                res = (True,) + res if (x >> start) & 1 else (False,) + res
            elif (x >> start) == 1:
                check = True
            start -= 1
        #print(res)
        return res

if __name__=="__main__":
    c = Converter(1)
    x = c.bools_to_bytes([True, False, False, False, False, False])
    print(c.bytes_to_bools(x))
