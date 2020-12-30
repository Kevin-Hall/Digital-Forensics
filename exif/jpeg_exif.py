import sys
from tags import TAGS
from struct import unpack

class Exif(object):

    def init(__self__):
        pass

def carve(f, start, end):
    # return the bytes

    all_bytes = f.read()
    exif_bytes = all_bytes[start:end + 1]

    return exif_bytes


def find_jfif(f, max_length=None):
    # do some stuff

    soi = b'\xff\xd8'
    eoi = b'\xff\xd9'

    data = f.read(1)

    s = 0
    e = 0

    pairs = []

    prev_data = b''

    while data:
        if prev_data + data == soi:
            s = f.tell()-2
            while data:
                if prev_data + data == eoi:
                    e = f.tell()-1
                    if max_length == None:
                        pairs.append((s, e))
                    elif int(e-s) < max_length:
                        pairs.append((s, e))
                prev_data = data
                data = f.read(1)
            f.seek(s+2)
        prev_data = data
        data = f.read(1)
    return pairs

def parse_exif(f):

    markers = []
    four_d = 0
    ifd_count = 0
    ifd_start = 0
    dict = {}

    # find markers
    data = f.read(2)  # should be the start of image marker xffxd8
    marker = 0
    size = 0
    while marker != b"\xff\xda":
        marker = f.read(2)
        size = f.read(2)
        markers.append(f.tell())
        size = unpack(">H", size)[0]
        f.seek(size - 2, 1)

    # find header
    find_header(f, markers)

    # find out endian
    four_d = f.tell()
    endian = f.read(4)
    next_ifd = 1

    while next_ifd != 00000000:
        if next_ifd != 1:
            ifd_offset = next_ifd
        else:
            if endian == b'II\x2a\x00':
                ifd_offset = unpack("<L", f.read(4))[0]
            elif endian == b'MM\x00\x2a':
                ifd_offset = unpack(">L", f.read(4))[0]
            else:
                assert False
            f.seek(ifd_offset - 8, 1)

        if endian == b'II\x2a\x00':
            ifd_count = unpack("<H", f.read(2))[0]
        elif endian == b'MM\x00\x2a':
            ifd_count = unpack(">H", f.read(2))[0]
        else:
            assert false

        print('ifd_count:', ifd_count)
        ifd_start = f.tell()

        if endian != b'MM\x00\x2a':
            next_ifd = parse_ifd_le(f, ifd_offset, ifd_count, ifd_start, dict, four_d, endian)
        else:
            next_ifd = parse_ifd_be(f, ifd_offset, ifd_count, ifd_start, dict, four_d, endian)

    print (dict)
    return dict


def parse_ifd_be(f, ifd_offset, ifd_count, ifd_start, dict, four_d, endian):
    bytes_per_component = (0, 1, 1, 2, 4, 8, 1, 1, 2, 4, 8, 4, 8)

    for i in range(0, ifd_count):
        print('i:', i)

        # 12 bytes per entry
        f.seek(i * 12, 1)

        # tag
        t = unpack(">H", f.read(2))[0]
        print('t: %d' % t)
        if t not in TAGS:
            print('continuing')
            f.seek(ifd_start)
            continue
        tag = TAGS[t]
        print ("tag: %s" % tag)

        # all the parts of the ifd
        format = unpack(">H", f.read(2))[0]
        components = unpack(">L", f.read(4))[0]
        length = bytes_per_component[format] * components
        data = f.read(4)

        # check if its the value or an offset
        if length > 4:
            f.seek(four_d + unpack(">L", data)[0])  # find the offset
            data = f.read(length)  # variable size when its an offset
        add_to_dict(tag, format, components, length, data, dict, endian)

        # check the next bytes to look for potential offset
        if i == ifd_count - 1:
            end_val = f.read(4)
            if (end_val != b'\x00\x00\x00\x00'):
                return f.seek(four_d + unpack(">L", end_val)[0])  # find the offset
            else:
                return 00000000

        f.seek(ifd_start)


def parse_ifd_le(f, ifd_offset, ifd_count, ifd_start, dict, four_d, endian):
    bytes_per_component = (0, 1, 1, 2, 4, 8, 1, 1, 2, 4, 8, 4, 8)

    for i in range(0, ifd_count):

        print ('i:', i)

        # 12 bytes per entry
        f.seek(i * 12, 1)

        # tag
        t = unpack("<H", f.read(2))[0]
        print('t: %d' % t)
        if t not in TAGS:
            print('continuing')
            f.seek(ifd_start)
            continue
        tag = TAGS[t]
        print ("tag: %s" % tag)


        # all the parts of the ifd
        format = unpack("<H", f.read(2))[0]
        print ("f: %d" % format)
        components = unpack("<L", f.read(4))[0]
        length = bytes_per_component[format] * components
        data = f.read(4)

        # check if its the value or an offset
        if length > 4:
            f.seek(four_d + unpack("<L", data)[0])  # find the offset
            data = f.read(length)  # variable size when its an offset

        add_to_dict(tag, format, components, length, data, dict, endian)

        # check the next bytes to look for potential offset
        if i == ifd_count - 1:

            end_val = f.read(4)
            print ("end val: ",end_val)
            if (end_val != b'\x00\x00\x00\x00'):
                return f.seek(four_d + unpack("<L", end_val)[0])  # find the offset
            else:
                return 00000000

        f.seek(ifd_start)

def find_header(f,markers):
    for m in markers:
        f.seek(m)
        exif = f.read(6)

        # check for exif header
        if exif == b'Exif\x00\x00':
            return

def add_to_dict(tag, format, components, length, data, dict, endian):
    if endian != b'MM\x00\x2a':
        if format == 1:
            dict[tag] = [unpack("<B", data[0:1])[0]]
        elif format == 2:
            dict[tag] = [bytes.decode(data[0:length - 1])]
        elif format == 3:
            if tag in dict:
                dict[tag].append(unpack("<%dH" % components, data[0:length])[0])
            else:
                dict[tag] = ([unpack("<%dH" % components, data[0:length])[0]])
        elif format == 4:
            dict[tag] = [unpack("<L", data[0:4])[0]]
        elif format == 5:
            (numerator, denominator) = unpack('<LL', data[0:8])
            if tag in dict:
                dict[tag].append('%s/%s' % (numerator, denominator))
            else:
                dict[tag] = ['%s/%s' % (numerator, denominator)]
        elif format == 7:
            value = unpack("<%dB" % length, data[0:length])
            dict[tag] = "".join("%.2x" % x for x in value)
    else:
        if format == 1:
            dict[tag] = [unpack(">B", data[0:1])[0]]
        elif format == 2:
            dict[tag] = [bytes.decode(data[0:length - 1])]
        elif format == 3:
            if tag in dict:
                dict[tag].append(unpack(">%dH" % components, data[0:length])[0])
            else:
                dict[tag] = ([unpack(">%dH" % components, data[0:length])[0]])
        elif format == 4:
            dict[tag] = [unpack(">L", data[0:4])[0]]
        elif format == 5:
            (numerator, denominator) = unpack('>LL', data[0:8])
            if tag in dict:
                dict[tag].append('%s/%s' % (numerator, denominator))
            else:
                dict[tag] = ['%s/%s' % (numerator, denominator)]
        elif format == 7:
            value = unpack(">%dB" % length, data[0:length])
            dict[tag] = "".join("%.2x" % x for x in value)


# Standard boilerplate to run main()
if __name__ == '__main__':
    with open(sys.argv[1], 'rb') as f:
        parse_exif(f)


