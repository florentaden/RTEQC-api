#!/bin/bash

# Defaults that can be overwritten by the user through cmd line args
IMAGE="rteqc-api"
TAG="latest"
NAME="rteqc-api"

HOSTNAME="$(hostname):$IMAGE"
# -- Volume(s) to mount 
HOST_DIR="/mnt/Zoomer/RCET_testing/RCET_RTEQcorrscan/simulations/detections"
CONTAINER_DIR="/tmp/outputs/detections"

# -- Ports
HOST_PORT="8000"
CONTAINER_PORT="8000"



function usage(){
cat <<EOF
Usage: $0 [Options] 
Build or run docker $IMAGE

Optional Arguments:
    -h, --help              Show this message.
    -b, --build             Rebuild the image.
    -c, --clean             Clean out the old image.
    -r, --run               Run the API
    --image                 Provide alternative image name.
    --name                  Provide an alternative name for the running image
    --tag                   Provide alternative tag
    --detect-dir            Porvide alternative detection directory to mount (default: $HOST_DIR)
EOF
}

# Processing command line options
if [[ $# -eq 0 ]] ; then
    usage
    exit 1
fi

while [ $# -gt 0 ]
do
    case "$1" in
        -b | --build) BUILD=true;;
        -r | --run) RUN=true;;
        -c | --clean) CLEAN=true;;
        --image) IMAGE="$2";shift;;
        --name) NAME="$2";shift;;
        --tag) TAG="$2";shift;;
        --detect-dir) HOST_DIR="$2";shift;;
        -h) usage; exit 0;;
        -*) echo "Unknown args: $1"; usage; exit 1;;
esac
shift
done



if [ "${CLEAN}" == "true" ]; then
  echo "Removing current version of ${IMAGE}:${TAG}"
  docker rmi "${IMAGE}:${TAG}"
fi

if [ "${BUILD}" == "true" ]; then
  echo "Building ${IMAGE}:${TAG}"
  # Usually you should be able to re-use the old image, for changes to deps though we need to rebuild
  if [ "${CLEAN}" == "true" ]; then
      docker build --no-cache -t $IMAGE:${TAG} .
  else
      docker build -t $IMAGE .
  fi
fi

if [ ! -d $HOST_DIR ];then
  echo "Directory not found: $HOST_DIR"
  exit 1
fi


if [ "${RUN}" == "true" ]; then
  echo "Running API"
  docker run \
    --rm -d --name $NAME -h $HOSTNAME \
    -p $HOST_PORT:$CONTAINER_PORT \
    -v $HOST_DIR:$CONTAINER_DIR \
    $IMAGE:$TAG

  # -- Find container
  CONTAINER="$(docker ps | grep $NAME:$TAG | awk '{print $1}')"
  PORT="$(docker inspect $CONTAINER | grep HostPort | tail -1 | awk -F\" '{print $4}')"

  echo $NAME:$TAG up and running on container: $CONTAINER
  echo Try
  echo http://`hostname`:$PORT
fi
