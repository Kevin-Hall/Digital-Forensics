import sys
from struct import unpack
import datetime


class NTFS(object):
    """
    Parses the $MFT and an arbitrary MFT entry of an NTFS image.
    p.s. If I had more time I would refactor and reorganize this more than I did.
    p.p.s. I understand NTFS now.
    Variables:
        _dmg (string): name of the image to be parsed
        _fd (file): the image being parsed
        _entry_num (int): the MFT entry to be parsed other than the $MFT_entry
        _mft0 (MFT_entry): the first entry in the MFT
        _bytes_per_sector (int): the number of bytes per sector
        _sectors_per_cluster (int): the number of sectors per cluster
        _mft_start (int): the starting byte of the MFT
        _mft (bytes): the first entry of the MFT
    Functions:
        run()
        parse_boot_sector()
        parse_mft()
        parse_entry()
        open_image()
    """

    def __init__(self, entry, dmg):
        self._dmg = dmg
        self._fd = None

        try:
            self._entry_num = int(entry)
        except:
            print("Please input number not letter...")
            print("Error:", sys.exc_info()[0])

        self._bytes_per_sector = 0
        self._sectors_per_cluster = 0
        self._mft_start = 0
        self._mft = None

    def run(self):
        """
        Runs all necessary functions to parse the $MFT and the arbitrary
        entry in the MFT.
        """
        self.open_image()
        self.parse_boot_sector()
        self.parse_mft()
        self.parse_entry()

    def parse_boot_sector(self):
        """
        Finds the starting cluster address of the MFT.
        Prints:
            The important values found or calculateed from the boot sector
        """
        print ("---- PARSING BOOT SECTOR ----")

        # get the number of bytes per sector from the boot sector
        self._fd.seek(11)
        self._bytes_per_sector = unpack("<H", self._fd.read(2))[0]
        print ("Bytes per Sector: %d" % self._bytes_per_sector)

        # get the number of sectors per cluster from the boot sector
        self._sectors_per_cluster = unpack("<B", self._fd.read(1))[0]
        print ("Sectors per Cluster: %d" % self._sectors_per_cluster)

        # get the start of the $MFT
        self._fd.seek(48)
        self._mft_start = unpack("<2L", self._fd.read(8))[0]
        print ("MFT Cluster Start: %d" % self._mft_start)
        self._mft_start *= self._bytes_per_sector * self._sectors_per_cluster
        print ("MFT Byte Start: %d" % self._mft_start)

        # get total sectors
        self._fd.seek(40)
        self._total_sectors = unpack("<2L", self._fd.read(8))[0]
        print ("Total Sectors: %d" % self._total_sectors)

        print ("")

    def parse_mft(self):
        """
        Parses the first entry in the MFT.
        Prints:
            Output for the first entry of the MFT
        """
        print ("---- PARSING MFT ENTRY 0 ----")
        self._fd.seek(self._mft_start)
        self._mft = self._fd.read(1024)

        self._mft0 = MFT_entry(self._mft)
        self._mft0.run()

    def parse_entry(self):
        """
        Locates the given entry in the MFT on disk and parses it the same way
        as entry 0.
        Attributes:
            entries_per_cluster (int):
            entry_start (int): the starting cluster of the given entry and the
                and the starting byte of the given entry
            entry (MFT_entry): the MFT entry that is parsed
        Prints:
            Output for the given entry
        """
        print ("---- PARSING ENTRY %d ----" % self._entry_num)
        entries_per_cluster = self._sectors_per_cluster * self._bytes_per_sector / 1024

        try:
            # get starting cluster
            entry_start = self._mft0._runlist[(int)(self._entry_num / entries_per_cluster)]
            # get starting byte
            entry_start *= self._bytes_per_sector * self._sectors_per_cluster

            self._fd.seek(entry_start)
            entry = MFT_entry(self._fd.read(1024))
            entry.run()
        except:
            # the entry is out of the runlists bounds
            print ("The file system does not contain the selected entry...")
            print ("Error:", sys.exc_info()[0])

    def open_image(self):
        """ Opens dmg, and calls usage() on error """
        try:
            self._fd = (open(self._dmg, "rb"))
        except IOError as err:
            print("IOError opening image: \n\t%s" % err)
            usage()
        except:
            print("Unexpected error:", sys.exc_info()[0])
            usage()


