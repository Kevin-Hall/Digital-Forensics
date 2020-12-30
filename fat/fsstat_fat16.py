from struct import unpack
import struct
import sys


def fsstat_fat16(fat16_file, sector_size=512, offset=2):
    result = ['FILE SYSTEM INFORMATION',
              '--------------------------------------------',
              'File System Type: FAT16',
              '']

    # then do a few things, .append()ing to result as needed

    boot = fat16_file.read()


    if offset>0:
        boot=boot[sector_size*offset:len(boot)]




    number_of_sectors_before = unpack('<I', boot[28:32])[0]  # sectors before file system



    oem = bytes.decode(boot[3:11])
    volume_id = ''.join('{:x}'.format(b) for b in reversed(boot[39:43]))
    volume_label_boot = bytes.decode(boot[43:54])
    volume_label_root = bytes.decode(boot[43:54])
    file_type = bytes.decode(boot[54:61])

    number_of_sectors = unpack('<H', boot[19:21])[0] - 1 + number_of_sectors_before
    if number_of_sectors == 0:
        number_of_sectors = unpack("<L", boot[32:36])[0] - 1 + number_of_sectors_before

    reserved_sector_size = unpack('<H', boot[14:16])[0]  # size in sectors of reserved area
    number_of_fats = unpack("<B", boot[16:17])[0]
    fat_size = unpack("<H", boot[22:24])[0] # size in sector of each fat
    fats_end = reserved_sector_size + fat_size
    sectors_per_cluster = unpack("<B", boot[13:14])[0]
    max_number_of_files = unpack('<H', boot[17:19])[0]

    cluster_area = (number_of_sectors / sectors_per_cluster) * sectors_per_cluster
    cluster_size = sector_size * sectors_per_cluster
    cluster_range_start = (max_number_of_files*32)/ sector_size




    unallocated = (cluster_area % 2)

    # cluster_range_end = (cluster_area // sectors_per_cluster) - cluster_range_start
    # ((cluster_area - unallocated) - (fats_end + cluster_range_start) / 2

    cluster_range_end = (((cluster_area-offset-unallocated) - cluster_range_start) / 2) - fat_size + 1


    result.append("OEM Name: %s" % oem)

    result.append("Volume ID: 0x" + volume_id)

    result.append("Volume Label (Boot Sector): %s" % volume_label_boot)

    result.append("File System Type Label: %s" % file_type)

    result.append('')

    result.append("Sectors before file system: %s" % number_of_sectors_before)

    result.append('')

    result.append("File System Layout (in sectors)")

    result.append("Total Range: %d - %d" % (0, number_of_sectors - offset))

    result.append("* Reserved: %d - %d" % (0, reserved_sector_size - 1))

    result.append("** Boot Sector: 0")

    result.append("* FAT 0: %d - %d" % (1, fat_size))
    if number_of_fats == 2:
        result.append("* FAT 1: %d - %d" % (fats_end, fats_end + fat_size - 1))
        fats_end = fats_end * 2 - 2

    result.append("* Data Area: %d - %d" % (fats_end+1, number_of_sectors-offset))

    result.append("** Root Directory: %d - %d" % (fats_end + 1, fats_end+((max_number_of_files*32)/sector_size)))

    result.append("** Cluster Area: %d - %d" % (fats_end+cluster_range_start+1, cluster_area-offset - unallocated))

    result.append('')

    result.append('CONTENT INFORMATION')

    result.append('--------------------------------------------')

    result.append("Sector Size: %d" % sector_size)

    result.append("Cluster Size: %d" % cluster_size)

    result.append("Total Cluster Range: 2 - %d" % (cluster_range_end))

    result.append('')

    result.append('FAT CONTENTS (in sectors)')

    result.append('--------------------------------------------')





    sector_start = (fats_end+((max_number_of_files*32)/sector_size) + 1 - offset)
    fat_offset = reserved_sector_size * sector_size + 4 - offset

    starting_fat_offset = fat_offset
    print ("Fat offset start : %d" % fat_offset)
    print ("start sector : %d" % sector_start)

    curr = boot[fat_offset:fat_offset + 2]
    next = boot[fat_offset+2:fat_offset+4]
    cluster_count = 2

    start_sector_of_cluster_area = 0
    end_sector_of_cluster_area = 0

    previous_sector = 0



    while cluster_count < cluster_range_end:

        cluster_count += 1
        fat_offset += 2

        curr = boot[fat_offset:fat_offset + 2]
        next = boot[fat_offset+2:fat_offset + 4]

        curr_val = unpack('<H', curr)[0]
        next_val = unpack('<H', next)[0]

        if curr_val > 0:

            # Set starting sector of the run
            if (start_sector_of_cluster_area == 0 and next_val == (curr_val+1)):
                sector_number = (cluster_count - 2) * sectors_per_cluster + start_sector_of_cluster_area
                start_sector_of_cluster_area = sector_number
                print ("set start sector to %d" % start_sector_of_cluster_area)
                previous_sector = sector_number
            elif start_sector_of_cluster_area == 0 and curr_val == 65535 and next_val == 65535:
                start_sector_of_cluster_area = previous_sector+1


            # FFFF case
            if curr_val == 65535:
                # set the end sector number to the curr val for the endpoint
                w = start_sector_of_cluster_area + sector_start + cluster_count-1
                x = cluster_count * 2 + sector_start - 3
                y = x-w + 1


                print ("-----------")
                print (start_sector_of_cluster_area)
                # add the value and reset the cluster marker numbers
                print("%d-%d (%d) -> EOF" % (w,x,y))
                add_result(w, x, y, "EOF",result)


                if next_val == 65535:
                    start_sector_of_cluster_area += 1
                else:
                    start_sector_of_cluster_area = 0

                continue

            # if the next value is not sequential then the run is over
            if next_val != (curr_val+1):
                print (cluster_count)

                if next_val == 65535:
                    end_sector_of_cluster_area = cluster_count + sector_start

                    w = start_sector_of_cluster_area + sector_start
                    x = cluster_count * 2 + sector_start - 1
                    y = x-w + 1

                    add_result(w,x,y,"EOF",result)
                    print("%d-%d (%d) -> EOF" % (w,x,y))

                    # add the value and reset the cluster marker numbers
                    start_sector_of_cluster_area = 0
                    cluster_count += 1
                    fat_offset += 2
                else:
                    # set the end sector number to the curr val
                    sector_number = (next_val - 2) * sectors_per_cluster + start_sector_of_cluster_area + sector_start - 2

                    w = start_sector_of_cluster_area+sector_start
                    x = cluster_count * 2 + sector_start - 1
                    y = x-w + 1
                    z = int(sector_number - start_sector_of_cluster_area + (unallocated*2) + offset)

                    add_result(w,x,y,z,result)
                    print("%d-%d (%d) -> %d" % (w, x, y, z))

                    # add the value and reset the cluster marker numbers
                    start_sector_of_cluster_area = 0
                    cluster_count += 1
                    fat_offset += 2

    for i in result:
        print (i)

    return result


def add_result(first_sector,last_sector,number_of_sectors,end,result):
    result.append( "%d-%d (%d) -> %s" % (first_sector, last_sector, number_of_sectors,end))



if __name__ == '__main__':
    with open(sys.argv[1], 'rb') as f:
        fsstat_fat16(f,512,2)
