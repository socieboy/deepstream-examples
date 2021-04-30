#
# Author: Frank Sepulveda
# Email: socieboy@gmail.com
#
# Display camera on screen using "nveglglessink"
#
# gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! nvvidconv ! nvegltransform ! nveglglessink
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
        sys.stderr.write(" Unable to create Pipeline")
    
    # Create Elements
    source = create_element_or_error("nvarguscamerasrc", "camera-source")
    caps = create_element_or_error("capsfilter", "source-caps")
    caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080, framerate=30/1, format=(string)NV12"))
    convertor = create_element_or_error('nvvidconv', 'converter')
    capsConverter = create_element_or_error("capsfilter", "converter-caps")
    capsConverter.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)720, height=(int)480, framerate=30/1, format=(string)NV12"))
    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "egl-overlay")

    # Set Element Properties
    source.set_property('sensor-id', 0)
    
    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(source)
    pipeline.add(caps)
    pipeline.add(convertor)
    pipeline.add(capsConverter)
    pipeline.add(transform)
    pipeline.add(sink)

    # Link the elements together:
    print("Linking elements in the Pipeline")
    source.link(caps)
    caps.link(convertor)
    convertor.link(capsConverter)
    capsConverter.link(transform)
    transform.link(sink)

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