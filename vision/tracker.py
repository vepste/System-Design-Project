
import cv2
import numpy as np
import tools
import vision
import math
from colors import BGR_COMMON
#from findYUV import CalibrationGUI

class MyTracker(object):

    def __init__(self, calibration, pitch_number, extras = False):
        self.calibration    = calibration
        self.time           = tools.current_milli_time()
        self.pitch_number = pitch_number
        self.ball_queue     = []
        self.extras         = extras


    def processed_mask(self, image, color):
        BLUR_VALUE      = self.calibration[color]['blur']
        MIN_VALUE       = self.calibration[color]['min']
        MAX_VALUE       = self.calibration[color]['max']
        CONTRAST_VALUE  = self.calibration[color]['contrast']
        OPEN_KERNEL     = (int)(self.calibration[color]['open_kernel'])
        CLOSE_KERNEL    = (int)(self.calibration[color]['close_kernel'])
        ERODE_KERNEL    = (int)(self.calibration[color]['erode'])
        HIGHPASS_VALUE  = self.calibration[color]['highpass']
        OBJECT_COUNT    = (int)(self.calibration[color]['object_count'])

        # prevent damage to original image
        frame = image.copy()

        # Apply gaussian blur to soften noise
        blur = BLUR_VALUE
        if blur >= 1:
            if blur % 2 == 0:
                blur += 1
            frame = cv2.GaussianBlur(frame, (blur, blur), 0)

        # apply contrast
        contrast = CONTRAST_VALUE
        if contrast >= 1.0:
            frame = cv2.add(frame, np.array([contrast]))

        # get initial frame mask
        frame_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        min_color = MIN_VALUE
        max_color = MAX_VALUE
        frame_mask = cv2.inRange(frame_yuv, min_color, max_color)


        if OPEN_KERNEL >= 1:
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (OPEN_KERNEL,OPEN_KERNEL))
                frame_mask = cv2.morphologyEx(frame_mask,
                                              cv2.MORPH_OPEN,
                                              kernel,
                                              iterations=1)
        if CLOSE_KERNEL >= 1:
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_KERNEL,CLOSE_KERNEL))
                frame_mask = cv2.morphologyEx(frame_mask,
                                              cv2.MORPH_CLOSE,
                                              kernel,
                                              iterations=1)
        if ERODE_KERNEL >= 1:
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ERODE_KERNEL,ERODE_KERNEL))
                frame_mask = cv2.erode(frame_mask,
                                        kernel,
                                        iterations=1)

        # NOT APPLYING HIGHPASS
        #out = frame
        #hp = int(HIGHPASS_VALUE)
        #frame_mask = CalibrationGUI.highpass(frame_mask, frame, hp)
        #cv2.imshow('frame mask'+str(color),frame_mask)

        return frame_mask

    def count_pixels(self, color, mask):
        MIN_DATA    = self.calibration[color]['min']
        MAX_DATA    = self.calibration[color]['max']
        dst         = cv2.inRange(mask, MIN_DATA, MAX_DATA)

        return cv2.countNonZero(dst)


    def recognize_plates(self, image, robot_mask, ball_mask, draw=True):
        # pink = self.calibrations['pink']

        frame = image.copy()

        #plate_mask = cv2.subtract(robot_mask, ball_mask)
        plate_mask = robot_mask

        #cv2.imshow("plate_mask", plate_mask)

        # set processing values
        BLUR   = 11;
        KERNEL = 7;

        # process plate mask for whole plate detection
        plate_mask = cv2.GaussianBlur(plate_mask, (BLUR, BLUR), 0)
        #plate_mask = cv2.bilateralFilter(plate_mask,9,75,75)
        kernel     = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (KERNEL,KERNEL))
        plate_mask = cv2.morphologyEx(plate_mask, cv2.MORPH_CLOSE, kernel)
        plate_mask = cv2.morphologyEx(plate_mask, cv2.MORPH_OPEN, kernel)

        # get contours from the mask
        _, contours, _ = cv2.findContours(plate_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # get number of plates expected
        OBJECT_COUNT = (int)(self.calibration['plate']['object_count'])
        sorted_cnt   = sorted(contours, key=lambda cnt: cv2.contourArea(cnt))
        contours     = sorted_cnt[-OBJECT_COUNT:]

        contour_frame = np.zeros((480, 640, 3), np.uint8)
        cv2.drawContours(contour_frame, contours, -1, (255,255,255), cv2.FILLED);
        if self.extras:
            cv2.imshow('all-contours mask', contour_frame)

        cnt_index  = 0       # contour  index to process
        robot_data = []     # robot data to be returned

        if draw:
            test_mask  = np.zeros((480, 640, 3), np.uint8)
        for cnt in contours:

            #TODO check if contours have a square shape
            # check for countours of decent size
            if cv2.contourArea(cnt) < 300 or cv2.contourArea(cnt) > 1500:
                cnt_index += 1
                continue

            # copy the contour part from the image
            contour_frame = np.zeros((480, 640, 3), np.uint8)
            #TODO cleanup @vesko
            #old
            #cv2.drawContours(contour_frame, contours, cnt_index, (255,255,255), cv2.FILLED);
            #new
            rect = cv2.minAreaRect(cnt)
            box  = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(contour_frame, [box], -1, (255,255,255), cv2.FILLED)

            # find centre
            m = cv2.moments(cnt, False);
            (cx, cy) = int(m['m10'] / (m['m00'] + 0.001)), int(m['m01'] / (m['m00'] + 0.001))
            #----
            contour_frame = cv2.bitwise_and(image, contour_frame)

            if draw:
                test_mask     = cv2.bitwise_or(test_mask, contour_frame)

            contour_frame = cv2.cvtColor(contour_frame, cv2.COLOR_BGR2YUV)



            #new
            bisectors = box
            bisectors = (bisectors + np.roll(bisectors, 2)) / 2

            middle_dot_rect = cv2.minAreaRect(bisectors)
            middle_dot_mask = np.zeros((480, 640, 3), np.uint8)
            cv2.ellipse(middle_dot_mask, middle_dot_rect, (255,255,255), -1)
            middle_dot_mask = cv2.bitwise_and(contour_frame, middle_dot_mask)
            # count blue coloured pixels
            blue_no   = self.count_pixels('blue', middle_dot_mask)
            # count yellow coloured pixels
            yellow_no = self.count_pixels('yellow', middle_dot_mask)

            #old
            # # count blue coloured pixels
            # blue_no   = self.count_pixels('blue', contour_frame)
            # # count yellow coloured pixels
            # yellow_no = self.count_pixels('yellow', contour_frame)
            #-----

            #new
            green_no = 0
            pink_no = 0
            for i in range(4):
                outer_dots_mask = np.zeros((480, 640, 3), np.uint8) * 4
                vertices = np.array([ box[i], bisectors[i], np.array([cx,cy]), bisectors[(i + 1) % 4] ])
                outer_dot_rect = cv2.minAreaRect(vertices)
                cv2.ellipse(outer_dots_mask, outer_dot_rect, (255,255,255), -1)
                # count green coloured pixels
                outer_dots_mask = cv2.bitwise_and(contour_frame, outer_dots_mask)
                green_pixels  = self.count_pixels('bright_green', outer_dots_mask)
                # count pink coloured pixels
                pink_pixels   = self.count_pixels('pink', outer_dots_mask)
                if (green_pixels > pink_pixels):
                    green_no += 1
                else:
                    pink_no += 1
            # calculate ratios for definig teams
            blue_yellow_ratio = blue_no / (yellow_no + 1)
            pink_green_ratio  = pink_no / (green_no + 1)
            #old
            # # count green coloured pixels
            # green_no  = self.count_pixels('bright_green', contour_frame)
            # # count pink coloured pixels
            # pink_no   = self.count_pixels('pink', contour_frame)
            # print('orig_green '+str(green_no))
            # print('orig_pink '+str(pink_no))
            #
            # # calculate ratios for definig teams
            # blue_yellow_ratio = blue_no / (yellow_no + 1)
            # pink_green_ratio  = pink_no / (green_no + 1)
            #------

            # find the mass centre of the single circle (to find angle)
            if pink_green_ratio < 0.5:
                #pink
                min_range = self.calibration['pink']['min']
                max_range = self.calibration['pink']['max']
            else:
                #green
                min_range = self.calibration['bright_green']['min']
                max_range = self.calibration['bright_green']['max']

            tmp_mask = cv2.inRange(contour_frame, min_range, max_range)
            m        = cv2.moments(tmp_mask, True)
            (tx, ty) = int(m['m10'] / (m['m00'] + 0.001)), int(m['m01'] / (m['m00'] + 0.001))
            if draw:
                cv2.circle(image, (tx, ty), 5, (255, 255, 255), -1)

            if draw:
                cv2.drawContours(test_mask,[box],0,(0,0,255),2)

            minx, miny, maxx, maxy = 100000,100000,0,0
            for (x, y) in box:
                miny = min(miny, y)
                minx = min(minx, x)
                maxy = max(miny, y)
                maxx = max(minx, x)

            # find the closest corner to the mass centre
            closest_corner = 0
            distance       = 10000000
            for i in range(4):
                tmp_dist = (box[i][0] - tx) * (box[i][0] - tx) + (box[i][1] - ty) * (box[i][1] - ty)
                if (tmp_dist < distance):
                    distance       = tmp_dist
                    closest_corner = i

            if draw:
                cv2.circle(image, (box[closest_corner][0], box[closest_corner][1]), 5, (100, 100, 255), -1)

            if pink_green_ratio < 0.5:
                group = 'bright_green'
            else:
                group = 'pink'

            if blue_yellow_ratio < 1.0:
                team = 'yellow'
            else:
                team = 'blue'

            # get direction
            direction_vector_x = -(box[(closest_corner) % 4][0] - box[(closest_corner + 1) % 4][0])
            direction_vector_y = -(box[(closest_corner) % 4][1] - box[(closest_corner + 1) % 4][1])
            angle = math.atan2(direction_vector_y, direction_vector_x) + math.pi / 2
            if angle > math.pi:
                angle -= 2 * math.pi
            angle = angle / 2 / math.pi * 360

            angle -= 90
            robot_data.append({'center': (cx, cy), 'angle': angle, 'team': team, 'group': group})

            if draw:
                cv2.line(image, (cx, cy), (cx + direction_vector_x, cy + direction_vector_y),(255, 255, 255), 3)
                cv2.drawContours(image,[box],0,(0,0,255),2)
                #cv2.putText(self.frame, "PLATE: b-y ratio %lf p-g ratio %lf" % (byr, pgr), (maxx, maxy), cv2.FONT_HERSHEY_SIMPLEX, 0.3, None, 1)
                #cv2.putText(image, "PLATE: team %s group %s" % (team, group), (maxx, maxy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, None, 1)
                if self.extras:
                    cv2.imshow('image', image)

            cnt_index += 1

        if self.extras:
            cv2.imshow("contours ", test_mask)

        contour_mask = cv2.cvtColor(test_mask, cv2.COLOR_BGR2GRAY)
        _, contour_mask = cv2.threshold(contour_mask,0,255,cv2.THRESH_BINARY)

        # print(robot_data)
        return robot_data, image, contour_mask

    def get_masks(self, image):

        ball_mask  = None
        plate_mask = None

        # Ball mask
        red_mask        = self.processed_mask(image, 'red')
        violet_mask     = self.processed_mask(image, 'violet')
        ball_mask       = cv2.bitwise_or(red_mask, violet_mask)

        # Robot mask
        #plate_mask      = self.processed_mask(image, 'plate')
        pink_mask       = self.processed_mask(image, 'pink')
        plate_mask       = self.processed_mask(image, 'plate')
        green_mask       = self.processed_mask(image, 'bright_green')
        yellow_mask       = self.processed_mask(image, 'yellow')
        blue_mask       = self.processed_mask(image, 'blue')

        # combine all colors into one plate mask
        plate_mask      = cv2.bitwise_or(pink_mask, pink_mask)
        plate_mask      = cv2.bitwise_or(plate_mask, green_mask)
        plate_mask      = cv2.bitwise_or(plate_mask, yellow_mask)
        plate_mask      = cv2.bitwise_or(plate_mask, blue_mask)

        # pink and violet intercept
        violet_mask     = cv2.subtract(violet_mask, pink_mask)
        ball_mask       = cv2.bitwise_or(red_mask, violet_mask)

        return ball_mask, plate_mask

    def recognize_ball(self, image, robot_mask, ball_mask):
        """
        :return: radius, center, modified_frame
        """
        #cv2.imshow("ball_mask", ball_mask)
        ball_mask = cv2.subtract(ball_mask, robot_mask)

        #cv2.imshow("robot_mask", robot_mask)

        # extract contours
        #cv2.imshow("ball_mask", ball_mask)
        _, contours, _  = cv2.findContours(ball_mask.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        largest_contour = self.get_largest_contour(contours)

        cv2.drawContours(image, contours, -1, (255,255,0), 1)
        # Ball is not detected
        if largest_contour is None or cv2.contourArea(largest_contour) < 10:
            #print("Ball is not detected!")
            return 0, None, ball_mask

        ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)
        center = (x, y)
        self.ball_queue.append((x, y))

        if len(self.ball_queue) > 5:
            self.ball_queue = self.ball_queue[1:]
        ball_vector_x = int(self.ball_queue[-1][0] - self.ball_queue[0][0])
        ball_vector_y = int(self.ball_queue[-1][1] - self.ball_queue[0][1])

        x = int(x)
        y = int(y)

        direction = (ball_vector_x, ball_vector_y)
        cv2.line(image, (x, y), (x + ball_vector_x, y + ball_vector_y), (255, 255, 255))

        # Draw ball outline
        cv2.circle(image,(int(x), int(y)),4,(0,0,0))
        cv2.circle(image,(int(x), int(y)),5,BGR_COMMON['red'])
        cv2.circle(image,(int(x), int(y)),6,(0,0,0))

        if self.extras:
            #cv2.`imshow`("ball_image ", image)
            cv2.imshow("ball_mask", ball_mask)

        return radius, center, direction, image

    def get_largest_contour(self, contours):
        areas = [cv2.contourArea(c) for c in contours]
        return contours[np.argmax(areas)] if len(areas) > 0 else None

    def get_world_state(self, image):
        """
        Retrieves all data from vision system.
        """

        data = {'ball': {'center': (-1, -1), 'radius': 0, 'direction':(0,0)}, 'robots': []}

        frame = image
        fore = image.copy()

        # background image used for background subtraction
        #TODO make interface to acquire such image
        og = cv2.imread('currBg_' + str(self.pitch_number) + '.png')
        og = cv2.GaussianBlur(og,(3,3),0)
        og = cv2.cvtColor(og,cv2.COLOR_BGR2YUV)

        #background subtraction
        fore = cv2.GaussianBlur(fore,(3,3),0)
        yuv = cv2.cvtColor(fore,cv2.COLOR_BGR2YUV)
        yuv = cv2.absdiff(yuv, og)
        yuv = cv2.cvtColor(yuv,cv2.COLOR_BGR2GRAY)
        #TODO create interface to change variable
        mask = cv2.inRange(yuv, 15, 255) #################TODO interface variable - increase if extra bits, decrease otherwise
        #TODO mask out sides of the pich
        #mask = cv2.bitwise_and(mask, mask, mask=sides)
        mask = cv2.GaussianBlur(mask,(11,11),0) ############## variable
        retval,mask = cv2.threshold(mask,0,255,cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask = cv2.GaussianBlur(mask,(19,19), 0) ############## variable
        frame = cv2.bitwise_and(frame,frame, mask=mask)
        if self.extras:
            cv2.imshow('bg sub', frame)
        #------
        # TESTING DIFFERENT BACKGROUND SUBTRACTION FOR PRESENTATION
        # GENERIC OPENCV BG SUBTRACTION
        # og = cv2.imread('currBg_' + str(self.pitch_number) + '.png')
        # og = cv2.GaussianBlur(og,(5,5),0)
        # #og = cv2.cvtColor(og,cv2.COLOR_BGR2YUV)
        # kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
        # fgbg = cv2.createBackgroundSubtractorMOG2(history=1)
        # fgmask = fgbg.apply(og, learningRate=1)
        # fore = cv2.GaussianBlur(fore,(5,5),0)
        # fgmask = fgbg.apply(fore)
        # fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
        # if self.extras:
        #      cv2.imshow('bg sub', cv2.bitwise_and(frame, frame, mask=fgmask))
        #------

        ball_mask   = None
        robot_mask  = None
        ball_center = None

        ball_mask, robot_mask = self.get_masks(frame);
        if self.extras:
            cv2.imshow("ball_mask ", ball_mask)
            cv2.imshow("robot_mask ", robot_mask)

        # Robots recognition code goes here.
        # Store things into data dictionary.
        plate_data, modified_frame, robot_mask = self.recognize_plates(image=image.copy(), robot_mask=robot_mask, ball_mask=ball_mask)
        for robot in plate_data:
            data['robots'].append(robot)

        ball_reck = self.recognize_ball(image=image, robot_mask=robot_mask, ball_mask=ball_mask)

        if len(ball_reck) == 4:
            ball_radius, ball_center, ball_direction, ball_image = ball_reck

        if ball_center is not None:
            # print("BALL - x : %d y : %d radius : %d" % (ball_center[0], ball_center[1], ball_radius))
            data['ball']['radius'] = ball_radius
            data['ball']['center'] = (ball_center[0], ball_center[1])
            data['ball']['direction'] = ball_direction


        # Should return data dictionary and the modified frame to the drawing utilities.
        return data, modified_frame


# Test tracking objects of certain color
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pitch", help="[0] Main pitch, [1] Secondary pitch")
   # parser.add_argument("color", help="The color to adjust")
    args = parser.parse_args()

    pitch_number = int(args.pitch)

    capture = vision.Camera(pitch=pitch_number)
    #capture = cv2.VideoCapture('output.avi')
    calibration = tools.get_colors(pitch=pitch_number)
    croppings = tools.get_croppings(pitch=pitch_number)
    tracker = MyTracker(calibration=calibration, pitch_number=pitch_number)

    while True:

        frame = capture.get_frame()
        #re,frame = capture.read()

        data, modified_frame = tracker.get_world_state(frame)

        cv2.imshow('Tracker', modified_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    capture.release()
    cv2.destroyAllWindows()
