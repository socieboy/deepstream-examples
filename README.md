# Deepstream + Gstreamer Jetson Examples

**Author:**\
Frank Sepulveda\
socieboy@gmail.com

This repository contains examples of gstreamer + deepstream pipelines in python to be used in Jetson devices.


Reset Json Clocks
```
sudo nvpmodel -m 0
sudo jetson_clocks
```

Clear Cache
```
rm ${HOME}/.cache/gstreamer-1.0/registry.aarch64.bin
```