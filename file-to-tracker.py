#!/usr/bin/env python3

import sys
sys.path.append('../')
import gi
import configparser
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from gi.repository import GLib
from ctypes import *
import time
import math
import cv2
import numpy as np
import platform
from common.bus_call import bus_call
from common.create_element_or_error import create_element_or_error

import pyds


def analytics_meta_buffer_probe(pad,info,u_data):

    # Get the buffer from the pipeline
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return Gst.PadProbeReturn.OK

    # With the pyds wrapper get the batch of metadata from the buffer
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))

    # From the batch of metadata get the list of frames
    list_of_frames = batch_meta.frame_meta_list

    # Iterate thru the list of frames
    while list_of_frames is not None:
        try:
            
            # Get the metadata on the current frame
            # The next frame is set at the end of the while loop
            frame_meta = pyds.NvDsFrameMeta.cast(list_of_frames.data)

        except StopIteration:
            break

        # INFORMATION THAT IS PRESENT THE FRAME
        #
        # - frame_meta.frame_num
        # - frame_meta.frame_num
        # - frame_meta.source_id
        # - frame_meta.batch_id
        # - frame_meta.source_frame_width
        # - frame_meta.source_frame_height
        # - frame_meta.num_obj_meta

        # Print the frame width and height to see what positions can the bounding boxed be drawed
        # print('Frame Width: ' + str(frame_meta.source_frame_width)) = 1920
        # print('Frame Height: ' + str(frame_meta.source_frame_height)) = 1080

        # In the information of the frame we can get a list of objects detected on the frame.
        list_of_objects = frame_meta.obj_meta_list

        # Iterate thru the list of objects
        while list_of_objects is not None:
            try: 
                # Get the metadata for each object in the frame
                object_meta = pyds.NvDsObjectMeta.cast(list_of_objects.data)

            except StopIteration:
                break

            # Go to the next object in the list
            l_user_meta = object_meta.obj_user_meta_list

            while l_user_meta:
                try:
                    pass
                    # user_meta = pyds.NvDsUserMeta.cast(l_user_meta.data)
                    # print(user_meta.base_meta.meta_type)
                    # if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSOBJ.USER_META"):             
                    #     user_meta_data = pyds.NvDsAnalyticsObjInfo.cast(user_meta.user_meta_data)
                    #     if user_meta_data.dirStatus: print("Object {0} moving in direction: {1}".format(object_meta.object_id, user_meta_data.dirStatus))                    
                    #     if user_meta_data.lcStatus: print("Object {0} line crossing status: {1}".format(object_meta.object_id, user_meta_data.lcStatus))
                    #     if user_meta_data.ocStatus: print("Object {0} overcrowding status: {1}".format(object_meta.object_id, user_meta_data.ocStatus))
                    #     if user_meta_data.roiStatus: print("Object {0} roi status: {1}".format(object_meta.object_id, user_meta_data.roiStatus))
                except StopIteration:
                    break

            try: 
                list_of_objects = list_of_objects.next
            except StopIteration:
                break
        # When there is no more object in the list of objects
        # we continue here

        # INFORMATION OF THE OBJECT METADATA
        #
        # - object_meta.class_id
        # - object_meta.confidence
        # - object_meta.obj_label
        # - object_meta.object_id (If not tracker present on the pipeline, the ID is the same for all objects)
        # - object_meta.rect_params

        # Get the display meta from the batch meta, this is another metadata different that the frame meta collected 
        # befor
        display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)

        # Define the number of rects that we are going to draw

        # Draw the boxes on the frame
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)

        try:
            # Go to the next frame in the list
            list_of_frames = list_of_frames.next
        except StopIteration:
            break
        # When there are not frames in the buffer we end here, and the function returns ok


    return Gst.PadProbeReturn.OK



def cb_newpad(decodebin, decoder_src_pad,data):
    print("In cb_newpad")
    caps=decoder_src_pad.get_current_caps()
    gststruct=caps.get_structure(0)
    gstname=gststruct.get_name()
    source_bin=data
    features=caps.get_features(0)

    # Need to check if the pad created by the decodebin is for video and not
    # audio.
    print("gstname=",gstname)
    if(gstname.find("video")!=-1):
        # Link the decodebin pad only if decodebin has picked nvidia
        # decoder plugin nvdec_*. We do this by checking if the pad caps contain
        # NVMM memory features.
        print("features=",features)
        if features.contains("memory:NVMM"):
            # Get the source bin ghost pad
            bin_ghost_pad=source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                sys.stderr.write("Failed to link decoder src pad to source bin ghost pad\n")
        else:
            sys.stderr.write(" Error: Decodebin did not pick nvidia decoder plugin.\n")

