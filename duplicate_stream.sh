ffmpeg -f video4linux2 -i /dev/video0 -codec copy -f v4l2 /dev/video1  -codec copy -f v4l2 /dev/video2 -codec copy -f v4l2 /dev/video3 -codec copy -f v4l2 /dev/video4