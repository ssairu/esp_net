class Frag:
    def __init__(self, sender_id, img_id, frag_id, data):
        self.sender_id = sender_id
        self.img_id = img_id
        self.id = frag_id
        self.size = len(data)
        self.data = data

    def __eq__(self, other):
        return (self.img_id == other.img_id and
                self.id == other.id and
                self.sender_id == other.sender_id)

    def print(self):
        print('[ sender_id = ')
        print(self.sender_id)
        print('\n  img_id = ')
        print(self.img_id)
        print('\n  id = ')
        print(self.id)
        print('\n  size = ')
        print(self.size)
        print('\n  data = ')
        print(self.data)
        print(' ]\n')