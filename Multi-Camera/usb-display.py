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
from common.bus_call import bus_call

def main():

    cameras_list = [
        {"index" : 0, "source": "/dev/video0", "name": "Camera-1"},
        # {"index" : 1, "source": "/dev/video1", "name": "Camera-2"},
    ]

    GObject.threads_init()
    Gst.init(None)

    pipeline = Gst.Pipeline()

    if not pipeline:
        print("Unable to create Pipeline")
        exit(0)

    # Muxer
    muxer = create_element_or_error("nvstreammux", "stream-muxer")
    muxer.set_property('live-source', True)
    muxer.set_property('width', 1280)
    muxer.set_property('height', 720)
    muxer.set_property('num-surfaces-per-frame', 1)
    muxer.set_property('batch-size', 1)
    muxer.set_property('batched-push-timeout', 4000000)
    pipeline.add(muxer)

    # Sources
    for camera in cameras_list:
        
        # Source
        source = create_element_or_error("nvv4l2camerasrc", "source-" + camera['name'])
        source.set_property('device', camera["source"])
        source.set_property('do-timestamp', True)
        source.set_property('bufapi-version', True)
        pipeline.add(source)

        # Caps
        caps = create_element_or_error("capsfilter", "source-caps-source-1")
        caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080, framerate=(fraction)30/1, format=(string)UYVY"))
        pipeline.add(caps)
        source.link(caps)

        convertor = create_element_or_error("nvvideoconvert", "converter-1")
        pipeline.add(convertor)
        caps.link(convertor)

        srcpad = convertor.get_static_pad("src")
        sinkpad = muxer.get_request_pad('sink_' + str(camera['index']))

        if not sinkpad:
            print("Unable to create source sink pad")
            exit(0)
        if not srcpad:
            print("Unable to create source src pad")
            exit(0)
        srcpad.link(sinkpad)

    pgie = create_element_or_error("nvinfer", "primary-inference")
    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")
    pipeline.add(pgie)
    muxer.link(pgie)

    tracker = create_element_or_error("nvtracker", "tracker")
    tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvdcf.so')
    tracker.set_property('enable-batch-process', 1)
    tracker.set_property('tracker-width', 640)
    tracker.set_property('tracker-height', 480)
    pipeline.add(tracker)
    pgie.link(tracker)

    tiler = create_element_or_error("nvmultistreamtiler", "nvtiler")
    tiler.set_property("rows", 1)
    tiler.set_property("columns", 1)
    tiler.set_property("width", 1280)
    tiler.set_property("height", 720)
    pipeline.add(tiler)
    tracker.link(tiler)

    convertor2 = create_element_or_error("nvvideoconvert", "converter-2")
    pipeline.add(convertor2)
    tiler.link(convertor2)

    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    pipeline.add(nvosd)
    convertor2.link(nvosd)

    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    pipeline.add(transform)
    nvosd.link(transform)

    sink = create_element_or_error("nveglglessink", "nvvideo-renderer")
    pipeline.add(sink)
    transform.link(sink)

    loop = GObject.MainLoop()

    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except:
        pass

    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    sys.exit(main())


