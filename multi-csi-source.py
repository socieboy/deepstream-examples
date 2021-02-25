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

def new_pad_added(bin, src_pad, data):
    print("In cb_newpad")
    caps = src_pad.get_current_caps()
    gststruct = caps.get_structure(0)
    gstname = gststruct.get_name()
    source_bin = data
    features = caps.get_features(0)

    print("gstname=", gstname)

    if(gstname.find("video")!=-1):
        print("features=", features)
        if features.contains("memory:NVMM"):

            bin_ghost_pad = source_bin.get_static_pad("src")

            print(bin_ghost_pad)

            if not bin_ghost_pad.set_target(decoder_src_pad):

                print("Failed to link decoder src pad to source bin ghost pad")
                exit(0)
        else:
            print("Error: Decodebin did not pick nvidia decoder plugin.")
            exit(0)


def source_child_added(child_proxy, Object, name, user_data):
    print("Decodebin child added:", name)
    if(name.find("decodebin") != -1):
        Object.connect("child-added", decodebin_child_added, user_data)

def create_source_bin(camera):

    print("Creating Source Bin")

    bin_name="source-bin-" + str(camera["id"])
    source_bin = Gst.Bin.new(bin_name) 
    if not source_bin:
        print("Unable to create source bin")
        exit(0)

    source = create_element_or_error("nvarguscamerasrc", "camera-source")
    if not source:
        print("Unable to nvarguscamerasrc")
        exit(0)
    source.set_property("sensor-id", camera['source'])
    source.set_property('bufapi-version', True)

    source.connect("pad-added", new_pad_added, source_bin)


    Gst.Bin.add(source_bin, source)
    bin_pad = source_bin.add_pad(Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC))
    if not bin_pad:
        print("Failed to add ghost pad in source bin")
        exit(0)


    return source_bin

def main():

    cameras_list = [
        {"id": 0, "source": 0, "name": "Camera 1",},
        {"id": 1, "source": 1, "name": "Camera 2"},
    ]
    
    GObject.threads_init()
    Gst.init(None)

    pipeline = Gst.Pipeline()
    if not pipeline:
        print("Unable to create Pipeline")
        return False

    streammux = create_element_or_error("nvstreammux", "Stream-muxer")
    pipeline.add(streammux)

    for camera in cameras_list:

        print("Creating Source for ", camera["name"])

        source_bin = create_source_bin(camera)

        if not source_bin:
            sys.stderr.write("Unable to create source bin")

        pipeline.add(source_bin)

        padname = "sink_" + str(camera["id"])

        sinkpad = streammux.get_request_pad(padname) 
        if not sinkpad:
            sys.stderr.write("Unable to create sink pad bin")

        srcpad = source_bin.get_static_pad("src")

        if not srcpad:
            sys.stderr.write("Unable to create src pad bin \n")

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
    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    # streammux.set_property('num-surfaces-per-frame', 2)
    streammux.set_property('batch-size', 2)
    streammux.set_property('batched-push-timeout', 4000000)

    tiler_rows=int(math.sqrt(2))
    tiler_columns=int(math.ceil((1.0* 2 )/tiler_rows))
    tiler.set_property("rows", tiler_rows)
    tiler.set_property("columns", tiler_columns)
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
