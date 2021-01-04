import queue
import threading
import time
import urllib.error
import urllib.request
import av
import m3u8

import junk_messenger as jm


class SegmentGenerator(threading.Thread):
    def __init__(self, source):
        super().__init__()
        self.setDaemon(True)
        self.source = source
        self.interrupted = False

    def run(self):
        print("Submitter started.")
        num_segments = 0

        stream = next(s for s in self.source.streams if s.type == 'video')
        stream_it = self.source.demux(stream)

        while not self.interrupted:
            filename = 'seg-%d.ts' % num_segments
            print("Generating segment: %s" % filename)
            num_segments += 1
            duration, frame_count = self.gen_segment(filename,
                                                     stream_it,
                                                     width=stream.width,
                                                     height=stream.height)
            print("Segment generated: (%s, %f, %d)" %
                  (filename, duration, frame_count))

    def gen_segment(self,
                    out_filename,
                    in_stream,
                    bit_rate=1000000,
                    vcodec='h264',
                    width=680,
                    height=480,
                    pix_fmt='yuv420p',
                    frame_rate=20,
                    duration=2):

        out_container = av.open(out_filename, 'w')

        out_vstream = out_container.add_stream(vcodec, str(frame_rate))
        out_vstream.bit_rate = bit_rate
        out_vstream.pix_fmt = pix_fmt
        out_vstream.width = width
        out_vstream.height = height
        secs_per_frame = 1.0 / frame_rate
        frame_count = 0
        segment_start_time = time.time()

        for packet in in_stream:
            start_time = time.time()

            for frame in packet.decode():
                frame.pts = None
                out_packet = out_vstream.encode(frame)
                frame_count += 1
                if out_packet:
                    out_container.mux(out_packet)

            if time.time() - segment_start_time > duration:
                break

            time_to_wait = secs_per_frame - (time.time() - start_time)
            if time_to_wait > 0:
                try:
                    time.sleep(time_to_wait)
                except KeyboardInterrupt:
                    self.interrupted = True
                    break

        out_container.close()
        segment_duration = time.time() - segment_start_time
        return segment_duration, frame_count

