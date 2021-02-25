#
# Publish video to Ant Server
#
import argparse
import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.create_element_or_error import create_element_or_error

def main():

    cameras_list = [
        {"source": 0, "name": "Camera 1",},
        {"source": 1, "name": "Camera 2"},
    ]
    
    GObject.threads_init()
    Gst.init(None)

    pipeline = Gst.Pipeline()

    if not pipeline:
        print("Unable to create Pipeline")
        exit(0)

    streammux = create_element_or_error("nvstreammux", "Stream-muxer")
    pipeline.add(streammux)

    for camera in cameras_list:
        source = create_element_or_error("nvarguscamerasrc", "source-" + str(camera['name']))
        source.set_property('sensor-id', camera['source'])
        source.set_property('bufapi-version', True)
        pipeline.add(source)

        sinkpad = streammux.get_request_pad('sink_' + str(camera['source']))
        srcpad = source.get_static_pad("src")

        if not sinkpad:
            print("Unable to create source sink pad")
            exit(0)
        if not srcpad:
            print("Unable to create source src pad")
            exit(0)
        srcpad.link(sinkpad)

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


