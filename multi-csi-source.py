#
# Publish video to Ant Server
#
import argparse
import sys
sys.path.append('../')
import math
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
from common.create_element_or_error import create_element_or_error

def main():

    GObject.threads_init()
    Gst.init(None)

    pipeline = Gst.Pipeline()
    if not pipeline:
        print("Unable to create Pipeline")
        return False

    streammux = create_element_or_error("nvstreammux", "Stream-muxer")
    pipeline.add(streammux)

    source = create_element_or_error("nvarguscamerasrc", "camera-source-1")
    source.set_property('sensor-id', 0)
    source.set_property('bufapi-version', True)
    pipeline.add(source)

    sinkpad1 = streammux.get_request_pad('sink_0') 
    if not sinkpad1:
        print("Unable to create sink pad bin")
        exit(0)
    srcpad1 = source.get_static_pad("src")
    if not srcpad1:
        print("Unable to create src pad bin \n")
        exit(0)
    srcpad1.link(sinkpad1)

    source2 = create_element_or_error("nvarguscamerasrc", "camera-source-2")
    source2.set_property('sensor-id', 1)
    source2.set_property('bufapi-version', True)
    pipeline.add(source2)

    sinkpad2 = streammux.get_request_pad('sink_1') 
    if not sinkpad2:
        print("Unable to create sink pad bin")
        exit(0)
    srcpad2 = source2.get_static_pad("src")
    if not srcpad2:
        print("Unable to create src pad bin \n")
        exit(0)
    srcpad2.link(sinkpad2)

    tiler = create_element_or_error("nvmultistreamtiler", "nvtiler")
    nvvidconv = create_element_or_error("nvvideoconvert", "converter-1")
    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "nvvideo-renderer")

    queue1=create_element_or_error("queue","queue1")
    queue2=create_element_or_error("queue","queue2")
    queue3=create_element_or_error("queue","queue3")
    queue4=create_element_or_error("queue","queue4")

    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(queue3)
    pipeline.add(queue4)

    # Set Element Properties
    streammux.set_property('live-source', 1)
    streammux.set_property('width', 1280)
    streammux.set_property('height', 720)
    streammux.set_property('num-surfaces-per-frame', 1)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)

    tiler.set_property("rows", 2)
    tiler.set_property("columns", 2)
    tiler.set_property("width", 1280)
    tiler.set_property("height", 720)
    sink.set_property("qos", 0)

    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(tiler)
    pipeline.add(nvvidconv)
    pipeline.add(transform)
    pipeline.add(sink)

    # Link the elements together:
    print("Linking elements in the Pipeline")

    streammux.link(queue1)
    queue1.link(tiler)
    tiler.link(queue2)
    queue2.link(nvvidconv)
    nvvidconv.link(queue3)
    queue3.link(transform)
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


