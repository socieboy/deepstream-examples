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


# def nvanalytics_src_pad_buffer_probe(pad,info,u_data):
#     frame_number=0
#     num_rects=0
#     gst_buffer = info.get_buffer()
#     if not gst_buffer:
#         print("Unable to get GstBuffer ")
#         return

#     # Retrieve batch metadata from the gst_buffer
#     # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
#     # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
#     batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
#     l_frame = batch_meta.frame_meta_list

#     while l_frame:
#         try:
#             # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
#             # The casting is done by pyds.NvDsFrameMeta.cast()
#             # The casting also keeps ownership of the underlying memory
#             # in the C code, so the Python garbage collector will leave
#             # it alone.
#             frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
#         except StopIteration:
#             break

#         # frame_number=frame_meta.frame_num
#         l_obj=frame_meta.obj_meta_list
#         # num_rects = frame_meta.num_obj_meta
#         # obj_counter = {
#         # PGIE_CLASS_ID_VEHICLE:0,
#         # PGIE_CLASS_ID_PERSON:0,
#         # PGIE_CLASS_ID_BICYCLE:0,
#         # PGIE_CLASS_ID_ROADSIGN:0
#         # }
#         print("#"*50)
#         while l_obj:
#             try: 
#                 # Note that l_obj.data needs a cast to pyds.NvDsObjectMeta
#                 # The casting is done by pyds.NvDsObjectMeta.cast()
#                 obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
#             except StopIteration:
#                 break
#             # obj_counter[obj_meta.class_id] += 1
#             l_user_meta = obj_meta.obj_user_meta_list
#             # Extract object level meta data from NvDsAnalyticsObjInfo
#             while l_user_meta:
#                 try:
#                     user_meta = pyds.NvDsUserMeta.cast(l_user_meta.data)
#                     if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSOBJ.USER_META"):             
#                         user_meta_data = pyds.NvDsAnalyticsObjInfo.cast(user_meta.user_meta_data)
#                         # if user_meta_data.dirStatus: print("Object {0} moving in direction: {1}".format(obj_meta.object_id, user_meta_data.dirStatus))                    
#                         # if user_meta_data.lcStatus: print("Object {0} line crossing status: {1}".format(obj_meta.object_id, user_meta_data.lcStatus))
#                 except StopIteration:
#                     break

#                 try:
#                     l_user_meta = l_user_meta.next
#                 except StopIteration:
#                     break
#             try: 
#                 l_obj = l_obj.next
#             except StopIteration:
#                 break
    
#         # Get meta data from NvDsAnalyticsFrameMeta
#         l_user = frame_meta.frame_user_meta_list
#         while l_user:
#             try:
#                 user_meta = pyds.NvDsUserMeta.cast(l_user.data)
#                 if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSFRAME.USER_META"):
#                     user_meta_data = pyds.NvDsAnalyticsFrameMeta.cast(user_meta.user_meta_data)
#                     print(obj_meta.obj_label)
#                     if user_meta_data.objLCCumCnt: print("Linecrossing Cumulative: {0}".format(user_meta_data.objLCCumCnt))
#                     # if user_meta_data.objLCCurrCnt: print("Linecrossing Current Frame: {0}".format(user_meta_data.objLCCurrCnt))
#             except StopIteration:
#                 break
#             try:
#                 l_user = l_user.next
#             except StopIteration:
#                 break
        
#         # print("Frame Number=", frame_number, "stream id=", frame_meta.pad_index, "Number of Objects=",num_rects,"Vehicle_count=",obj_counter[PGIE_CLASS_ID_VEHICLE],"Person_count=",obj_counter[PGIE_CLASS_ID_PERSON])
#         # Get frame rate through this probe
#         # fps_streams["stream{0}".format(frame_meta.pad_index)].get_fps()
#         try:
#             l_frame=l_frame.next
#         except StopIteration:
#             break
#         print("#"*50)

#     return Gst.PadProbeReturn.OK



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

    source_bin = create_source_bin("file:/home/socieboy/edge/deepstream-examples/videos/front.mp4")

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
    # queue2 = create_element_or_error("queue","queue2")
    # queue3 = create_element_or_error("queue","queue3")
    # queue4 = create_element_or_error("queue","queue4")
    # queue5 = create_element_or_error("queue","queue5")
    queue6 = create_element_or_error("queue","queue6")
    queue7 = create_element_or_error("queue","queue7")

    pipeline.add(queue1)
    # pipeline.add(queue2)
    # pipeline.add(queue3)
    # pipeline.add(queue4)
    # pipeline.add(queue5)
    pipeline.add(queue6)
    pipeline.add(queue7)

    pgie = create_element_or_error("nvinfer", "primary-inference")
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    converter = create_element_or_error("nvvideoconvert", "convertor-1")
    nvosd.set_property('process-mode', 2)
    # nvosd.set_property('display-text', 0)

    transform=create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "nvvideo-renderer")

    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)

    sink.set_property('sync', False)
    sink.set_property('window-width', 1080)
    sink.set_property('window-height', 720)
    
    # pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")
    pgie.set_property('config-file-path', "models/yolov3-nurawash-80/config_infer_primary_yoloV3.txt")

    print("Adding elements to Pipeline")
    pipeline.add(pgie)
    pipeline.add(converter)
    pipeline.add(nvosd)
    pipeline.add(transform)
    pipeline.add(sink)

    print("Linking elements in the Pipeline")
    streammux.link(pgie)
    pgie.link(converter)
    converter.link(nvosd)
    nvosd.link(transform)
    transform.link(sink)

    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    # analytics_src_pad = analytics.get_static_pad("src")
    # if not analytics_src_pad:
    #     sys.stderr.write("Unable to get src pad")
    # else:
    #     analytics_src_pad.add_probe(Gst.PadProbeType.BUFFER, nvanalytics_src_pad_buffer_probe, 0)

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