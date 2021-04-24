#
# Author: Frank Sepulveda
# Email: socieboy@gmail.com
#
# Publish stream to RTMP server and applying the tracker plugin to keep a record
# of the objects detected.
#
import sys, gi, time
sys.path.append("../")
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.bus_call import bus_call
from common.create_element_or_error import create_element_or_error
import pyds


detectedObjectsIds = []
detectedObjects = []

def sink_pad_buffer_probe(pad,info,u_data):
   
    gst_buffer = info.get_buffer()

    if not gst_buffer:
        sys.stderr.write("Unable to get GstBuffer")

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    frame_list = batch_meta.frame_meta_list

    while frame_list is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(frame_list.data)
        except StopIteration:
            break

        # detected_time = frame_meta.ntp_timestamp
        # print(detected_time)
        list_of_objects = frame_meta.obj_meta_list

        while list_of_objects is not None:
            
            try:
                object_meta = pyds.NvDsObjectMeta.cast(list_of_objects.data)
                # https://docs.nvidia.com/metropolis/deepstream/5.0DP/python-api/NvDsMeta/NvDsObjectMeta.html
                if object_meta.object_id not in detectedObjectsIds:
                    t = time.localtime()
                    current_time = time.strftime("%H:%M:%S", t)

                    detectedObjectsIds.append(object_meta.object_id)
                    detectedObjects.append({
                        "id" : str(object_meta.object_id),
                        "label": str(object_meta.obj_label),
                        "time": str(current_time),
                        "confidence": str(object_meta.confidence)
                    })
                    
            except StopIteration:
                break
            # obj_counter[object_meta.class_id] += 1
            try:
                list_of_objects = list_of_objects.next
            except StopIteration:
                break
        try:
            frame_list = frame_list.next
        except StopIteration:
            break

        display_meta=pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]

        textDisplay = "DETECTED OBJECTS:\n\n"
        if len(detectedObjects) > 10:
            detectedObjectsList = detectedObjects[-10]
        else:
            detectedObjectsList = detectedObjects
            
        for _object in detectedObjectsList:
            print("Time      : " + _object["time"])
            print("Object ID : " + _object["id"])
            print("Object    : " + _object["label"])
            print("Confidence: " + _object["confidence"])
            # textDisplay = textDisplay + _object["time"] + ": Detected: \"" + _object["label"] + "\", ID: " + _object["id"] + ", Confidence: " + _object["confidence"] + "\n"

        # py_nvosd_text_params.display_text = textDisplay
        # py_nvosd_text_params.x_offset = 10
        # py_nvosd_text_params.y_offset = 12
        # py_nvosd_text_params.font_params.font_name = "Serif"
        # py_nvosd_text_params.font_params.font_size = 10
        # py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)
        # py_nvosd_text_params.set_bg_clr = 1
        # py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        # pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
			
    return Gst.PadProbeReturn.OK

def main():
    
    print('Tracker Example')

    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create Pipeline Element
    pipeline = Gst.Pipeline()
    if not pipeline:
        print("Unable to create Pipeline")
        return False
    
    # Create GST Elements
    source = create_element_or_error("nvarguscamerasrc", "camera-source")
    srcCaps = create_element_or_error("capsfilter", "source-caps")
    srcCaps.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), width=(int)1920, height=(int)1080, framerate=30/1, format=(string)NV12"))
    streammux = create_element_or_error("nvstreammux", "Stream-muxer")
    pgie = create_element_or_error("nvinfer", "primary-inference")
    tracker = create_element_or_error("nvtracker", "tracker")
    convertor = create_element_or_error("nvvideoconvert", "convertor-1")
    nvosd = create_element_or_error("nvdsosd", "onscreendisplay")
    convertor2 = create_element_or_error("nvvideoconvert", "converter-2")
    encoder = create_element_or_error("nvv4l2h264enc", "encoder")
    parser = create_element_or_error("h264parse", "parser")
    muxer = create_element_or_error("flvmux", "muxer")
    queue = create_element_or_error("queue", "queue-sink")
    sink = create_element_or_error("rtmpsink", "sink")

    # Set Element Properties
    source.set_property('sensor-id', 0)
    source.set_property('bufapi-version', True)

    encoder.set_property('insert-sps-pps', True)
    encoder.set_property('bitrate', 4000000)
    
    streammux.set_property('live-source', 1)
    streammux.set_property('width', 1080)
    streammux.set_property('height', 720)
    streammux.set_property('num-surfaces-per-frame', 1)
    streammux.set_property('nvbuf-memory-type', 4)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)

    pgie.set_property('config-file-path', "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_infer_primary.txt")

    tracker.set_property('ll-lib-file', '/opt/nvidia/deepstream/deepstream/lib/libnvds_nvdcf.so')
    tracker.set_property('gpu-id', 0)
    tracker.set_property('enable-batch-process', 1)
    tracker.set_property('ll-config-file', '/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/tracker_config.yml')

    muxer.set_property('streamable', True)
    sink.set_property('location', 'rtmp://media.streamit.live/LiveApp/csi-camera')

    # Add Elemements to Pipielin
    print("Adding elements to Pipeline")
    pipeline.add(source)
    pipeline.add(srcCaps)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(tracker)
    pipeline.add(convertor)
    pipeline.add(nvosd)
    pipeline.add(convertor2)
    pipeline.add(encoder)
    pipeline.add(parser)
    pipeline.add(muxer)
    pipeline.add(queue)
    pipeline.add(sink)

    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux")

    # Link the elements together:
    print("Linking elements in the Pipeline")
    source.link(srcCaps)
    srcCaps.link(streammux)
    streammux.link(pgie)
    pgie.link(tracker)
    tracker.link(convertor)
    convertor.link(nvosd)
    nvosd.link(convertor2)
    convertor2.link(encoder)
    encoder.link(parser)
    parser.link(muxer)
    muxer.link(queue)
    queue.link(sink)
    
    # Create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    print('Create OSD Sink Pad')
    nvosd_sinkpad = nvosd.get_static_pad("sink")
    if not nvosd_sinkpad:
        sys.stderr.write("Unable to get sink pad of nvosd")

    nvosd_sinkpad.add_probe(Gst.PadProbeType.BUFFER, sink_pad_buffer_probe, 0)

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
