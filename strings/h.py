import sys

def hexdump():
    with open(sys.argv[1], 'rb') as f:

        bytes = f.read(16)
        if not bytes:
            return

        offset = 0

        while bytes:
            print('{:08x}'.format(offset),end = '  ')

            hexValues = ''
            for h in range(0,len(bytes)):
                if h == 8:
                    hexValues += ' '
                h = bytes[h]
                h = hex(h).replace('0x','')
                if len(h) == 1:
                    h = '0' + h;
                hexValues += h + ' '
            print (hexValues.ljust(49), end = ' ')

            perusal = ''
            for p in bytes:
                if 0x20 <= p < 0x7F:
                    perusal += chr(p)
                else:
                    perusal += '.'
            print ('|' + perusal + '|')

            offset += len(bytes)
            bytes = f.read(16)
        print ('{:08x}'.format(offset), end = '\n')


if __name__ == "__main__":
    hexdump()


