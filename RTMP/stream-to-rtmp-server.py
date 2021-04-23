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
VIDEO_OUTPUT_HEIGHT=480

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
    caps = create_element_or_error("capsfilter", "source-caps")
    caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080, framerate=30/1, format=(string)NV12"))
    converter = create_element_or_error('nvvidconv', 'converter')
    capsConverter = create_element_or_error("capsfilter", "converter-caps")
    capsConverter.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)720, height=(int)480, framerate=30/1, format=(string)NV12"))
    encoder = create_element_or_error("nvv4l2h264enc", "encoder")
    parser = create_element_or_error("h264parse", "parser")
    muxer = create_element_or_error("flvmux", "muxer")
    queue = create_element_or_error("queue", "queue")
    sink = create_element_or_error("rtmpsink", "sink")

    # Set Element Properties
    # converter.set_property('flip-method', 1)
    encoder.set_property('bitrate', 4000000)
    encoder.set_property('maxperf-enable', True)
    source.set_property('sensor-id', 1)
    source.set_property('do-timestamp', True)
    muxer.set_property('streamable', True)
    sink.set_property('location', 'rtmp://media.streamit.live/LiveApp/stream-test')

    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(source)
    pipeline.add(caps)
    pipeline.add(converter)
    pipeline.add(capsConverter)
    pipeline.add(encoder)
    pipeline.add(parser)
    pipeline.add(muxer)
    pipeline.add(queue)
    pipeline.add(sink)

    # Link the elements together:
    print("Linking elements in the Pipeline")
    source.link(caps)
    caps.link(converter)
    converter.link(capsConverter)
    capsConverter.link(encoder)
    encoder.link(parser)
    parser.link(muxer)
    muxer.link(queue)
    queue.link(sink)
    
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