class MFT_entry(object):
    """
    Parses an MFT entry.
    Variables:
        _entry (bytes): the entry being parsed
        _first_attr (int): offset to the first attribute
        _used_size (int): bytes filled in the entry
        _next_attrID (int): the value would be assigned to a new attribute
        _runlist (ints): clusters in the runlist
    Functions:
        run()
        parse_header()
        fix_up()
        parse_attributes()
        parse_attr_header()
        parse_resident_attr()
        parse_nonresident_attr()
        parse_runlist()
    """

    def __init__(self, entry):
        self._entry = entry
        self._first_attr = 0
        self._used_size = 0
        self._next_attrID = 0
        self._runlist = []

    def run(self):
        """
        Runs the necessary functions to parse the entry.
        """
        self.parse_header()
        self.fix_up()
        self.parse_attributes()

    def parse_header(self):
        """
        Parses the header values of the MFT entry.
        Attributes:
            seq (int): sequence value of the entry
            lsn (int): logfile sequence number of the entry
            allocated_size (int): allocated size of the entry
        """

        # get the sequence value of the entry
        seq = unpack("<B", self._entry[16:17])[0]

        # get the logfile sequence number (lsn) of the entry
        lsn = unpack("<2L", self._entry[8:16])[0]

        # get used size of the entry
        self._used_size = unpack("<L", self._entry[24:28])[0]

        # get allocated size of the entry
        allocated_size = unpack("<L", self._entry[28:32])[0]

        # get offset to first attribute
        self._first_attr = unpack("<H", self._entry[20:22])[0]

        # get next attribute id
        self._next_attrID = unpack("<H", self._entry[40:42])[0]

        print ("MFT Entry Header Values:")
        print ("Sequence: %d" % seq)
        print ("$LogFile Sequence Number: %d" % lsn)
        if allocated_size > 0:
            print ("Allocated File")
        else:
            print ("Unallocated File")
        print ("")
        print ("Used size: %d bytes" % self._used_size)
        print ("Allocated size: %d bytes" % allocated_size)
        print ("")

    def fix_up(self):
        """
        Handle the fix up array. Finds the fixup array, the number of entries
        and the signature. Then swaps the last two values of each sector
        with the corresponding value from the fixup array.
        Attributes:
            offset (int): the offset to the fixup array
            num (int): the number of entries in the fixup array
            signature (hex): the fixup signature
            fixup_array (bytes): the byte values of the fixup array
            string (string): the string of fixup array values to print
            temp_entry (bytes): the temporary array to enable overwriting the fixup values
            current_offset (int): the offset to the next bytes to swap with the fixup array
            sector_offset (int): offset to the bytes in the sector where the fixup value is going
        """

        # get the offset to the fix up array
        offset = unpack("<H", self._entry[4:6])[0]
        print ("Offset to fix up array: %d" % offset)

        # get the number of entries in the fix up array
        num = unpack("<H", self._entry[6:8])[0]
        print ("Number of entries in the fix up array: %d" % num)

        # get the fixup signature
        signature = ''.join('{:02x}'.format(b) for b in reversed(self._entry[offset:offset + 2]))
        print ("Fixup sig: 0x" + signature)

        # read in the fixup array
        fixup_array = []
        for i in range(0, num - 1):
            fixup_array.append(self._entry[offset + 2 + i * 2: offset + 4 + i * 2])

        # overwrite proper values
        temp_entry = []  # cannot overwrite bytes without making a new array
        current_offset = 0

        for i in range(0, num - 1):
            sector_offset = 510 * (i + 1) + i * 2

            bytes = "0x" + ''.join('{:02x}'.format(b) for b in
                                   reversed(self._entry[sector_offset:sector_offset + 2]))
            print ("Bytes %d/%d %s;" % (sector_offset, sector_offset + 1, bytes), end=" ")

            print ("Overwriting 0x%s into bytes %d/%d" %
                   (''.join('{:02x}'.format(b) for b in reversed(fixup_array[i])),
                    sector_offset, sector_offset + 1))

            # add sector up until last two bytes
            temp_entry.extend(self._entry[current_offset:sector_offset])

            # add fixup value
            temp_entry.extend(fixup_array[i])

            # replace value in the fixup array with the one on disk
            fixup_array[i] = self._entry[sector_offset:sector_offset + 2]

            # update offset
            current_offset = sector_offset + 2

        # create temp_entry as bytearray
        temp_entry = bytearray(temp_entry)
        self._entry = temp_entry  # overwrite the bytes in memory

        print ("")

    def parse_attributes(self):
        """
        Parses all attributes in the entry.
        Attributes:
            byte_offset (int): the offset of the next attribute
            attr_count (int): the number of attributes parsed
            attr_size (int): the size in bytes of the attribute
            attr (bytes): the attribute in memory
            standard_info (STD_INFO): the $STD_INFO attribute
            file_name (FILE_NAME): the $FILE_NAME attribute
            nr_flag (int): zero if attribute is resident, 1 if non-resident
        """

        byte_offset = self._first_attr
        attr_count = 0

        # while still within the entry and the number assigned attributes
        while (byte_offset + 16 < self._used_size and attr_count < self._next_attrID):
            print (
                        "Parsing next attribute: ((byte_offset=(%d+16) < used_size=%d) and (attr_count=%d < next_attribute=%d)"
                        % (byte_offset, self._used_size, attr_count, self._next_attrID))

            # read in first/next attribute
            attr_size = unpack("<L", self._entry[byte_offset + 4:byte_offset + 8])[0]
            attr = self._entry[byte_offset:byte_offset + attr_size]

            attr_type, nr_flag = self.parse_attr_header(attr, attr_size)

            # if it is a resident attribute
            if nr_flag == 0:
                content_size, content_offset = self.parse_resident_attr(attr)

                # if type is 16, parse std_info
                if attr_type == 16:
                    standard_info = STD_INFO(attr, content_size, content_offset)
                    standard_info.parse()

                # if type is 48, parse file_name
                elif attr_type == 48:
                    file_name = FILE_NAME(attr, content_size, content_offset)
                    file_name.parse()

            # if it is a non-resident attribute
            elif nr_flag == 1:
                self.parse_nonresident_attr(attr, attr_type)

            # set up for next attribute
            byte_offset += attr_size
            attr_count += 1
            print ("")
            # end while loop

    def parse_attr_header(self, attr, attr_size):
        """
        Parses attribute's header.
        Attributes:
            attr_type (int): the identifier for certain attribute types
            nr_flag (int): non-resident flag - 0 if the attribute is resident, 1 if non-resident
            resident (string): "resident" if attr. is resident, "non-resident" otherwise
            name_length (int): length of name
            name_offset (int): offset to name
            flags (int): attribute flags, compressed, encrypted, or sparse
            attr_id (int): unique number to this attr. for this MFT entry
        Prints:
            Important values in the attribute headers
        Returns:
            Attribute type and non-resident flag
        """
        # get attribute type identifier 0-3
        attr_type = unpack("<L", attr[0:4])[0]

        # get non-resident flag 8-8
        nr_flag = unpack("<B", attr[8:9])[0]
        if nr_flag == 0:
            resident = "Resident"
        else:
            resident = "Non-resident"

        # get length of name 9-9
        name_length = unpack("<B", attr[9:10])[0]

        # get offset to name 10-11
        name_offset = unpack("<H", attr[10:12])[0]

        # get flags 12-13
        flags = unpack("<H", attr[12:14])[0]

        # get attribute identifier 14-15
        attr_id = unpack("<H", attr[14:16])[0]

        # print attribute header
        print ("Type: %d, %s, size: %d, " % (attr_type, resident, attr_size), end="")
        print ("NameLen: %d, NameOff: %d, " % (name_length, name_offset), end="")
        print ("Flags: %d, Attribute id: %d" % (flags, attr_id))

        return attr_type, nr_flag

    def parse_resident_attr(self, attr):
        """
        Parses resident attributes.
        Attributes:
            content_size (int): size of the attribute content
            content_offset (int): offset to the attribute content
        Returns:
            Content size and offset
        """

        # get offset to content
        content_offset = unpack("<H", attr[20:22])[0]
        print ("\tOffset to content:  %d" % content_offset, end=" ")

        # get size of content
        content_size = unpack("<L", attr[16:20])[0]
        print ("\tSize of content:  %d" % content_size)

        return content_size, content_offset

    def parse_nonresident_attr(self, attr, attr_type):
        """
        Parses non-resident attributes.
        Attributes:
            start_vcn (int): starting virtual cluster number
            end_vcn (int): ending virtual cluster number
            offset_to_rl (int): offset to runlist
        """

        start_vcn = unpack("<2L", attr[16:24])[0]
        end_vcn = unpack("<2L", attr[24:32])[0]
        print ("VCN: %d - %d" % (start_vcn, end_vcn))

        # get offset to runlist 32-33
        offset_to_rl = unpack("<H", attr[32:34])[0]
        print ("Start of RL = %d" % offset_to_rl)
        self.parse_runlist(attr, attr_type, offset_to_rl)

        if attr_type == 128:
            print ("Parsing $DATA")
            print ("Runlist:  %s" % self._runlist)

    def parse_runlist(self, attr, attr_type, offset):
        """
        Parses the runlist of a non-resident attribute.
        Attributes:
            first_byte (byte): first byte of a runlist entry, determines how long the
                the runlist field and offset field are
            offset (int): current offset in the runlist
            prev_rl_offset (int): previous offset runlist offset
            offset_field (int): number of bytes in the offset field
            rl_field (int): number of bytes in the runlist length field
            rl_length (int): runlist length / number of clusters in the runlist
            rl_offset (int): offset to starting cluster in the runlist
            start_cluster (int): first cluster in the runlist
            end_cluster (int): last cluster in the runlist
        Prints:
            Important runlist related values
        """

        first_byte = attr[offset:offset + 1]  # read first byte
        offset += 1
        prev_rl_offset = 0

        while (first_byte != b"\x00"):  # indicates end of rl
            print ("First byte: 0x" + ''.join('{:x}'.format(b) for b in reversed(first_byte)))

            # get offset field by shifting byte to get the first 4 nibbles
            offset_field = unpack("<B", first_byte)[0] >> 4
            print ("Length of offset field: %d" % offset_field)

            # get runlist field by masking to get the second 4 nibbles
            rl_field = unpack("<B", first_byte)[0] & 0b00001111
            print ("Length of RL field: %d" % rl_field)

            # get the length of the runlist
            rl_length = getSigned(attr[offset:offset + rl_field])
            offset += rl_field
            print ("Runlist length: %d" % rl_length)

            # get the runlist offset
            rl_offset = getSigned(attr[offset:offset + offset_field])
            offset += offset_field
            print ("Runlist offset: %d" % rl_offset)

            start_cluster = prev_rl_offset + rl_offset
            end_cluster = start_cluster + rl_length - 1
            print ("Clusters go from: %d - %d" % (start_cluster, end_cluster))
            if attr_type == 128:
                self._runlist.extend(range(start_cluster, end_cluster + 1))

            # set up for next item in the runlist
            prev_rl_offset = rl_offset
            first_byte = attr[offset:offset + 1]
            offset += 1
            print ("")


