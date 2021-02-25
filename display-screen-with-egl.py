#
#
# Display the Image on the Screen using the EGL Sink of Nvidia
#
#
import argparse
import sys
sys.path.append('../')

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
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
    
    # gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! nvvidconv ! nvegltransform ! nveglglessink
    # Create Elements
    source = create_element_or_error("nvarguscamerasrc", "camera-source")
    convertor = create_element_or_error("nvvidconv", "converter-1")
    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "egl-overlay")

    # Set Element Properties
    source.set_property('sensor-id', 0)
    source.set_property('bufapi-version', True)
    
    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(source)
    pipeline.add(convertor)
    pipeline.add(sink)
    pipeline.add(transform)


    # Link the elements together:
    print("Linking elements in the Pipeline")
    source.link(convertor)
    convertor.link(transform)
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


gst-launch-1.0 nvarguscamerasrc bufapi-version=true sensor-id=0 ! "video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1,format=NV12" ! m.sink_0 nvstreammux name=m batch-size=1 width=1280 height=720 ! nvinfer config-file-path=/opt/nvidia/deepstream/deepstream-5.0/samples/configs/deepstream-app/config_infer_primary.txt ! nvtracker tracker-width=640 tracker-height=480 ll-lib-file=/opt/nvidia/deepstream/deepstream-5.0/lib/libnvds_mot_klt.so enable-batch-process=1 ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=RGBA" ! nvmultistreamtiler ! nvdsosd ! nvvideoconvert ! nvegltransform ! nveglglessink