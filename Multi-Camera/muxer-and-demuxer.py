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

'''
gst-launch-1.0 nvstreammux name=mux live-source=1 sync-inputs=1 batch-size=3 width=3264 height=1848 batched-push-timeout=4000000 ! \
nvinfer config-file-path=/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt ! \
nvstreamdemux name=demux \

nvarguscamerasrc sensor-id=0 bufapi-version=1 ! "video/x-raw(memory:NVMM), width=(int)3264, height=(int)1848, framerate=30/1, format=(string)NV12" ! mux.sink_0 \
nvarguscamerasrc sensor-id=1 bufapi-version=1 ! "video/x-raw(memory:NVMM), width=(int)3264, height=(int)1848, framerate=30/1, format=(string)NV12" ! mux.sink_1 \

demux.src_0 ! nvvidconv ! nvv4l2h264enc insert-sps-pps=1 ! h264parse ! flvmux ! rtmpsink location=rtmp://media.streamit.live/LiveApp/cam1 \
demux.src_1 ! nvvidconv ! nvv4l2h264enc insert-sps-pps=1 ! h264parse ! flvmux ! rtmpsink location=rtmp://media.streamit.live/LiveApp/cam2
'''

def main(args):

    withInferance = False

    # Standard GStreamer initialization
    cameras_list = [
        { "source": 0, "name": "camera1", "rtmp": "rtmp://media.streamit.live/LiveApp/cam1" },
        { "source": 1, "name": "camera2", "rtmp": "rtmp://media.streamit.live/LiveApp/cam2" },
    ]
    
    GObject.threads_init()
    Gst.init(None)

    pipeline = Gst.Pipeline()

    # Muxer
    muxer = create_element_or_error("nvstreammux", "muxer")
    muxer.set_property('live-source', True)
    muxer.set_property('sync-inputs', True)
    muxer.set_property('width', 1920)
    muxer.set_property('height', 1080)
    muxer.set_property('batch-size', 3)
    muxer.set_property('batched-push-timeout', 4000000)
    pipeline.add(muxer)

    # Demuxer
    demux = create_element_or_error("nvstreamdemux", "demuxer")
    pipeline.add(demux)

    if withInferance:
        # Primart Inferance
        pgie = create_element_or_error("nvinfer", "primary-inference")
        pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")
        pipeline.add(pgie)
        muxer.link(pgie)
        pgie.link(demux)
    else:
        muxer.link(demux)

    # Sources
    for camera in cameras_list:
        source = create_element_or_error("nvarguscamerasrc", "source-" + camera['name'])
        source.set_property('sensor-id', camera['source'])

        caps = create_element_or_error("capsfilter", "source-caps-" + camera['name'])
        caps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080, framerate=(fraction)30/1, format=(string)NV12"))

        source.set_property('do-timestamp', True)
        source.set_property('bufapi-version', True)
        source.set_property('tnr-mode', 2)
        source.set_property('ee-mode', 2)
        source.set_property('aeantibanding', 0)

        pipeline.add(source)
        pipeline.add(caps)

        source.link(caps)
        
        srcpad = caps.get_static_pad("src")
        sinkpad = muxer.get_request_pad('sink_' + str(camera['source']))

        if not sinkpad:
            print("Unable to create source sink pad")
            exit(0)
        if not srcpad:
            print("Unable to create source src pad")
            exit(0)
        srcpad.link(sinkpad)

    # Outputs
    for camera in cameras_list:
        converter = create_element_or_error("nvvidconv", "converter-" + camera['name'])
        encoder = create_element_or_error("nvv4l2h264enc", "encoder-" + camera['name'])
        parser = create_element_or_error("h264parse", "parser-" + camera['name'])
        flmuxer = create_element_or_error("flvmux", "flmuxer-" + camera['name'])
        queue = create_element_or_error("queue", "queue-" + camera['name'])
        sink = create_element_or_error("rtmpsink", "sink-" + camera['name'])

        encoder.set_property('maxperf-enable', True)
        encoder.set_property('insert-sps-pps', True)
        encoder.set_property('bitrate', 8000000)
        flmuxer.set_property('streamable', True)
        sink.set_property('location', camera['rtmp'])
        sink.set_property('sync', False)

        pipeline.add(converter)
        pipeline.add(encoder)
        pipeline.add(parser)
        pipeline.add(flmuxer)
        pipeline.add(queue)
        pipeline.add(sink)

        _srcpad = demux.get_request_pad("src_" + str(camera['source']))
        if not _srcpad:
            print("Unable to create output src pad")
            exit(0)

        _sinkpad = converter.get_static_pad('sink')
        if not _sinkpad:
            print("Unable to create output sink pad")
            exit(0)

        _srcpad.link(_sinkpad)

        converter.link(encoder)
        encoder.link(parser)
        parser.link(flmuxer)
        flmuxer.link(queue)
        queue.link(sink)


    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    # List the sources
    print("Starting pipeline")
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except:
        pass
        
    # cleanup
    pipeline.set_state(Gst.State.NULL)

    print("Exiting app")
    

if __name__ == '__main__':
    sys.exit(main(sys.argv))