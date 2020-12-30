import datetime
import struct


def as_signed_le(bs):
    if len(bs) <= 0 or len(bs) > 8:
        raise ValueError()

    signed_format = {1: 'b', 2: 'h', 4: 'l', 8: 'q'}

    fill = b'\xFF' if ((bs[-1] & 0x80) >> 7) == 1 else b'\x00'

    while len(bs) not in signed_format:
        bs = bs + fill

    return struct.unpack('<' + signed_format[len(bs)], bs)[0]


def istat_ntfs(f, address, sector_size=512, offset=0):

    result = ["MFT Entry Header Values:"]

    all_bytes = f.read()
    boot = all_bytes[0:512]

    if offset > 0:
        boot = boot[sector_size * offset:sector_size * offset + len(boot)]

    """
    Parse Boot Sector
    """
    print ("parsing boot sector ----------------------------")
    bytes_per_sector = as_signed_le(boot[11:13])
    sectors_per_cluster = as_signed_le(boot[13:14])
    total_sectors = as_signed_le(boot[40:48])

    mft_starting_address = as_signed_le(boot[48:56])
    mft_starting_address *= bytes_per_sector * sectors_per_cluster
    mft_starting_address += (1024 * address)

    mft_entry_size = as_signed_le(boot[64:66])
    indexrecord_size = as_signed_le(boot[68:69])
    print ("bytes per sector %s" % bytes_per_sector)
    print ("sectors per cluster: %s" % sectors_per_cluster)
    print ("total sectors: %s" % total_sectors)
    print ("mft start: %s" % mft_starting_address)
    print ("mft size: %s" % mft_entry_size)
    print ("index record: %s" % indexrecord_size)
    print ("")

    """
    Parse First MFT entry
    """
    print ("parsing first MFT header ----------------------------")
    f.seek(mft_starting_address)
    first_mft = f.read(1024)

    LSN = as_signed_le(first_mft[8:16])             # logfile seq number
    seq_val = as_signed_le(first_mft[16:18])
    link_count = as_signed_le(first_mft[18:20])
    offset_first_attr = as_signed_le(first_mft[20:22])
    flags = as_signed_le(first_mft[22:24])
    used_size_mft_entry = as_signed_le(first_mft[24:28])
    allocated_size_mft_entry = as_signed_le(first_mft[28:32])
    nextattr_id = as_signed_le(first_mft[40:42])

    result.append("Entry: %d        Sequence: %d" % (address,seq_val))
    result.append("$LogFile Sequence Number: %d" % LSN)

    if allocated_size_mft_entry > 0:
        result.append("Allocated File")
    else:
        result.append("Unallocated File")

    result.append("Links: %d" % link_count)
    result.append("")

    """
    First MFT entry Fixup 
    """
    print ("First MFT entry Fixup ----------------------------")
    fixuparr_offset = as_signed_le(first_mft[4:6])
    fixuparr_count = as_signed_le(first_mft[6:8])

    # read in the fixup array
    fixup_arr = []
    for i in range(0, fixuparr_count - 1):
        fixup_arr.append(first_mft[offset + 2 + i * 2: offset + 4 + i * 2])

    new_entry = []
    curr_offset = 0

    # replace final two values with fixup values
    for i in range(0, fixuparr_count - 1):
        sector_offset = 510 * (i + 1) + i * 2
        new_entry.extend(first_mft[curr_offset:sector_offset])
        new_entry.extend(fixup_arr[i])
        fixup_arr[i] = first_mft[sector_offset:sector_offset + 2]
        curr_offset = sector_offset + 2

    new_entry = bytearray(new_entry)
    first_mft = new_entry  # overwrite the bytes in memory

    byte_offset = offset_first_attr
    attr_count = 0

    """
    parse First MFT attributes
    """
    attributes = []
    runlist = []
    while (byte_offset + 16 < used_size_mft_entry and attr_count < nextattr_id):

        attr_size = as_signed_le(first_mft[byte_offset+4:byte_offset+8])
        attr = first_mft[byte_offset:byte_offset + attr_size]

        attr_type = as_signed_le(attr[0:4])
        nr_flag = as_signed_le(attr[8:9])
        attr_id = as_signed_le(attr[14:16])

        # Resident attribute
        if nr_flag == 0:
            content_offset = as_signed_le(attr[20:22])
            content_size = as_signed_le(attr[16:20])

            # $STD_INFO
            if attr_type == 16:
                result.append("$STANDARD_INFORMATION Attribute Values:")
                content = attr[content_offset:content_offset + content_size]

                flags = as_signed_le(content[32:36])
                flags = get_flags(flags)

                if content[48:52] == b'':
                    owner_id = 0
                else:
                    owner_id = as_signed_le(content[48:52])


                result.append("Flags: %s" % flags)
                result.append("Owner ID: %s" % owner_id)
                result.append("Created:\t%s" % into_localtime_string(struct.unpack('<Q', content[0:8])[0]))
                result.append("File Modified:\t%s" % into_localtime_string(struct.unpack('<Q', content[8:16])[0]))
                result.append("MFT Modified:\t%s" % into_localtime_string(struct.unpack('<Q', content[16:24])[0]))
                result.append("Accessed:\t%s" % into_localtime_string(struct.unpack('<Q', content[24:32])[0]))
                result.append("")

                size = (attr_size - address) * 2
                attributes.append("Type: $STANDARD_INFORMATION (%d-%d)   Name: %s   Resident   size: %d" % (attr_type,attr_id, "N/A",len(content)))

            # $FILE_NAME
            elif attr_type == 48:
                result.append("$FILE_NAME Attribute Values:")

                content = attr[content_offset:content_offset + content_size]

                parent_dir_seq = as_signed_le(content[0:2])
                seq = as_signed_le(content[6:8])
                alloc_size = as_signed_le(content[40:48])
                real_size = as_signed_le(content[48:56])
                flags = as_signed_le(content[56:60])
                flags = get_flags(flags)
                name_length = as_signed_le(content[64:65])
                namespace = as_signed_le(content[65:66])
                name = content[66:].decode("utf-16le")

                result.append("Flags: %s" % flags)
                result.append("Name: %s" % name)
                result.append("Parent MFT Entry: %d \tSequence: %d" % (parent_dir_seq,seq))
                result.append("Allocated Size: %d   \tActual Size: %d" % (alloc_size,real_size))
                result.append("Created:\t%s" % into_localtime_string(struct.unpack('<Q', content[8:16])[0]))
                result.append("File Modified:\t%s" % into_localtime_string(struct.unpack('<Q', content[16:24])[0]))
                result.append("MFT Modified:\t%s" % into_localtime_string(struct.unpack('<Q', content[24:32])[0]))
                result.append("Accessed:\t%s" % into_localtime_string(struct.unpack('<Q', content[32:40])[0]))
                result.append("")

                attributes.append("Type: $FILE_NAME (%d-%d)   Name: %s   Resident   size: %d" % (attr_type, attr_id, "N/A", len(content)))
            elif attr_type == 128:
                content = attr[content_offset:content_offset + content_size]
                attributes.append("Type: $DATA (%d-%d)   Name: %s   Resident   size: %d" % (attr_type, attr_id, "N/A", len(content)))

        # Non-resident attribute
        elif nr_flag == 1:

            size = as_signed_le(attr[48:56])
            init_size = as_signed_le(attr[56:64])
            if attr_type == 128:
                attributes.append("Type: $DATA (%d-%d)   Name: %s   Non-Resident   size: %d  init_size: %d" % (
                attr_type, attr_id, "N/A", size, init_size))


            #setup for parsing runlist
            first = as_signed_le(attr[32:34])
            curr_rl_offset = as_signed_le(attr[32:34])
            curr = attr[curr_rl_offset:curr_rl_offset + 1]
            curr_rl_offset += 1
            prev_offset = 0

            # parse the runlist (cluster range)
            while (curr != b"\x00"):

                offset_field = as_signed_le(curr) >> 4

                rl_field = as_signed_le(curr) & 0b00001111
                rl_length = as_signed_le(attr[curr_rl_offset:curr_rl_offset + rl_field])
                curr_rl_offset += rl_field

                rl_offset = as_signed_le(attr[curr_rl_offset:curr_rl_offset + offset_field])

                print (rl_offset)
                curr_rl_offset += offset_field




                start_cluster = prev_offset + rl_offset
                end_cluster = start_cluster + rl_length - 1

                runlist.extend(range(start_cluster, end_cluster + 1))

                if prev_offset != 0:
                    prev_offset += rl_offset
                else:
                    prev_offset = rl_offset
                curr = attr[curr_rl_offset:curr_rl_offset + 1]
                curr_rl_offset += 1

        # set up for next attribute
        byte_offset += attr_size
        attr_count += 1

    """
    parse attributes
    """
    result.append("Attributes:")

    for attr in attributes:
        result.append(attr)



    """
    parse cluster range
    """
    if runlist != []:
        sectors_string = ""
        column = 0
        for s in runlist:
            if column > 7:
                result.append(sectors_string)
                column = 0
                sectors_string = "" + str(s) + " "
            else:
                sectors_string = sectors_string + str(s) + " "
            column += 1

        result.append(sectors_string)

    return result


