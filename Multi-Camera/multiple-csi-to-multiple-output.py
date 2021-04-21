#
# Author: Frank Sepulveda
# Email: socieboy@gmail.com
#
# Display multiple CSI cameras as source in the screen
#
# gst-launch-1.0 nvarguscamerasrc bufapi-version=true sensor-id=0 ! "video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1,format=NV12" ! m.sink_0 nvstreammux name=m batch-size=2 width=1280 height=720 live-source=1 ! nvinfer config-file-path=/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt ! nvtracker tracker-width=640 tracker-height=480 ll-lib-file=/opt/nvidia/deepstream/deepstream/lib/libnvds_mot_klt.so enable-batch-process=1 ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=RGBA" ! nvmultistreamtiler ! nvdsosd ! nvvideoconvert ! nvegltransform ! nveglglessink nvarguscamerasrc bufapi-version=true sensor-id=1 ! "video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1,format=NV12" ! m.sink_1

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

        srcpad = source.get_static_pad("src")

        sinkpad = streammux.get_request_pad('sink_' + str(camera['source']))

        if not sinkpad:
            print("Unable to create source sink pad")
            exit(0)
        if not srcpad:
            print("Unable to create source src pad")
            exit(0)
        srcpad.link(sinkpad)

    pgie = create_element_or_error("nvinfer", "primary-inference")
    convertor = create_element_or_error("nvvideoconvert", "converter-1")
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    transform = create_element_or_error("nvegltransform", "nvegl-transform")
    tee = create_element_or_error("tee", "tee")
    queue = create_element_or_error("queue", "queue1")
    queue2 = create_element_or_error("queue", "queue2")

    # Set Element Properties
    streammux.set_property('live-source', 1)
    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('num-surfaces-per-frame', 1)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)

    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")

    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(pgie)
    pipeline.add(convertor)
    pipeline.add(nvosd)
    pipeline.add(transform)

    # Create outputs
    for camera in cameras_list:
        sink = create_element_or_error("nveglglessink", "nvvideo-renderer-" + camera['name'])
        # sink.set_property("qos", 0)
        pipeline.add(sink)
        srcpad = streammux.get_pad_template("src_%u")
        # srcpad.link

    # Link the elements together:
    print("Linking elements in the Pipeline")
    streammux.link(pgie)
    pgie.link(convertor)
    convertor.link(nvosd)
    nvosd.link(transform)
    # transform.link(sink)
    
    
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


