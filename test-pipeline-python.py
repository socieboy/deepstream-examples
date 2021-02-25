import argparse
import sys
sys.path.append('../')
import gi
gi.require_version('Gst', '1.0')
import time
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
from common.create_element_or_error import create_element_or_error
from common.object_detection import osd_sink_pad_buffer_probe

def main():
    
    GObject.threads_init()
    Gst.init(None)


    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write("Unable to create Pipeline")
        return
    
    source = create_element_or_error("nvarguscamerasrc", "camera-source")
    caps = create_element_or_error("capsfilter", "source-caps")
    caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM),width=1640,height=1232,framerate=30/1,format=NV12"))

    streammux = create_element_or_error("nvstreammux", "Stream-muxer")
    pgie = create_element_or_error("nvinfer", "primary-inference")
    tracker = create_element_or_error("nvtracker", "tracker")
    convertor = create_element_or_error("nvvideoconvert", "converter-1")
    caps2 = create_element_or_error("capsfilter", "source-caps-definition")
    caps2.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM),format=RGBA"))
    tiler = create_element_or_error("nvmultistreamtiler", "tiler")
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    convertor2 = create_element_or_error("nvvideoconvert", "convertor-2")
    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "egl-overlay")

    # Set Element Properties
    source.set_property('sensor-id', 0)
    source.set_property('bufapi-version', True)
    
    streammux.set_property('live-source', 1)
    streammux.set_property('width', 1280)
    streammux.set_property('height', 720)
    streammux.set_property('num-surfaces-per-frame', 1)
    streammux.set_property('nvbuf-memory-type', 4)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)

    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream-5.0/samples/configs/deepstream-app/config_infer_primary.txt")

    tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream-5.0/lib/libnvds_nvdcf.so')
    tracker.set_property('enable-batch-process', 1)
    tracker.set_property('tracker-width', 640)
    tracker.set_property('tracker-height', 480)


    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(source)
    pipeline.add(caps)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(tracker)
    pipeline.add(convertor)
    pipeline.add(tiler)
    pipeline.add(nvosd)
    pipeline.add(convertor2)
    pipeline.add(caps2)
    pipeline.add(transform)
    pipeline.add(sink)

    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        sys.stderr.write("Unable to get the sink pad of streammux")

    # Link the elements together
    print("Linking elements in the Pipeline")
    source.link(caps)
    caps.link(streammux)
    streammux.link(pgie)
    pgie.link(tracker)
    tracker.link(convertor)
    convertor.link(tiler)
    tiler.link(nvosd)
    nvosd.link(convertor2)
    convertor2.link(caps2)
    caps2.link(transform)
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