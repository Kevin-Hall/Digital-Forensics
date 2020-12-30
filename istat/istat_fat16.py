import struct
import sys
from struct import unpack
import struct



def as_unsigned(bs, endian='<'):
    unsigned_format = {1: 'B', 2: 'H', 4: 'L', 8: 'Q'}
    if len(bs) <= 0 or len(bs) > 8:
        raise ValueError()
    fill = '\x00'
    while len(bs) not in unsigned_format:
        bs = bs + fill
    result = struct.unpack(endian + unsigned_format[len(bs)], bs)[0]
    return result


def decode_fat_time(time_bytes, tenths=0, tz='EDT'):
    v = as_unsigned(time_bytes)
    second = int(int(0x1F & v) * 2)
    if tenths > 100:
        second += 1
    minute = (0x7E0 & v) >> 5
    hour = (0xF800 & v) >> 11
    return '{:02}:{:02}:{:02} ({})'.format(hour, minute, second, tz)


def decode_fat_day(date_bytes):
    v = as_unsigned(date_bytes)
    day = 0x1F & v
    month = (0x1E0 & v) >> 5
    year = ((0xFE00 & v) >> 9) + 1980
    return '{}-{:02}-{:02}'.format(year, month, day)


def istat_fat16(f, address, sector_size=512, offset=0):
    result = []

    boot = f.read()

    if offset>0:
        boot=boot[sector_size*offset:len(boot)]

    reserved_sector_size = unpack('<H', boot[14:16])[0]  # size in sectors of reserved area
    number_of_fats = unpack("<B", boot[16:17])[0]
    fat_size = unpack("<H", boot[22:24])[0]  # size in sector of each fat
    fats_end = reserved_sector_size + fat_size
    max_number_of_files = unpack('<H', boot[17:19])[0]
    if number_of_fats == 2:
        fats_end = fats_end * 2 - 1
    fat_offset = reserved_sector_size * sector_size + 2 - offset


    root_directory_start = ((fats_end)*sector_size)
    root_directory_end = int((fats_end+fat_offset+((max_number_of_files*32)/sector_size)) * sector_size)
    root = boot[root_directory_start:root_directory_end]


    # start = 0*32
    start = (address-3)*32
    end = start + 33
    curr_node = root[start:end]


    result.append("Directory Entry: %d" % address)

    if (curr_node[0:1] != b'\x00' and curr_node[0:1] != b'\xe5'):
        result.append("Allocated")
        file_name = (bytes.decode(curr_node[0:8])).strip(" ")
        allocated = True
    else:
        result.append("Not Allocated")
        file_name = "_" + ((bytes.decode(curr_node[1:8])).strip(" "))
        allocated = False


    file_attributes = curr_node[11:12]

    print (curr_node)
    low = curr_node[26:28]
    print ("low %s" % as_unsigned(low))

    lowval = as_unsigned(low)*2 + 29 + (offset*32)
    print (lowval)

    sectors = get_cluster_sectors(lowval,address, boot, sector_size=sector_size, offset=offset)
    print (sectors)



    r1 = sectors[0]
    r2 = sectors[1]
    sectors = []

    if allocated:
        for i in range(r1, r2 + 1):
            sectors.append(i)
    else:
        for i in range(r1, r1 + 2):
            sectors.append(i)


    result.append("File Attributes: %s" % get_attr(file_attributes))

    file_size = as_unsigned(curr_node[28:32])
    if file_size == 0:
        file_size = len(sectors) * sector_size
    result.append("Size: %d" % (file_size))



    file_extension = curr_node[8:11]
    file_extension = bytes.decode(file_extension).strip(" ")
    if file_extension != "":
        result.append("Name: %s" % file_name + "." + file_extension)
    else:
        result.append("Name: %s" % file_name)

    result.append("")

    result.append("Directory Entry Times:")

    created_time_tenths = curr_node[13:14]
    created_time_hms = curr_node[14:16]
    created_day = curr_node[16:18]
    accessed_day = curr_node[18:20]
    written_time_hms = curr_node[22:24]
    written_day = curr_node[24:26]






    result.append("Written:\t%s %s"% (decode_fat_day(written_day),decode_fat_time(written_time_hms,0)))
    result.append("Accessed:\t%s %s" % (decode_fat_day(accessed_day),decode_fat_time(bytes.fromhex('0000'),0)))
    result.append("Created:\t%s %s" % (decode_fat_day(created_day),decode_fat_time(created_time_hms,as_unsigned(created_time_tenths))))
    result.append("")
    result.append("Sectors:")


    sectors_string = ""
    column = 0

    for s in sectors:
        if column > 7:
            result.append(sectors_string)
            column = 0
            sectors_string = "" + str(s) + " "
        else:
            sectors_string = sectors_string + str(s) + " "
        column += 1

    result.append(sectors_string)


    for r in result:
        print (r)

    return result


