#
# Author: Frank Sepulveda
# Email: socieboy@gmail.com
#
# Publish stream to RTMP server
#
import sys, gi
sys.path.append("../")
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.bus_call import bus_call
from common.create_element_or_error import create_element_or_error


# VIDEO_OUTPUT_WIDTH=2560
# VIDEO_OUTPUT_HEIGHT=1440
VIDEO_OUTPUT_WIDTH=720
VIDEO_OUTPUT_HEIGHT=440

def main():
    
    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create Pipeline Element
    pipeline = Gst.Pipeline()
    if not pipeline:
        print("Unable to create Pipeline")
        return False
    
    # Create GST Elements
    source = create_element_or_error("nvarguscamerasrc", "camera-source")
    caps = create_element_or_error("capsfilter", "source-caps-source")
    caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM),width=" + str(VIDEO_OUTPUT_WIDTH) + ",height=" + str(VIDEO_OUTPUT_HEIGHT) + ",framerate=30/1,format=NV12"))

    encoder = create_element_or_error("nvv4l2h264enc", "encoder")
    parser = create_element_or_error("h264parse", "parser")
    muxer = create_element_or_error("flvmux", "muxer")
    sink = create_element_or_error("rtmpsink", "sink")

    # Set Element Properties
    source.set_property('sensor-id', 1)
    sink.set_property('location', 'rtmp://media.streamit.live/LiveApp/stream-test')

    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(source)
    pipeline.add(caps)
    pipeline.add(encoder)
    pipeline.add(parser)
    pipeline.add(muxer)
    pipeline.add(sink)

    # Link the elements together:
    print("Linking elements in the Pipeline")
    source.link(caps)
    caps.link(encoder)
    encoder.link(parser)
    parser.link(muxer)
    muxer.link(sink)
    
    # Create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    # Start play back and listen to events
    print("Starting pipeline")
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except:
        pass

    # Cleanup
    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    sys.exit(main())
