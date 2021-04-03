if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

rmmod v4l2loopback
modprobe v4l2loopback video_nr=21,22,23,24,25
ffmpeg -f video4linux2 -i /dev/v4l2/by-id/usb-046d_HD_Pro_Webcam_C920_5AB6901F-video-index0 \
-codec copy -f v4l2 /dev/video21 \
-codec copy -f v4l2 /dev/video22 \
-codec copy -f v4l2 /dev/video23 \
-codec copy -f v4l2 /dev/video24 \
-codec copy -f v4l2 /dev/video25