def get_cluster_sectors(lowval,inode,boot, sector_size=512, offset=0):

    result = []

    number_of_sectors_before = unpack('<I', boot[28:32])[0]  # sectors before file system
    number_of_sectors = unpack('<H', boot[19:21])[0] - 1 + number_of_sectors_before
    if number_of_sectors == 0:
        number_of_sectors = unpack("<L", boot[32:36])[0] - 1 + number_of_sectors_before
    reserved_sector_size = unpack('<H', boot[14:16])[0]  # size in sectors of reserved area
    number_of_fats = unpack("<B", boot[16:17])[0]
    fat_size = unpack("<H", boot[22:24])[0] # size in sector of each fat
    fats_end = reserved_sector_size + fat_size
    if number_of_fats == 2:
        fats_end = fats_end * 2
    sectors_per_cluster = unpack("<B", boot[13:14])[0]
    max_number_of_files = unpack('<H', boot[17:19])[0]
    cluster_area = (number_of_sectors / sectors_per_cluster) * sectors_per_cluster
    unallocated = (cluster_area % 2)

    cluster_size = sector_size * sectors_per_cluster
    cluster_range_start = (max_number_of_files*32)/ sector_size
    cluster_range_end = (((cluster_area-offset-unallocated) - cluster_range_start) / 2) - fat_size + 1

    sector_start = (fats_end + ((max_number_of_files * 32) / sector_size) + 1 - offset)
    fat_offset = reserved_sector_size * sector_size + 4 - offset

    curr = boot[fat_offset:fat_offset + 2]
    next = boot[fat_offset + 2:fat_offset + 4]
    cluster_count = 2

    start_sector_of_cluster_area = 0

    previous_sector = 0
    curr_run = 2
    match_run = inode

    while cluster_count < cluster_range_end:

        cluster_count += 1
        fat_offset += 2

        curr = boot[fat_offset:fat_offset + 2]
        next = boot[fat_offset + 2:fat_offset + 4]
        curr_val = unpack('<H', curr)[0]
        next_val = unpack('<H', next)[0]

        if curr_val > 0:

            # Set starting sector of the run
            if (start_sector_of_cluster_area == 0 and next_val == ((curr_val + 1) or next_val == 65535)) :
                sector_number = (cluster_count - 2) * sectors_per_cluster + start_sector_of_cluster_area
                start_sector_of_cluster_area = sector_number
                previous_sector = sector_number
                # curr_run += 1
            elif start_sector_of_cluster_area == 0 and curr_val == 65535 and next_val == 65535:
                start_sector_of_cluster_area = previous_sector + 1
                curr_run += 1

            # FFFF case
            if curr_val == 65535:
                # set the end sector number to the curr val for the endpoint
                w = start_sector_of_cluster_area + sector_start + (cluster_count-2) - 1
                x = cluster_count * 2 + sector_start - 5

                if w > lowval:
                    result.append(int(w))
                    result.append(int(x))

                if next_val == 65535:
                    start_sector_of_cluster_area += 1
                    # curr_run += 1
                else:
                    start_sector_of_cluster_area = 0
                    curr_run += 1

                continue

            # if the next value is not sequential then the run is over
            if next_val != (curr_val + 1):
                if next_val == 65535:
                    w = start_sector_of_cluster_area + sector_start - 2
                    x = cluster_count * 2 + sector_start - 3

                    # if curr_run == match_run:
                    #     # result = []
                    if w > lowval:
                        result.append(int(w))
                        result.append(int(x))

                    # add the value and reset the cluster marker numbers
                    start_sector_of_cluster_area = 0
                    curr_run += 1

                    cluster_count += 1
                    fat_offset += 2
                else:
                    # set the end sector number to the curr val
                    sector_number = (next_val - 2) * sectors_per_cluster + start_sector_of_cluster_area + sector_start - 2

                    w = start_sector_of_cluster_area+sector_start - 2
                    x = cluster_count * 2 + sector_start - 3


                    if w > lowval:
                        result.append(int(w))
                        result.append(int(x))

                    # add the value and reset the cluster marker numbers
                    start_sector_of_cluster_area = 0
                    curr_run += 1
                    cluster_count += 1
                    fat_offset += 2
    return result


def get_attr(b):

    ret = ""

    if (bytes(b)[0] & bytes(b'\x0f')[0]) == (bytes(b'\x0f')[0]):
        ret += "Long File Name"
    else:
        if (bytes(b)[0] & bytes(b'\x10')[0]) == (bytes(b'\x10')[0]):
            ret += "Directory"
        elif (bytes(b)[0] & bytes(b'\x08')[0]) == (bytes(b'\x08')[0]):
            ret += "Volume Label"
        else:
            ret += "File"
        if (bytes(b)[0] & bytes(b'\x01')[0]) == (bytes(b'\x01')[0]):
            ret += ", Read Only"
        if (bytes(b)[0] & bytes(b'\x02')[0]) == (bytes(b'\x02')[0]):
            ret += ", Hidden"
        if (bytes(b)[0] & bytes(b'\x04')[0]) == (bytes(b'\x04')[0]):
            ret += ", System"
        if (bytes(b)[0] & bytes(b'\x20')[0]) == (bytes(b'\x20')[0]):
            ret += ", Archive"

    return ret



if __name__ == '__main__':
    with open(sys.argv[1], 'rb') as f:
        istat_fat16(f,776,512,2)