class STD_INFO(object):
    """
    Parses the $STD_INFO attribute of the $MFT.
    Variables:
        _attr (bytes): the attribute being parsed
        _content_size (int): the size of the attribute content
        _content_offset (int): the offset to the attribute content
        _content (bytes): the content being parsed
        _file_creation (datetime): when the file was created
        _file_altered (datetime): when the file was last altered
        _mft_altered (datetime): when the mft was last altered
        _file_accessed (datetime): when the file was last accessed
        _flags (int/string): flag value and flag strings
        _num_versions (int): maximum number of versions
        _class_id (int): class ID
        _owner_id (int): owner ID
        _security_id (int): security ID
        _quota (int): quota charged
        _usn (int): update sequence number
    Functions:
        parse()
        print_fields()
    """

    def __init__(self, attribute, content_size, content_offset):
        self._attr = attribute
        self._content_size = content_size
        self._content_offset = content_offset

    def parse(self):
        print ("\tParsing $STANDARD_INFO")

        # read in content
        self._content = self._attr[self._content_offset:self._content_size
                                                        + self._content_offset]

        # get creation time 0-7
        self._file_creation = convert_time(self._content[0:8])

        # get file altered time 8-15
        self._file_altered = convert_time(self._content[8:16])

        # get MFT altered time 16-23
        self._mft_altered = convert_time(self._content[16:24])

        # get file accessed time 24-31
        self._file_accessed = convert_time(self._content[24:32])

        # get flags 32-35
        self._flags = unpack("<L", self._content[32:36])[0]
        self._flags = check_flags(self._flags)

        # get maximum number of versions 36-39
        self._num_versions = unpack("<L", self._content[36:40])[0]

        # get version number 40-43
        self._version = unpack("<L", self._content[40:44])[0]

        # get class id 44-47
        self._class_id = unpack("<L", self._content[44:48])[0]

        # get owner id 48-51
        self._owner_id = unpack("<L", self._content[48:52])[0]

        # get security id 52-55
        self._security_id = unpack("<L", self._content[52:56])[0]

        # get quota charged 56-63
        self._quota = unpack("<2L", self._content[56:64])[0]

        # update sequence number 64-71
        self._usn = unpack("<2L", self._content[64:72])[0]

        self.print_fields()

    def print_fields(self):
        print ("\t file accessed \t %s" % self._file_accessed)
        print ("\t      Owner ID \t %s" % self._owner_id)
        print ("\tversion number \t %s" % self._version)
        print ("\t creation time \t %s" % self._file_creation)
        print ("\t   Security ID \t %s" % self._security_id)
        print ("\t   mft altered \t %s" % self._mft_altered)
        print ("\t  Update seq # \t %s" % self._usn)
        print ("\t         flags \t %s" % self._flags)
        print ("\tmax # versions \t %s" % self._num_versions)
        print ("\t      Class ID \t %s" % self._class_id)
        print ("\t Quota Charged \t %s" % self._quota)
        print ("\t  file altered \t %s" % self._file_altered)


