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

tracked_objects = []
# objects_in_frame = []
tracked_objects_to_slipstream = []

def handle_track_object_meta(obj_meta):
    
    if not next((obj for obj in tracked_objects if obj["object_id"] == obj_meta.object_id), None):

        tracked_objects.append({
            "object_id" : obj_meta.object_id,
            "class_id" : obj_meta.class_id,
            "object_label" : obj_meta.obj_label,
            "tracker_confidence" : obj_meta.tracker_confidence,
            "directions" : [],
            ""
        })

            # print('Object id: ' + str(obj_meta.object_id))
            # print('Class id: ' + str(obj_meta.class_id))
            # print('Tracker Confidence: ' + str(obj_meta.tracker_confidence))

    # obj_counter[obj_meta.class_id] += 1
    l_user_meta = obj_meta.obj_user_meta_list

    while l_user_meta:
        try:

            user_meta = pyds.NvDsUserMeta.cast(l_user_meta.data)

            if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSOBJ.USER_META"):  

                user_meta_data = pyds.NvDsAnalyticsObjInfo.cast(user_meta.user_meta_data)

                if user_meta_data.dirStatus: print("Object {0} moving in direction: {1}".format(obj_meta.object_id, user_meta_data.dirStatus))                    
                if user_meta_data.lcStatus: print("Object {0} line crossing status: {1}".format(obj_meta.object_id, user_meta_data.lcStatus))
                if user_meta_data.roiStatus: print("Object {0} roi status: {1}".format(obj_meta.object_id, user_meta_data.roiStatus))

        except StopIteration:
            break

        try:
            l_user_meta = l_user_meta.next
        except StopIteration:
            break

def handle_src_pad_buffer_probe(pad,info,u_data):
    gst_buffer = info.get_buffer()

    if not gst_buffer:
        print("Unable to get GstBuffer")
        return

    # Get the frames on the batch of metadata
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    current_frame = batch_meta.frame_meta_list

    # Iterate thru each frame
    while current_frame:

        try:
            frame_meta = pyds.NvDsFrameMeta.cast(current_frame.data)
        except StopIteration:
            break

        # Get the current frame number
        # frame_meta.frame_num

        # Get the number of rectangules/objects in the current frame
        # frame_meta.num_obj_meta

        # Get the source id
        # frame_meta.source_id

        # get the current frame
        current_object = frame_meta.obj_meta_list
        
        # Iterate thru each object in the current frame
        while current_object:
            try: 
                object_meta = pyds.NvDsObjectMeta.cast(current_object.data)
            except StopIteration:
                break

            handle_track_object_meta(object_meta)

            try: 
                current_object = current_object.next
            except StopIteration:
                break
    
        # l_user = frame_meta.frame_user_meta_list

        # while l_user:
        #     try:
        #         user_meta = pyds.NvDsUserMeta.cast(l_user.data)
        #         if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSFRAME.USER_META"):
        #             user_meta_data = pyds.NvDsAnalyticsFrameMeta.cast(user_meta.user_meta_data)
        #             # if user_meta_data.objInROIcnt: print("Objs in ROI: {0}".format(user_meta_data.objInROIcnt))                    
        #             # if user_meta_data.objLCCumCnt: print("Linecrossing Cumulative: {0}".format(user_meta_data.objLCCumCnt))
        #             # if user_meta_data.objLCCurrCnt: print("Linecrossing Current Frame: {0}".format(user_meta_data.objLCCurrCnt))
        #     except StopIteration:   
        #         break
        #     try:
        #         l_user = l_user.next
        #     except StopIteration:
        #         break

            ## Append event right here.
        try:
            # Get the next frame if exists on the batch of data
            current_frame = current_frame.next
        except StopIteration:
            break

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
        Object.connect("child-added", decodebin_child_added, user_data)

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

    # Muxer
    streammux = create_element_or_error("nvstreammux", "Stream-muxer")
    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)
    pipeline.add(streammux)

    # Source
    source_bin = create_source_bin("file:/deepstream-examples/Analitycs/traffic.mp4")

    if not source_bin:
        sys.stderr.write("Unable to create source bin")
    pipeline.add(source_bin)

    sinkpad = streammux.get_request_pad('sink_0') 
    if not sinkpad:
        sys.stderr.write("Unable to create sink pad bin")
    srcpad = source_bin.get_static_pad("src")
    if not srcpad:
        sys.stderr.write("Unable to create src pad bin")
    srcpad.link(sinkpad)

    # Primary Inferance
    pgie = create_element_or_error("nvinfer", "primary-inference")
    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")
    pipeline.add(pgie)
    streammux.link(pgie)

    # Tracker
    tracker = create_element_or_error("nvtracker", "tracker")
    tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvdcf.so')
    tracker.set_property('gpu-id', 0)
    tracker.set_property('enable-past-frame', 1)
    tracker.set_property('enable-batch-process', 1)
    pipeline.add(tracker)
    pgie.link(tracker)

    # Second Inferance
    sgie = create_element_or_error("nvinfer", "secondary-inference")
    sgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_secondary_carmake.txt")
    sgie.set_property('unique-id', 12345)
    pipeline.add(sgie)
    tracker.link(sgie)

    # Analytcis
    analytics = create_element_or_error("nvdsanalytics", "analytics")
    analytics.set_property("config-file", "./analitycs.txt")
    pipeline.add(analytics)
    sgie.link(analytics)

    # Converter
    converter = create_element_or_error("nvvideoconvert", "convertor")
    pipeline.add(converter)
    analytics.link(converter)
    
    # Nvosd
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    # nvosd.set_property('process-mode', 2)
    nvosd.set_property('display-text', False)
    nvosd.set_property('display-mask', False)
    nvosd.set_property('display-bbox', True)
    pipeline.add(nvosd)
    converter.link(nvosd)

    # Transform
    transform=create_element_or_error("nvegltransform", "nvegl-transform")
    pipeline.add(transform)
    nvosd.link(transform)

    # Sink
    sink = create_element_or_error("nveglglessink", "nvvideo-renderer")
    pipeline.add(sink)
    transform.link(sink)

    # Prove
    # tracker_prove_src_pad = tracker.get_static_pad("src")
    # if not tracker_prove_src_pad:
    #     sys.stderr.write("Unable to get src pad")
    # else:
    #     tracker_prove_src_pad.add_probe(Gst.PadProbeType.BUFFER, handle_src_pad_buffer_probe, 0)

    analytics_prove_src_pad = analytics.get_static_pad("src")
    if not analytics_prove_src_pad:
        sys.stderr.write("Unable to get src pad")
    else:
        analytics_prove_src_pad.add_probe(Gst.PadProbeType.BUFFER, handle_src_pad_buffer_probe, 0)

    loop = GObject.MainLoop()
    pipeline.set_state(Gst.State.PLAYING)

    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    try:
        loop.run()
    except:
        pass

    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    sys.exit(main(sys.argv))