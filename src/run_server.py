import sys

import junk_messenger as jm


def main():
    svr = jm.JunkThreadingHTTPServer(('127.0.0.1', int(sys.argv[1])),
                                     jm.JunkHTTPRequestHandler)
    print('Start server')
    svr.serve_forever()


if __name__ == '__main__':
    main()
