import argparse



def get_bytes(num, byts):
    if num == 2:
        result = bytes([byts[0], byts[1]])
        # print(byts[0])
        # print(byts[1])
        # print(result)
        return result
    elif num == 3:
        result = bytes([byts[0], byts[1], byts[2]])
        # print(byts[0])
        # print(byts[1])
        # print(byts[2])
        # print(result)
        return result
    elif num == 4:
        result = bytes([byts[0], byts[1], byts[2], byts[3]])
        # print(byts[0])
        # print(byts[1])
        # print(byts[2])
        # print(byts[3])
        # print(result)
        return result


def encode(codepoint):
    if codepoint < 128:
        return bytes([codepoint])

    bit_length = codepoint.bit_length()
    byts = []
    num_bytes = 0

    if bit_length >= 8:
        if codepoint <= 2047:
            byts.append(0xC0 | (codepoint >> 6) & 0x1F)
            byts.append(0x80 | codepoint & 0x3F)
            num_bytes = 2
        elif codepoint <= 65535:
            byts.append(0xE0 | (codepoint >> 12) & 0x0F)
            byts.append(0x80 | (codepoint >> 6) & 0x3F)
            byts.append(0x80 | codepoint & 0x3F)
            num_bytes = 3
        elif codepoint <= 1114111:
            byts.append(0xF0 | (codepoint >> 18) & 0x07)
            byts.append(0x80 | (codepoint >> 12) & 0x3F)
            byts.append(0x80 | (codepoint >> 6) & 0x3F)
            byts.append(0x80 | codepoint & 0x3F)
            num_bytes = 4

    return get_bytes(num_bytes,byts)

def decode(bytes_object):

    byts = []

    if len(bytes_object) == 1:
        return bytes_object[0]

    elif len(bytes_object) == 2:

        y_mask = 0b00011111
        x_mask = 0b00111111

        y_bits = (bytes_object[0] & y_mask) << 6
        x_bits = bytes_object[1] & x_mask

        return y_bits | x_bits

    elif len(bytes_object) == 3:

        x_mask = 0b00001111
        y_mask = 0b00111111

        byte1 = (bytes_object[0] & x_mask) << 12
        byte2 = (bytes_object[1] & y_mask) << 6
        byte3 = (bytes_object[2] & y_mask)

        return byte1 | byte2 | byte3

    elif len(bytes_object) == 4:

        x_mask = 0b00000111
        y_mask = 0b00111111

        byte1 = (bytes_object[0] & x_mask) << 18
        byte2 = (bytes_object[1] & y_mask) << 12
        byte3 = (bytes_object[2] & y_mask) << 6
        byte4 = (bytes_object[3] & y_mask)

        return byte1 | byte2 | byte3 | byte4



def main():
    pass


if __name__ == '__main__':
    main()
