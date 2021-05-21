#
# Author: Frank Sepulveda
# Email: socieboy@gmail.com
#
# The folowing example records the video of the CSI Camera to a MP4 File, Encoded h265
#
# gst-launch-1.0 nvarguscamerasrc num-buffers=1 ! 'video/x-raw(memory:NVMM), width=(int)1280, height=(int)720, format=(string)NV12, framerate=(fraction)30/1' ! nvvidconv ! jpegenc ! filesink location=test.jpg
#
import sys, gi
sys.path.append("../")
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.bus_call import bus_call
from common.create_element_or_error import create_element_or_error

def main():
    
    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create Pipeline Element
    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write("Unable to create Pipeline")
    
    # Source
    source = create_element_or_error("nvarguscamerasrc", "camera-source")
    source.set_property('sensor-id', 1)
    pipeline.add(source)

    # Convertor
    convertor = create_element_or_error("nvvidconv", "converter-1")
    pipeline.add(convertor)
    source.link(convertor)

    # Video Rate
    videorate = create_element_or_error("videorate", "videorate")
    pipeline.add(videorate)
    convertor.link(videorate)

    # Video Rate Caps
    videoRateCaps = create_element_or_error("capsfilter", "videorate-caps-source")
    videoRateCaps.set_property("caps", Gst.Caps.from_string("video/x-raw,framerate=1/5"))
    pipeline.add(videoRateCaps)
    videorate.link(videoRateCaps)

    # Encoder
    encoder = create_element_or_error("nvjpegenc", "snapshot-encoder")
    pipeline.add(encoder)
    videoRateCaps.link(encoder)

    # File Sink
    sink = create_element_or_error("multifilesink", "snapshot-sink")
    sink.set_property('location', 'snapshot-%05d.jpg')
    pipeline.add(sink)
    encoder.link(sink)

    # Create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    # Start play back and listen to events
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except:
        pass


    # Cleanup
    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    sys.exit(main())