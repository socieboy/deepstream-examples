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
    print("Creating Pipeline")
    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write("Unable to create Pipeline")
    
    print("Creating Elements")
    source = create_element_or_error("nvarguscamerasrc", "camera-source")
    caps = create_element_or_error("capsfilter", "source-caps-source")
    caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1,format=NV12"))
    convertor = create_element_or_error("nvvidconv", "converter-1")
    s_encoder = create_element_or_error("jpegenc", "snapshot-encoder")
    s_sink = create_element_or_error("filesink", "snapshot-sink")

    print("Set element properties")
    source.set_property('sensor-id', 1)
    source.set_property('num-buffers', 1)
    s_sink.set_property('location', 'python-test.jpeg')
    
    print("Adding elements to Pipeline")
    pipeline.add(source)
    pipeline.add(caps)
    pipeline.add(convertor)
    pipeline.add(s_encoder)
    pipeline.add(s_sink)

    print("Linking elements in the Pipeline")
    source.link(caps)
    caps.link(convertor)
    convertor.link(s_encoder)
    s_encoder.link(s_sink)

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