def get_flags(flags):

    strings = ""

    if flags & 0b0001 == 1: strings += "Read Only "
    if flags & 0b0010 == 2: strings += "Hidden "
    if flags & 0b0100 == 4: strings += "System "
    if flags & 0b00100000 == 32: strings += "Archive "
    if flags & 0b01000000 == 64: strings += "Device "
    if flags & 0b10000000 == 128: strings += "#Normal "
    if flags & 0b000100000000 == 256: strings += "Temporary "
    if flags & 0b001000000000 == 512: strings += "Sparse file "
    if flags & 0b010000000000 == 1024: strings += "Reparse point "
    if flags & 0b100000000000 == 2048: strings += "Compressed "
    if flags & 0b0001000000000000 == 4096: strings += "Offline "
    if flags & 0b0010000000000000 == 8192: strings += "Content is not being indexed for faster searches "
    if flags & 0b0100000000000000 == 16384: strings += "Encrypted "

    return strings


def into_localtime_string(windows_timestamp):
    """
    Convert a windows timestamp into istat-compatible output.

    Assumes your local host is in the EDT timezone.

    :param windows_timestamp: the struct.decoded 8-byte windows timestamp
    :return: an istat-compatible string representation of this time in EDT
    """
    dt = datetime.datetime.fromtimestamp((windows_timestamp - 116444736000000000) / 10000000)
    hms = dt.strftime('%Y-%m-%d %H:%M:%S')
    fraction = windows_timestamp % 10000000
    return hms + '.' + str(fraction) + '00 (EDT)'


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Display details of a meta-data structure (i.e. inode).')
    parser.add_argument('-o', type=int, default=0, metavar='imgoffset',
                        help='The offset of the file system in the image (in sectors)')
    parser.add_argument('-b', type=int, default=512, metavar='dev_sector_size',
                        help='The size (in bytes) of the device sectors')
    parser.add_argument('image', help='Path to an NTFS raw (dd) image')
    parser.add_argument('address', type=int, help='Meta-data number to display stats on')
    args = parser.parse_args()
    with open(args.image, 'rb') as f:
        result = istat_ntfs(f, args.address, args.b, args.o)
        for line in result:
            print(line.strip())