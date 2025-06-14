# Quick reference

-    **Maintained by**:  
      [georchestra.org](https://www.georchestra.org/)

-    **Where to get help**:  
     the [geOrchestra Github repo](https://github.com/georchestra/datafeeder), [IRC chat](https://matrix.to/#/#georchestra:osgeo.org), Stack Overflow

# Featured tags

- `latest`, `1.0.x`
- Old builds : `24.0.x`

# Quick reference

-	**Where to file issues**:  
     [https://github.com/georchestra/datafeeder/issues](https://github.com/georchestra/datafeeder/issues)

-	**Supported architectures**:   
     [`amd64`](https://hub.docker.com/r/amd64/docker/)

-	**Source of this description**:  
     [daafeeder repo's ](https://github.com/georchestra/datafeeder/blob/main/DOCKER_HUB.md)

# What is `georchestra/datafeeder`

**Datafeeder** is geOrchestra's backend RESTful service to upload file based datasets and publish them to GeoServer and GeoNetwork in one shot.

The separate front-end UI ([georchestra/datafeeder-frontend](https://hub.docker.com/r/georchestra/datafeeder-frontend)) service provides the wizard-like user interface to interact with this backend.

# How to use this image

As for every other geOrchestra webapp, its configuration resides in the data directory ([datadir](https://github.com/georchestra/datadir)), typically something like /etc/georchestra, where it expects to find a analytics sub-directory.

It is recommended to use the official docker composition: https://github.com/georchestra/docker.

For this specific component, see the section `datafeeder` in the [`georchestra/docker/docker-compose.yml`](https://github.com/georchestra/docker/blob/master/docker-compose.yml) file.

# License

View [license information](https://www.georchestra.org/software.html) for the software contained in this image.

As with all Docker images, these likely also contain other software which may be under other licenses (such as Bash, etc from the base distribution, along with any direct or indirect dependencies of the primary software being contained).

[//]: # (Some additional license information which was able to be auto-detected might be found in [the `repo-info` repository's georchestra/ directory]&#40;&#41;.)

As for any docker image, it is the user's responsibility to ensure that usages of this image comply with any relevant licenses for all software contained within.