class FILE_NAME(object):
    """
    Parses the $FILE_NAME attribute in the $MFT.
    Variables:
        _attr (bytes): the attribute being parsed
        _content_size (int): size of the attribute content
        _content_offset (int): offset to the attribute content
        _content (bytes): the content being parsed
        _parent_dir (int): file reference of the parent directory
        _file_creation (datetime): when the file was created
        _file_modification (datetime): when the file was last modified
        _file_access (datetime): when the file was last accessed
        _alloc_size (int): the allocated size of the file
        _real_size (int): the real size of the file
        _flags (int/string): flag value and flag strings
        _reparse (int): reparse value
        _name_length (int): length of name
        _namespace (int): namespace value
        _name (string): file name
    Functions:
        parse()
        print_fields()
    """

    def __init__(self, attribute, content_size, content_offset):
        self._attr = attribute
        self._content_size = content_size
        self._content_offset = content_offset

    def parse(self):
        """
        Parses the $FILE_NAME attribute.
        """
        print ("\tParsing $FILE_NAME")

        # read in content
        self._content = self._attr[self._content_offset:self._content_size
                                                        + self._content_offset]

        # get file reference of parent directory 0-7
        self._parent_dir = unpack("<2L", self._content[0:8])[0]

        # get file creation time 8-15
        self._file_creation = convert_time(self._content[8:16])

        # get file modification time 16-23
        self._file_modification = convert_time(self._content[16:24])

        # get MFT modification time 24-31
        self._mft_modification = convert_time(self._content[24:32])

        # get file access time 32-39
        self._file_access = convert_time(self._content[32:40])

        # get allocated size of the file 40-47
        self._alloc_size = unpack("<2L", self._content[40:48])[0]

        # get real size of the file 48-55
        self._real_size = unpack("<2L", self._content[48:56])[0]

        # get flags 56-59
        self._flags = unpack("<L", self._content[56:60])[0]
        self._flags = check_flags(self._flags)

        # get reparse value 60-63
        self._reparse = unpack("<L", self._content[60:64])[0]

        # get length of name 64-64
        self._name_length = unpack("<B", self._content[64:65])[0]

        # get namespace 65-65
        self._namespace = unpack("<B", self._content[65:66])[0]

        # get name 66+
        self._name = self._content[66:].decode("utf-8")

        self.print_fields()

    def print_fields(self):
        print ("   Alloc. size of file \t %d" % self._alloc_size)
        print ("\tLength of name\t %d" % self._name_length)
        print ("\t  MFT mod time \t %s" % self._mft_modification)
        print ("\t          Name \t %s" % self._name)
        print ("\t     Namespace \t %d" % self._namespace)
        print ("\t    Parent dir \t %d" % self._parent_dir)
        print ("\t Real filesize \t %d" % self._real_size)
        print ("\t Reparse value \t %d" % self._reparse)
        print ("      file access time \t %s" % self._file_access)
        print ("    file creation time \t %s" % self._file_creation)
        print ("\t file mod time \t %s" % self._file_modification)
        print ("\t         flags \t %s" % self._flags)


