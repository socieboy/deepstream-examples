#
# Author: Frank Sepulveda
# Email: socieboy@gmail.com
#
# Playbin Example
#
#
import sys, gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst


def main():
    
    GObject.threads_init()
    Gst.init(None)

    mainloop = GObject.MainLoop()   

    player = Gst.ElementFactory.make("playbin", "camera-source")
    player.set_property('uri', 'https://www.freedesktop.org/software/gstreamer-sdk/data/media/sintel_cropped_multilingual.webm')
    # play.set_property('uri', 'front-with-text.mp4')
    player.set_property('flags', 1)
    player.set_property('connection-speed', 100)
    # play.set_property('video-sink', 'DISPLAY:0')
    player.set_property('volume', 0.2)

    player.set_state(Gst.State.PLAYING)

    try:
        mainloop.run()
    except:
        pass


    player.set_state(Gst.State.NULL)

if __name__ == "__main__":
    sys.exit(main())

