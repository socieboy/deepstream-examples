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


def nvanalytics_src_pad_buffer_probe(pad,info,u_data):
    frame_number=0
    num_rects=0
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return Gst.PadProbeReturn.OK

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list

    while l_frame:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        l_obj=frame_meta.obj_meta_list

        while l_obj:
            
            try: 
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break

            l_user_meta = obj_meta.obj_user_meta_list
            while l_user_meta:
                try:
                    user_meta = pyds.NvDsUserMeta.cast(l_user_meta.data)
                    if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSOBJ.USER_META"):             
                        user_meta_data = pyds.NvDsAnalyticsObjInfo.cast(user_meta.user_meta_data)
                        # if user_meta_data.dirStatus: print("Object {0} moving in direction: {1}".format(obj_meta.object_id, user_meta_data.dirStatus))                    
                        # if user_meta_data.lcStatus: print("Object {0} line crossing status: {1}".format(obj_meta.object_id, user_meta_data.lcStatus))
                except StopIteration:
                    break

                try:
                    l_user_meta = l_user_meta.next
                except StopIteration:
                    break
            try: 
                l_obj=l_obj.next
            except StopIteration:
                break
    
        l_user = frame_meta.frame_user_meta_list
        while l_user:
            try:
                user_meta = pyds.NvDsUserMeta.cast(l_user.data)
                if user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type("NVIDIA.DSANALYTICSFRAME.USER_META"):
                    user_meta_data = pyds.NvDsAnalyticsFrameMeta.cast(user_meta.user_meta_data)
                    if user_meta_data.objLCCumCnt: print("Linecrossing Cumulative: {0}".format(user_meta_data.objLCCumCnt))
                    # if user_meta_data.objLCCurrCnt: print("Linecrossing Current Frame: {0}".format(user_meta_data.objLCCurrCnt))
            except StopIteration:
                break
            try:
                l_user = l_user.next
            except StopIteration:
                break

        try:
            l_frame=l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK


def main(args):

    # Standard GStreamer initialization
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

    streammux = create_element_or_error("nvstreammux", "stream-muxer")
    pipeline.add(streammux)

    for camera in cameras_list:
        source = create_element_or_error("nvarguscamerasrc", "source-" + camera['name'])
        source.set_property('sensor-id', camera['source'])
        source.set_property('bufapi-version', True)
        caps = create_element_or_error("capsfilter", "source-caps-source-" + camera['name'])
        caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM),width=1920,height=1080,framerate=60/1,format=NV12"))
        pipeline.add(source)
        pipeline.add(caps)

        sinkpad = streammux.get_request_pad('sink_' + str(camera['source']))
        srcpad = source.get_static_pad("src")

        if not sinkpad:
            print("Unable to create source sink pad")
            exit(0)
        if not srcpad:
            print("Unable to create source src pad")
            exit(0)
        srcpad.link(sinkpad)

    queue1 = create_element_or_error("queue", "queue1")
    queue2 = create_element_or_error("queue", "queue2")
    queue3 = create_element_or_error("queue", "queue3")
    queue4 = create_element_or_error("queue", "queue4")
    queue5 = create_element_or_error("queue", "queue5")
    queue6 = create_element_or_error("queue", "queue6")
    queue7 = create_element_or_error("queue", "queue7")

    pgie = create_element_or_error("nvinfer", "primary-inference")
    tracker = create_element_or_error("nvtracker", "tracker")
    analytics = create_element_or_error("nvdsanalytics", "analytics")
    tiler = create_element_or_error("nvmultistreamtiler", "nvtiler")
    convertor = create_element_or_error("nvvideoconvert", "convertor")
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    transform=create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "nvvideo-renderer")

    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)
    
    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")

    tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream/lib/libnvds_mot_klt.so')
    tracker.set_property('gpu-id', 0)
    tracker.set_property('enable-past-frame', 1)
    tracker.set_property('enable-batch-process', 1)

    analytics.set_property("config-file", "./nvdsanalytics/live.txt")

    nvosd.set_property('process-mode', 0)
    nvosd.set_property('display-text', 0)

    sink.set_property('sync', False)

    print("Adding elements to Pipeline")
    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(queue3)
    pipeline.add(queue4)
    pipeline.add(queue5)
    pipeline.add(queue6)
    pipeline.add(queue7)
    pipeline.add(pgie)
    pipeline.add(tracker)
    pipeline.add(analytics)
    pipeline.add(tiler)
    pipeline.add(convertor)
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
    queue4.link(tiler)
    tiler.link(queue5)
    queue5.link(convertor)
    convertor.link(queue6)
    queue6.link(nvosd)
    nvosd.link(queue7)
    queue7.link(transform)
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
        analytics_src_pad.add_probe(Gst.PadProbeType.BUFFER, nvanalytics_src_pad_buffer_probe, 0)

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