# functions needed by all classes

def convert_time(time):
    """
    Converts windows time to datetime.
    Attributes:
        D (int): a constant for the conversion
        epoch (int): time in epoch time
    Returns:
        epoch as a datetime string
    """
    D = 116444736000000000
    time = getSigned(time)
    epoch = (time - D) / 10000000
    return str(datetime.datetime.fromtimestamp(epoch))


def getSigned(bytes):
    """
    Find the length and pad it to 8 bytes after checking the correct
    bit, unpack and return
    8 bytes is called a long-long and is represented as a 'q' in the
    unpack command: unpack ("<q", ...)[0]
    You can concatenate multiple bytes with "multiplication"
    "\x00*2
    Assume little endian
    Attributes:
        length (int): length of bytes
        pads (int): number of bytes that need to be added
        sig (int): the signed bit
    Returns:
        bytes with the correct length and sign
    """

    length = len(bytes)
    # print ("len: %d" %length)

    if length < 8:
        pads = 8 - length

        sig = bytes[length - 1]

        sig = sig >> 7

        # if positive pad with 00
        if sig == 0:
            return unpack("<q", bytes + b'\x00' * pads)[0]
        # if negative pad with FF
        elif sig == 1:
            return unpack("<q", bytes + b'\xFF' * pads)[0]

    else:
        return unpack("<q", bytes)[0]


