# son-vcdn-pilot
=======

This repository contains descriptors, code and images of the SONATA vCDN pilot.

SONATA vCDN pilots depends on the following VNFs 

* vTC: virtual Traffic Classifier 
* vCC: virtual Content Cache
* vTU: virtual Transcoding Unit 

It is also assumed that SDN capable networking elements provide connectivity for the various PoPs, End-Users and Content Server. The later exposes via NFS a content directory which is also mounted by the vTU. 
