#!/usr/bin/env python3
from collections import deque
from networktables import NetworkTables
import numpy as np
import sys
import threading
import cv2
import imutils
import time

CONNECT_TO_SERVER = True
# Normal image, Filter image, Show center band, Show horizontal divider
DEBUG = {
    'test': False,
    'fakeNetworkTables': False,
    'dshow': True,
    'show_img': True,
    'show_filter': True,
    'show_band': True,
    'show_horiz_div': True,
    'show_trails': False,
    'rotate': True
}
PRODUCTION = True # remove some double calculations. not actually.
CENTER_BAND = 100
HORIZONTAL_OFFSET = 125
VERTICAL_JUST = 50
PERCENT_ERROR = 0.25
BUFFER_LEN = 64
ROT_ANGLE = 180
ROT_SCALE = 1.0

def connect():
    cond = threading.Condition()
    notified = [False]

    def connectionListener(connected, info):
        print(info, '; Connected=%s' % connected)
        with cond:
            notified[0] = True
            cond.notify()

    NetworkTables.initialize(server='roborio-2643-frc.local')
    NetworkTables.addConnectionListener(
        connectionListener, immediateNotify=True)

    with cond:
        print("Waiting")
        if not notified[0]:
            cond.wait()

    return NetworkTables.getTable('gs-vision-table')


if CONNECT_TO_SERVER:
    if not DEBUG['fakeNetworkTables']:
        table = connect()
    else:
        table = open('gs_ballfakenetworktable.txt', 'w+')
    DEBUG = {
        'test': False,
        'fakeNetworkTables': DEBUG['fakeNetworkTables'],
        'dshow': False,
        'show_img': False,
        'show_filter': False,
        'show_band': False,
        'show_horiz_div': False,
        'show_trails': False,
        'rotate': True
    }

yellowLower = (15, 100, 0) # 22, 93, 0
yellowUpper = (30, 255, 255) # 45, 255, 255
minRadius = 5 # 10
pts = deque(maxlen=BUFFER_LEN)

if DEBUG['dshow']and sys.platform.startswith('win32'):
    vs = cv2.VideoCapture(0, cv2.CAP_DSHOW)
elif DEBUG['dshow'] and sys.platform.startswith('linux'):
    vs = cv2.VideoCapture(2)
else:
    vs = cv2.VideoCapture(20)

if not CONNECT_TO_SERVER and sys.platform.startswith('win32'):
    vs.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    vs.set(cv2.CAP_PROP_EXPOSURE, -4)
    vs.set(cv2.CAP_PROP_FPS, 30)

time.sleep(1.0)