def check_flags(flags):
    """
    Determine which flags the attribute has given the flag field.

    Attributes:
        strings (string): string of the attribute's flags
    Returns:
        string of the flags found from the given flag field
    """

    strings = ""

    # check for 0x0001, 0x0002, 0x0004 flags
    if flags & 0b0001 == 1: strings += "Read Only "
    if flags & 0b0010 == 2: strings += "Hidden "
    if flags & 0b0100 == 4: strings += "System "

    # check for 0x0020, 0x0040, 0x0080 flags
    if flags & 0b00100000 == 32: strings += "Archive "
    if flags & 0b01000000 == 64: strings += "Device "
    if flags & 0b10000000 == 128: strings += "#Normal "

    # check for 0x0100, 0x0200, 0x0400, 0x0800 flags
    if flags & 0b000100000000 == 256: strings += "Temporary "
    if flags & 0b001000000000 == 512: strings += "Sparse file "
    if flags & 0b010000000000 == 1024: strings += "Reparse point "
    if flags & 0b100000000000 == 2048: strings += "Compressed "

    # check for 0x1000, 0x2000, 0x4000 flags
    if flags & 0b0001000000000000 == 4096: strings += "Offline "
    if flags & 0b0010000000000000 == 8192:
        strings += "Content is not being indexed for faster searches "
    if flags & 0b0100000000000000 == 16384: strings += "Encrypted "

    return strings


# --------------------------------

def usage():
    """ Print usage string and exit() """
    print("Usage:\n%s <entry to parse> <image.dmg>\n" % sys.argv[0])
    sys.exit()


def main():
    """ Simple arg check and runs """
    if len(sys.argv) == 3:
        istat = NTFS(sys.argv[1], sys.argv[2])
        istat.run()
    else:
        usage()


# Standard boilerplate to run main()
if __name__ == '__main__':
    main()
