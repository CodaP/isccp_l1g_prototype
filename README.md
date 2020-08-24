# ISCCP L1g Prototype

The ISCCP Level-1G (L1G) dataset is a composition of imagery from all advanced geostationary imagers into homogeneous and globally gridded fields.
Sensor overlap is handled using a layering scheme similar to that of the NOAA/NESDIS GridSat product.
The L1G is intended to be the input for ISCCP-NG L2, but can also be a resource for applications needing geostationary data.
The provisional approach is to include all channels every 30 minutes with a maximum resolution of 4 km on a Equirectangular grid.


## Sampling Methodology

1. Average to uniform footprint
2. Sample to desired resolution


## Merge Methodology

### Static Ancillary Variables

* Surface Type
* Surface Elevation
* Surface Elevation Stddev 3x3
* Land Mask
* Coast Mask

### Dynamic Ancillary Variables

* Surface Temperature
* TPW
* Total Ozone
* Surface Emissivity
* Surface Reflectance

