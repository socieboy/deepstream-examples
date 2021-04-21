#
# Author: Frank Sepulveda
# Email: socieboy@gmail.com
#
# Read a local Video File, apply inference and tracking and stream to RTMP
# gst-launch-1.0 filesrc location=video.mp4 ! qtdemux name=demux demux.video_0 ! queue ! h264parse ! omxh264dec ! nvegltransform ! nveglglessink -e
#
import sys, gi
sys.path.append("../")
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.bus_call import bus_call
from common.create_element_or_error import create_element_or_error


def main():
    
    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create Pipeline Element
    pipeline = Gst.Pipeline()
    if not pipeline:
        print("Unable to create Pipeline")
        return False
    
    # Create GST Elements
    source = create_element_or_error("filesrc", "file-source")
    # parser = create_element_or_error("h264parse", "parse")
    # decoder = create_element_or_error("nvv4l2decoder", "decoder")
    # streammux = create_element_or_error("nvstreammux", "Stream-muxer")
    # pgie = create_element_or_error("nvinfer", "primary-inference")
    # tracker = create_element_or_error("nvtracker", "tracker")
    # convertor = create_element_or_error("nvvideoconvert", "convertor-1")
    # nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    sink = create_element_or_error("nveglglessink", "egl-overlay")

    # Set Element Properties
    source.set_property('location', './videos/sample_qHD.h264')
    # sink.set_property('location', 'rtmp://media.streamit.live/LiveApp/stream-test')

    # streammux.set_property('width', 1280)
    # streammux.set_property('height', 720)
    # streammux.set_property('batch-size', 1)
    # streammux.set_property('batched-push-timeout', 4000000)

    # pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream-5.1/samples/configs/deepstream-app/config_infer_primary.txt")

    # tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream-5.1/lib/libnvds_nvdcf.so')
    # tracker.set_property('gpu-id', 0)
    # tracker.set_property('enable-past-frame', 1)
    # tracker.set_property('enable-batch-process', 1)
    # tracker.set_property('ll-config-file', '/opt/nvidia/deepstream/deepstream-5.1/samples/configs/deepstream-app/tracker_config.yml')

    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(source)
    # pipeline.add(parser)
    # pipeline.add(decoder)
    # pipeline.add(streammux)
    # pipeline.add(pgie)
    # pipeline.add(tracker)
    # pipeline.add(convertor)
    # pipeline.add(nvosd)
    pipeline.add(transform)
    pipeline.add(sink)

    # source.link(parser)
    # parser.link(decoder)

    # sinkpad = streammux.get_request_pad("sink_0")
    # if not sinkpad:
    #     sys.stderr.write(" Unable to get the sink pad of streammux \n")
    # srcpad = decoder.get_static_pad("src")
    # if not srcpad:
    #     sys.stderr.write(" Unable to get source pad of decoder \n")
    # srcpad.link(sinkpad)

    # Link the elements together:
    print("Linking elements in the Pipeline")
    # source.link(parser)
    # parser.link(decoder)
    # decoder.link(streammux)
    # streammux.link(pgie)
    # pgie.link(tracker)
    # tracker.link(convertor)
    # convertor.link(nvosd)
    # nvosd.link(transform)
    source.link(transform)
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

