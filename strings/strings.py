import argparse


def read_file(file, encoding, min_len):

    if encoding == 's':

        data = file.read(1)
        str = ""

        while data:
            d = data[0]
            # if printable char add to string
            if d > 31 and d < 127:
                str += chr(d)
            # else its a non-printable
            elif len(str) >= min_len:
                print (str)
                str = ""
            else:
                str = ""
            data = file.read(1)

        if len(str) >= min_len:
            print (str)

    if encoding == 'l':

        data = file.read(2)
        str = ""

        while data:
            d = int.from_bytes(data, byteorder="little")
            # if printable
            if d > 31 and d < 127:
                str += chr(d)
            # else non-printable
            elif len(str) >= min_len:
                print (str)
                str = ""
            else:
                str = ""
            data = file.read(2)

        if len(str) >= min_len:
            print (str)

    if encoding == 'b':

        data = file.read(2)
        str = ""

        while data:
            d = int.from_bytes(data, byteorder="big")
            # if printable
            if d > 31 and d < 127:
                str += chr(d)
            # else non-printable
            elif len(str) >= min_len:
                print (str)
                str = ""
            else:
                str = ""
            data = file.read(2)

        if len(str) >= min_len:
            print (str)



def print_strings(file_obj, encoding, min_len):
    # Right now all this function does is print its arguments.
    # You'll need to replace that code with code that actually finds and prints the strings!
    print(file_obj.name)
    print(encoding)
    print(min_len)

def main():
    parser = argparse.ArgumentParser(description='Print the printable strings from a file.')
    parser.add_argument('filename')
    parser.add_argument('-n', metavar='min-len', type=int, default=4,
                        help='Print sequences of characters that are at least min-len characters long')
    parser.add_argument('-e', metavar='encoding', choices=('s', 'l', 'b'), default='s',
                        help='Select the character encoding of the strings that are to be found. ' +
                             'Possible values for encoding are: s = UTF-8, b = big-endian UTF-16, ' +
                             'l = little endian UTF-16.')
    args = parser.parse_args()

    # with open(args.filename, 'rb') as f:
    #     print_strings(f, args.e, args.n)

    with open(args.filename, 'rb') as f:
        read_file(f, args.e, args.n)



if __name__ == '__main__':
    main()

# print(d)
# print(chr(d))
# print('{:08b}'.format(d))