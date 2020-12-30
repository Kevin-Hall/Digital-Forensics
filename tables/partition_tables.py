from struct import unpack
import uuid
import sys


def parse_mbr(mbr_bytes):

    boot = mbr_bytes[0:446]
    p1 = mbr_bytes[446:446+16]
    p2 = mbr_bytes[446+16:446+32]
    p3 = mbr_bytes[446 + 32:446 + 48]
    p4 = mbr_bytes[446 + 48:446 + 64]
    hex_signature = mbr_bytes[446 + 64:446 + 66]

    partitions = [p1,p2,p3,p4]

    list = []


    if hex_signature == b'U\xaa':

        number = 0

        for p in partitions:
            dict = {}
            status_flags = p[0:1]
            starting_chs_adress = p[1:4]
            type = p[4:5]
            print (type)
            print (hex(unpack("<B", type)[0]))
            ending_lba_sector = p[5:8]
            starting_lba_sector = p[8:12]
            print (unpack('<I', starting_lba_sector)[0])
            number_of_sectors = p[12:16]
            print (unpack('<I', number_of_sectors)[0])

            if type != b'\x00':
                dict['type'] = hex(unpack("<B", type)[0])
                dict['end'] = unpack('<I', number_of_sectors)[0] + unpack('<I', starting_lba_sector)[0] - 1
                dict['start'] = unpack('<I', starting_lba_sector)[0]
                dict['number'] = number
                list.append(dict)
                print (dict)
                number += 1

    return list


def parse_gpt(gpt_file, sector_size=512):

    entries = []
    total_bytes = gpt_file.read()
    gpt_file.seek(0)

    gpt_protective_mbr = gpt_file.read(sector_size) #LBA 0
    gpt_header = gpt_file.read(sector_size)         #LBA 1

    signature = gpt_header[0:8]
    revision = gpt_header[8:12]
    header_size = gpt_header[12:16]
    crc32 = gpt_header[16:20]
    reserved = gpt_header[20:24] #must be zero
    current_LBA = gpt_header[24:32]
    backup_LBA = gpt_header[32:40]
    first_usable_LBA = gpt_header[40:48]
    last_usable_LBA = gpt_header[48:56]
    disk_GUID = gpt_header[56:72]
    partition_entries = gpt_header[72:80]
    num_entries = gpt_header[80:84]


    n = gpt_file.tell() # 2x sector size

    while n <= len(total_bytes):
        print (n)
        get_entry(entries, gpt_file, sector_size)
        n += 512

    return entries


def get_entry(entries, gpt_file, sector_size):
    curr_entry = gpt_file.read(128)
    dict = {}
    type = curr_entry[0:16]

    if type != b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00':

        first = curr_entry[32:40]
        dict['start'] = unpack('<Q', first)[0]

        last = curr_entry[40:48]
        dict['end'] = unpack('<Q', last)[0]

        if len(entries) == 0:
            num = 0
        else:
            num = len(entries)
        dict['number'] = num

        name = curr_entry[56:128]
        trimpoint = name.decode('utf-16le').find('\x00')
        name_trimmed = curr_entry[56:56 + trimpoint * 2]
        dict['name'] = name_trimmed.decode('utf-16le')

        dict['type'] = uuid.UUID(bytes_le=type)

        entries.append(dict)
        print (entries)


if __name__ == '__main__':
    parse_gpt(sys.argv[1])
