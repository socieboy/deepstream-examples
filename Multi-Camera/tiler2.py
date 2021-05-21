#
# Author: Frank Sepulveda
# Email: socieboy@gmail.com
#
# Display multiple CSI cameras as source in the screen
#
# gst-launch-1.0 nvarguscamerasrc bufapi-version=true sensor-id=0 ! "video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1,format=NV12" ! m.sink_0 nvstreammux name=m batch-size=2 width=1280 height=720 live-source=1 ! nvinfer config-file-path=/opt/nvidia/deepstream/deepstream-5.0/samples/configs/deepstream-app/config_infer_primary.txt ! nvtracker tracker-width=640 tracker-height=480 ll-lib-file=/opt/nvidia/deepstream/deepstream-5.0/lib/libnvds_mot_klt.so enable-batch-process=1 ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=RGBA" ! nvmultistreamtiler ! nvdsosd ! nvvideoconvert ! nvegltransform ! nveglglessink nvarguscamerasrc bufapi-version=true sensor-id=1 ! "video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1,format=NV12" ! m.sink_1
#
import sys, gi
sys.path.append("../")
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

    # Muxer
    streammux = create_element_or_error("nvstreammux", "stream-muxer")
    streammux.set_property('live-source', 1)
    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('num-surfaces-per-frame', 1)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)
    pipeline.add(streammux)

    # Sources
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

    # Primary Inferance
    pgie = create_element_or_error("nvinfer", "primary-inference")
    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")
    pipeline.add(pgie)
    streammux.link(pgie)

    # Tracker
    tracker = create_element_or_error("nvtracker", "tracker")
    tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvdcf.so')
    tracker.set_property('enable-batch-process', 1)
    tracker.set_property('tracker-width', 640)
    tracker.set_property('tracker-height', 480)
    pipeline.add(tracker)
    pgie.link(tracker)

    # Analitycs
    analytics = create_element_or_error("nvdsanalytics", "analytics")
    analytics.set_property("config-file", "/deepstream-examples/Analitycs/analitycs.txt")
    pipeline.add(analytics)
    tracker.link(analytics)

    # Tee
    tee = create_element_or_error("tee", "tee")
    pipeline.add(tee)
    analytics.link(tee)

    # Get Main Tee Sink Pad for the Queues
    tee_src_pad_template = tee.get_pad_template("src_%u")
    tee_display_src_pad = tee.request_pad(tee_src_pad_template, None, None)

    # Display Queue
    queue = create_element_or_error("queue", "queue")
    pipeline.add(queue)
    queue_sink_pad = queue.get_static_pad("sink")

    # Link Main Tee to Display Queue
    if (tee_display_src_pad.link(queue_sink_pad) != Gst.PadLinkReturn.OK):
        print("Could not link main tee to display queue")
        return

    # Tiler
    tiler = create_element_or_error("nvmultistreamtiler", "nvtiler")
    tiler.set_property("rows", 2)
    tiler.set_property("columns", 2)
    tiler.set_property("width", 1920)
    tiler.set_property("height", 1080)
    pipeline.add(tiler)
    queue.link(tiler)

    # Converter
    convertor = create_element_or_error("nvvideoconvert", "converter-1")
    pipeline.add(convertor)
    tiler.link(convertor)

    # Nvosd
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    pipeline.add(nvosd)
    convertor.link(nvosd)

    # Transform
    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    pipeline.add(transform)
    nvosd.link(transform)

    # Sink
    sink = create_element_or_error("nveglglessink", "nvvideo-renderer")
    sink.set_property("qos", 0)
    pipeline.add(sink)
    transform.link(sink)

    # Play Pipeline
    loop = GObject.MainLoop()
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except:
        pass

    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    sys.exit(main())


