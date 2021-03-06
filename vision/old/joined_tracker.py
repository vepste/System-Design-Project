
import cv2
import numpy as np
import tools
from colors import BGR_COMMON
from findYUV import CalibrationGUI


# For OpenCV2 image display
WINDOW_NAME = 'Tracker' 

class Vision(object):
    calibrations = None
    camera = None
    frame = None

    def __init__(self, file_path=None):
        self.camera = Camera()

        if file_path is None:
            self.calibrations = get_calibrations()
        else:
            self.calibrations = get_calibrations(file_path)
        self.camera.setup_camera(self.calibrations['auto_calibration'])
        # croppings = self.calibrations['croppings']
        self.ball_queue = []
        # assert croppings['y2'] - croppings['y1'] == MAX_HEIGHT
        # assert croppings['x2'] - croppings['x1'] == MAX_WIDTH


    def recognize_ball(self):
        """
        Recgonitions where the radius is

        :return: radius, center, modified_frame
        """
        modified_frame = self.frame
        ball = self.calibrations['ball']
        open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ball['morph_open'], ball['morph_open']))
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ball['morph_close'], ball['morph_close']))

        # Convert the frame to HSV color space.
        modified_frame = cv2.cvtColor(modified_frame, cv2.COLOR_BGR2HSV)

        # print(ball)

        red_mask = cv2.inRange(modified_frame, (ball['hue1_low'], ball['sat_low'], ball['val_low']), (ball['hue1_high'], ball['sat_high'], ball['val_high']))
        violet_mask = cv2.inRange(modified_frame, (ball['hue2_low'], ball['sat_low'], ball['val_low']), (ball['hue2_high'], ball['sat_high'], ball['val_high']))
        modified_frame = cv2.bitwise_or(red_mask, violet_mask)

        modified_frame = cv2.morphologyEx(modified_frame, cv2.MORPH_CLOSE, open_kernel)
        modified_frame = cv2.morphologyEx(modified_frame, cv2.MORPH_OPEN, close_kernel)

        contours = cv2.findContours(modified_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

        largest_contour = self.get_largest_contour(contours)

        # Ball is not detected
        if largest_contour is None:
            print("Ball is not detected!")
            return 0, None, modified_frame

        ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)
        center = (x, y)
        self.ball_queue.append((x, y))
        if len(self.ball_queue) > 5:
            self.ball_queue = self.ball_queue[1:]
        ball_vector_x = int(self.ball_queue[-1][0] - self.ball_queue[0][0])
        ball_vector_y = int(self.ball_queue[-1][1] - self.ball_queue[0][1])
        x = int(x)
        y = int(y)
        cv2.line(self.frame, (x, y), (x + ball_vector_x, y + ball_vector_y), (255, 255, 255))

        cv2.circle(self.frame, (int(x), int(y)), int(radius + 3), (0, 0, 0), -1)
        # center = self.get_contour_center(largest_contour)

        return radius, center, modified_frame

    def get_largest_contour(self, contours):
        areas = [cv2.contourArea(c) for c in contours]
        return contours[np.argmax(areas)] if len(areas) > 0 else None

    def get_contour_center(c):

        M = cv2.moments(c)
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

    def recognize_plates(self):
        """
        This is a mess and needs to be redone. The drawing stuff should
        go into GUI. Probably get four corners coordinates, then draw them
        there instead of here.

        TODO: compute the angle.
        """
        # pink = self.calibrations['pink']

        frame = self.frame.copy()
        frame = cv2.GaussianBlur(frame, (5, 5), 0)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        v1_min, v2_min, v3_min, v1_max, v2_max, v3_max = 27, 150, 106, 255, 255, 255
        not_grey_mask = cv2.inRange(frame, (v1_min, v2_min, v3_min), (v1_max, v2_max, v3_max))
        pink_mask =  cv2.inRange(frame, (150, 100, 100), (255, 255, 255))
        pink_mask = cv2.dilate(pink_mask, None, iterations=1)
        plate_mask = cv2.bitwise_or(not_grey_mask, pink_mask)

        plate_mask = cv2.GaussianBlur(plate_mask, (15, 15), 0)
        kernel =  cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        plate_mask = cv2.morphologyEx(plate_mask, cv2.MORPH_CLOSE, kernel)
        plate_mask = cv2.morphologyEx(plate_mask, cv2.MORPH_OPEN, kernel)
        cv2.imshow("plate detection", plate_mask)

        contours = cv2.findContours(plate_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

        cnt_index = 0
        robot_data = []
        for cnt in contours:
            # print cv2.contourArea(cnt)
            if cv2.contourArea(cnt) < 1000:
                cnt_index += 1
                continue
            # copy the contour part from the image
            contour_frame = np.zeros((480,640,3), np.uint8)
            cv2.drawContours(contour_frame, contours, cnt_index, (255,255,255), cv2.FILLED);

            #cv2.imshow('abc' + str(cnt_index), image)
            #cv2.imshow('adas' + str(cnt_index), tmp)
            contour_frame = cv2.bitwise_and(self.frame, contour_frame)
            #cv2.imshow('adaasds' + str(cnt_index), contour_frame)

            contour_frame = cv2.cvtColor(contour_frame, cv2.COLOR_BGR2HSV)
            #if cnt_index == 2:
            #    cv2.imshow("this", tmp)
            # count blue coloured pixels
            blue_no = self.count_pixels('blue', contour_frame)
            # print("blue", blue_no)
            # count yellow coloured pixels
            yellow_no = self.count_pixels('yellow', contour_frame)
            # print("yellow", yellow_no)
            # count green coloured pixels
            green_no = self.count_pixels('green', contour_frame)
            # print("green", green_no)
            # count pink coloured pixels
            pink_no =  self.count_pixels('pink', contour_frame)
            # pink_no += count_pixels(0, 0, 0, 25, 255, 255, tmp)
            # print("pink", pink_no)

            byr = blue_no / (yellow_no + 1)
            pgr = pink_no / (green_no + 1)
            # print("blue yellow ratio", byr)
            # print("pink green ratio", pgr)

            # find the mass centre of the single circle (to find angle)
            if pgr < 0.5:
                v1_min, v2_min, v3_min, v1_max, v2_max, v3_max = 160, 100, 80, 180, 255, 255
            else:
                v1_min, v2_min, v3_min, v1_max, v2_max, v3_max = 50, 100, 100, 90, 255, 255
            tmp_mask = cv2.inRange(contour_frame, (v1_min, v2_min, v3_min), (v1_max, v2_max, v3_max))
            m = cv2.moments(tmp_mask, True)
            (tx, ty) = int(m['m10'] / (m['m00'] + 0.001)), int(m['m01'] / (m['m00'] + 0.001))
            # print(tx, ty)
            cv2.circle(self.frame, (tx, ty), 5, (255, 255, 255), -1)

            # find the rotated rectangle around the plate
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            # print(box)
            minx, miny, maxx, maxy = 100000,100000,0,0
            for (x, y) in box:
                miny = min(miny, y)
                minx = min(minx, x)
                maxy = max(miny, y)
                maxx = max(minx, x)

            # find the closest corner to the mass centre
            closest_corner = 0
            distance = 10000000
            # cv2.circle(image, (tx, ty), 3, (100, 100, 100), -1)
            for i in range(4):
                tmp_dist = (box[i][0] - tx) * (box[i][0] - tx) + (box[i][1] - ty) * (box[i][1] - ty)
                # print(i, tmp_dist)
                if (tmp_dist < distance):
                    distance = tmp_dist
                    closest_corner = i
            cv2.circle(self.frame, (box[closest_corner][0], box[closest_corner][1]), 5, (100, 100, 255), -1)

            # find centre
            m = cv2.moments(cnt, False);
            (cx, cy) = int(m['m10'] / (m['m00'] + 0.001)), int(m['m01'] / (m['m00'] + 0.001))

            if pgr < 0.5:
                group = 'green'
            else:
                group = 'pink'

            if byr < 1.0:
                team = 'yellow'
            else:
                team = 'blue'

# draw direction line
            direction_vector_x = -(box[(closest_corner) % 4][0] - box[(closest_corner + 1) % 4][0])
            direction_vector_y = -(box[(closest_corner) % 4][1] - box[(closest_corner + 1) % 4][1])
            angle = math.atan2(direction_vector_y, direction_vector_x) + math.pi / 2
            if angle > math.pi:
                angle -= 2 * math.pi
            angle = angle / 2 / math.pi * 360
            cv2.putText(self.frame, "angle %lf" % (angle), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, None, 1)

            cv2.line(self.frame, (cx, cy), (cx + direction_vector_x, cy + direction_vector_y),(255, 255, 255), 3)
            robot_data.append({'center': (cx, cy), 'angle': angle, 'team': team, 'group': group})
            cv2.drawContours(self.frame,[box],0,(0,0,255),2)
            #cv2.putText(self.frame, "PLATE: b-y ratio %lf p-g ratio %lf" % (byr, pgr), (maxx, maxy), cv2.FONT_HERSHEY_SIMPLEX, 0.3, None, 1)
            cv2.putText(self.frame, "PLATE: team %s group %s" % (team, group), (maxx, maxy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, None, 1)
            cnt_index += 1

        # print(robot_data)
        return robot_data, frame

    def count_pixels(self, type, mask):
        data = self.calibrations[type]
        dst = cv2.inRange(mask, (data['hue1_low'], data['sat_low'], data['val_low']), (data['hue1_high'], data['sat_high'], data['val_high']))
        return cv2.countNonZero(dst)

    def get_world_state(self):
        """
        Retrieves all data from vision system.
        """
        data = {'ball': {'center': (0, 0), 'radius': 0}, 'robots': []}

        self.frame = self.camera.get_frame()
        # Maybe crop the frame here?

        ball_mask = None
        ball_radius, ball_center, ball_mask = self.recognize_ball()
        if ball_center is not None:
            # print("BALL - x : %d y : %d radius : %d" % (ball_center[0], ball_center[1], ball_radius))
            data['ball']['radius'] = ball_radius
            data['ball']['center'] = (ball_center[0], ball_center[1])


        # Robots recognition code goes here.
        # Store things into data dictionary.
        plate_data, modified_frame = self.recognize_plates()
        for robot in plate_data:
            data['robots'].append(robot)

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
    calibration = tools.get_colors(pitch_number)
    tracker = MyTracker(colors=['red', 'blue', 'bright_green','pink','yellow'], calibration=calibration)

    while True:

        frame = capture.get_frame()

        #tracker.adjust_color(image)
        tracker.track_points(frame)

        cv2.imshow('Tracker', frame)
      
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    capture.release()
    cv2.destroyAllWindows()