img_x_size = int(vs.get(cv2.CAP_PROP_FRAME_WIDTH))+VERTICAL_JUST
img_y_size = int(vs.get(cv2.CAP_PROP_FRAME_HEIGHT))+VERTICAL_JUST
img_center = (img_x_size//2, img_y_size//2)


hold_value = 0 # hold val
center_hold = None
while True:
    # grab frame
    frame = vs.read()
    frame = frame[1]

    if DEBUG['rotate']:
        frame = cv2.rotate(frame, cv2.ROTATE_180)

    # frame = imutils.resize(frame, width=600)
    blurred = cv2.GaussianBlur(frame, (11, 11), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # mask yellow, dilate and erode
    mask = cv2.inRange(hsv, yellowLower, yellowUpper)
    if DEBUG['show_filter']:
        cv2.imshow("filter", mask)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    # find contours in the mask and initialize the current
    # (x, y) center of the ball
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    center = None

    # only proceed if at least one contour was found
    if len(cnts) > 0:
        valid_cnts = []
        for c in cnts:
            # c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            
            area = M['m00']
            calc_area = np.pi*(radius**2)
            percent = area/calc_area

            # validate circular.
            if percent >= (1-PERCENT_ERROR) and percent <= (1+PERCENT_ERROR):
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                # only proceed if the radius meets a minimum size
                # draw the circle and centroid on the frame,
                # then update the list of tracked points
                if radius > minRadius:
                    valid_cnts.append(c)

                    if DEBUG['show_img']:
                        cv2.circle(frame, (int(x), int(y)), int(radius),
                        (0, 255, 255), 2)
                        cv2.circle(frame, center, 5, (0, 0, 255), -1)
            else:
                continue # useless else case lol.


        #track the largest
        if len(valid_cnts) > 0:
            c = max(valid_cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)

            # area = M['m00']
            # calc_area = np.pi*(radius**2)
            # percent = area/calc_area

            # if percent >= (1-PERCENT_ERROR) and percent <= (1+PERCENT_ERROR):
                # if radius > minRadius:
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
            center_hold = center
            hold_value = 5

            if DEBUG['show_img']:
                cv2.circle(frame, (int(x), int(y)), int(radius),
                (0, 255, 255), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), -1)
                # else:
                    # center = None
            # else:
                # center = None
        else:
            center = None
    else:
        center = None

    if hold_value >= 0:
        hold_value -= 1

    if CONNECT_TO_SERVER:
        if not DEBUG['fakeNetworkTables']:
            if center_hold is None:
                table.putBoolean('has_target', False)
                table.putBoolean('near', False)
            else:
                table.putBoolean('has_target', True)
                if center_hold[0] < (img_center[0] - CENTER_BAND):
                    table.putNumber('left_exceeded', ((img_center[0] - CENTER_BAND) - center_hold[0]))
                else:
                    table.putNumber('left_exceeded', 0)

                if center_hold[0] > (img_center[0] + CENTER_BAND):
                    table.putNumber('right_exceeded', (center_hold[0] - (img_center[0] + CENTER_BAND)))
                else:
                    table.putNumber('right_exceeded', 0)
                
                if center_hold[1] > (img_center[1] + HORIZONTAL_OFFSET):
                    table.putBoolean('near', True)
                else:
                    table.putBoolean('near', False)
        else:
            table.write(str(center).ljust(15)+str(center_hold).ljust(15)+str(hold_value).ljust(5)+'\n')
            table.flush()


    # if center_hold is None:
    # 	print("DED", hold_value)
    # else:
    # 	print("POTATO", hold_value)

    # update the points queue
    if hold_value > 0:
        pts.appendleft(center_hold)
    else:
        center_hold = center
        pts.appendleft(center) # clears pts list

    if DEBUG['test']:
        print(str(center).ljust(10), str(center_hold).ljust(10), str(hold_value).ljust(5), end='')
        if center_hold is None:
                print('False ', end='')
        else:
            print('True ', end='')
            if center_hold[0] < (img_center[0] - CENTER_BAND):
                print('left_exceeded:' + str((img_center[0] - CENTER_BAND) - center_hold[0]), end='')

            if center_hold[0] > (img_center[0] + CENTER_BAND):
                print('right_exceeded:' + str((center_hold[0] - (img_center[0] + CENTER_BAND))), end='')
                
            if center_hold[1] > (img_center[1] + HORIZONTAL_OFFSET):
                print('near', end='')
            
        print('')
        
    if DEBUG['show_img']:
        # loop over the set of tracked points
        for i in range(1, len(pts)):
            # if either of the tracked points are None, ignore them
            if pts[i - 1] is None or pts[i] is None:
                break

            # otherwise, compute the thickness of the line and
            # draw the connecting lines
            thickness = int(np.sqrt(BUFFER_LEN / float(i + 1)) * 2.5)
            cv2.line(frame, pts[i - 1], pts[i], (0, 0, 255), thickness)

    # show the frame to our screen
    if DEBUG['show_img']:
        if DEBUG['show_band']:
            left_bound = img_center[0] - CENTER_BAND
            right_bound = img_center[0] + CENTER_BAND
            frame = cv2.line(frame,(left_bound, 0),(left_bound, img_y_size),(252, 3, 119),3)
            frame = cv2.line(frame,(right_bound, 0),(right_bound, img_y_size),(252, 3, 119),3)

        if DEBUG['show_horiz_div']:
            horiz_band = img_center[1] + HORIZONTAL_OFFSET
            frame = cv2.line(frame,(0, horiz_band),(img_x_size, horiz_band),(252, 3, 119),3)

        cv2.imshow("Frame", frame)
        
    key = cv2.waitKey(1) & 0xFF

    # if the 'q' key is pressed, stop the loop
    if key == ord("q"):
        break

vs.release()
cv2.destroyAllWindows()

if CONNECT_TO_SERVER and DEBUG['fakeNetworkTables']:
    table.truncate(0)