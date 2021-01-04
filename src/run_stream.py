from ffmpeg_streaming import Formats, Bitrate, Representation, Size
import ffmpeg_streaming

_480p  = Representation(Size(854, 480), Bitrate(750 * 1024, 192 * 1024))

video = ffmpeg_streaming.input('video/00018.MTS')

hls = video.hls(Formats.h264(), hls_list_size=10, hls_time=5)
hls.flags('delete_segments')
hls.representations(_480p)
hls.output('playlist/hls.m3u8', ffmpeg_bin='/usr/local/bin/ffmpeg', async_run=False)