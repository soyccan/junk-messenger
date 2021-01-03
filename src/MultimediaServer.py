#  https://samkuo.me/post/2015/12/http-live-streaming-on-osx-camera-with-python/
import http.server
import av

import segment_generator
from common import *


class MultimediaServer(http.server.ThreadingHTTPServer):
    pass


class MultimediaRequestHandler(http.server.SimpleHTTPRequestHandler):
    pass


def main():
    # source = av.open(format='avfoundation', file='0')
    source = av.open('../video/00018.MTS')

    print("Number of streams in source: %d" % len(source.streams))
    seggen = segment_generator.SegmentGenerator(source)
    seggen.start()

    svr = MultimediaServer(ADDR, MultimediaRequestHandler)
    svr.serve_forever()


if __name__ == '__main__':
    main()