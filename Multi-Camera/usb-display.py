#
# From USB  to Display
#
import argparse
import sys
sys.path.append('../')
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.create_element_or_error import create_element_or_error
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call

def main():

   cameras_list = [
       {"source": "/dev/video0", "name": "Camera 1"},
       {"source": "/dev/video1", "name": "Camera 1"},
    ]

    GObject.threads_init()
    Gst.init(None)

    pipeline = Gst.Pipeline()

    if not pipeline:
        print("Unable to create Pipeline")
        exit(0)

    streammux = create_element_or_error("nvstreammux", "stream-muxer")
    pipeline.add(streammux)

    for camera in cameras_list:
        source = create_element_or_error("v4l2src", "source-" + camera['name'])
        source.set_property('device', camera["source"])
        caps = create_element_or_error("capsfilter", "source-caps-source-1")
        caps.set_property('caps', Gst.Caps.from_string("video/x-raw, framerate=30/1"))
    
    pipeline.add(source)
    pipeline.add(caps)

    sinkpad = streammux.get_request_pad('sink_0')
    srcpad = source.get_static_pad("src")

    if not sinkpad:
        print("Unable to create source sink pad")
        exit(0)
    if not srcpad:
        print("Unable to create source src pad")
        exit(0)
    srcpad.link(sinkpad)

    pgie = create_element_or_error("nvinfer", "primary-inference")
    tracker = create_element_or_error("nvtracker", "tracker")
    convertor = create_element_or_error("nvvideoconvert", "converter-1")
    tiler = create_element_or_error("nvmultistreamtiler", "nvtiler")
    convertor2 = create_element_or_error("nvvideoconvert", "converter-2")
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "nvvideo-renderer")

    queue1=create_element_or_error("queue","queue1")
    queue2=create_element_or_error("queue","queue2")
    queue3=create_element_or_error("queue","queue3")
    queue4=create_element_or_error("queue","queue4")
    queue5=create_element_or_error("queue","queue5")
    queue6=create_element_or_error("queue","queue6")

    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(queue3)
    pipeline.add(queue4)
    pipeline.add(queue5)
    pipeline.add(queue6)

    # Set Element Properties
    streammux.set_property('live-source', 1)
    streammux.set_property('width', 1280)
    streammux.set_property('height', 720)
    streammux.set_property('num-surfaces-per-frame', 1)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)

    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")

    tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvdcf.so')
    tracker.set_property('enable-batch-process', 1)
    tracker.set_property('tracker-width', 640)
    tracker.set_property('tracker-height', 480)

    tiler.set_property("rows", 1)
    tiler.set_property("columns", 1)
    tiler.set_property("width", 1280)
    tiler.set_property("height", 720)
    sink.set_property("qos", 0)

    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(pgie)
    pipeline.add(tracker)
    pipeline.add(tiler)
    pipeline.add(convertor)
    pipeline.add(nvosd)
    pipeline.add(transform)
    pipeline.add(sink)

    # Link the elements together:
    print("Linking elements in the Pipeline")

    streammux.link(queue1)
    queue1.link(pgie)
    pgie.link(queue2)
    queue2.link(tracker)
    tracker.link(queue3)
    queue3.link(tiler)
    tiler.link(queue4)
    queue4.link(convertor)
    convertor.link(queue5)
    queue5.link(nvosd)
    nvosd.link(queue6)
    queue6.link(transform)
    transform.link(sink)
    
    # Create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()

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