def decodebin_child_added(child_proxy,Object,name,user_data):
    print("Decodebin child added:", name, "\n")
    if(name.find("decodebin") != -1):
        Object.connect("child-added",decodebin_child_added,user_data)

def create_source_bin(uri):
    
    print("Creating source bin")

    source_bin = Gst.Bin.new('source-bin')
    if not source_bin:
        print("Unable to create source bin")
        exit(0)

    uri_decode_bin = create_element_or_error("uridecodebin", "uri-decode-bin")
    uri_decode_bin.set_property("uri", uri)
    uri_decode_bin.connect("pad-added", cb_newpad, source_bin)
    uri_decode_bin.connect("child-added", decodebin_child_added, source_bin)

    Gst.Bin.add(source_bin, uri_decode_bin)

    bin_pad = source_bin.add_pad(Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC))

    if not bin_pad:
        print("Failed to add ghost pad in source bin")
        exit(0)

    return source_bin

def main(args):

    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    print("Creating Pipeline")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline")
    print("Creating streamux")

    streammux = create_element_or_error("nvstreammux", "Stream-muxer")

    pipeline.add(streammux)

    source_bin = create_source_bin("file:/deepstream-examples/videos/traffic.mp4")

    if not source_bin:
        sys.stderr.write("Unable to create source bin")
    
    pipeline.add(source_bin)

    sinkpad= streammux.get_request_pad('sink_0') 
    if not sinkpad:
        sys.stderr.write("Unable to create sink pad bin")

    srcpad=source_bin.get_static_pad("src")
    if not srcpad:
        sys.stderr.write("Unable to create src pad bin")

    srcpad.link(sinkpad)

    queue1 = create_element_or_error("queue","queue1")
    queue2 = create_element_or_error("queue","queue2")
    queue3 = create_element_or_error("queue","queue3")
    queue4 = create_element_or_error("queue","queue4")
    queue5 = create_element_or_error("queue","queue5")
    queue6 = create_element_or_error("queue","queue6")

    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(queue3)
    pipeline.add(queue4)
    pipeline.add(queue5)
    pipeline.add(queue6)

    pgie = create_element_or_error("nvinfer", "primary-inference")
    tracker = create_element_or_error("nvtracker", "tracker")
    analytics = create_element_or_error("nvdsanalytics", "analytics")
    converter = create_element_or_error("nvvideoconvert", "convertor")
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    
    nvosd.set_property('process-mode', 0)
    nvosd.set_property('display-text', 0)

    transform=create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "nvvideo-renderer")

    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)
    
    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream-5.1/samples/configs/deepstream-app/config_infer_primary.txt")

    tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream-5.1/lib/libnvds_nvdcf.so')
    tracker.set_property('gpu-id', 0)
    tracker.set_property('enable-past-frame', 1)
    tracker.set_property('enable-batch-process', 1)

    analytics.set_property("config-file", "config_nvdsanalytics.txt")

    print("Adding elements to Pipeline")
    pipeline.add(pgie)
    pipeline.add(tracker)
    pipeline.add(analytics)
    pipeline.add(converter)
    pipeline.add(nvosd)
    pipeline.add(transform)
    pipeline.add(sink)

    print("Linking elements in the Pipeline")
    streammux.link(queue1)
    queue1.link(pgie)
    pgie.link(queue2)
    queue2.link(tracker)
    tracker.link(queue3)
    queue3.link(analytics)
    analytics.link(queue4)
    queue4.link(converter)
    converter.link(queue5)
    queue5.link(nvosd)
    nvosd.link(queue6)
    queue6.link(transform)
    transform.link(sink)

    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    analytics_src_pad = analytics.get_static_pad("src")
    if not analytics_src_pad:
        sys.stderr.write("Unable to get src pad")
    else:
        analytics_src_pad.add_probe(Gst.PadProbeType.BUFFER, analytics_meta_buffer_probe, 0)

    # List the sources
    print("Starting pipeline")
    # start play back and listed to events		
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    # cleanup
    print("Exiting app")
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    sys.exit(main(sys.argv))