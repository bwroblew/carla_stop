import xml.etree.ElementTree as ET
import math
import random

class BndBox:

    def __init__(self, name, xmin, xmax, ymin, ymax):

        self.name = name

        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax

        self.width = xmax - xmin
        self.height = ymax - ymin

        self.center_x = xmin + self.width / 2
        self.center_y = ymin + self.height / 2

        self.area = self.width * self.height

    def get_cent_dist(self, x, y):
        return math.sqrt((self.center_x - x) ** 2 + (self.center_y - y) ** 2)

    def get_min_dist(self, x, y):
        """
        Not using one liners to be more clear ;)
        :param x:
        :param y:
        :return:
        """
        if self.xmin <= x <= self.xmax:
            if self.ymin >= y:
                return self.ymin - y
            elif self.ymax <= y:
                return y - self.ymax
            else:
                return -(min(abs(self.ymin - y), abs(self.ymax - y)))
        elif self.ymin <= y <= self.ymax:
            if self.xmin >= x:
                return self.xmin - x
            elif self.xmax <= x:
                return x - self.xmax
            else:
                return -(min(abs(self.xmin - x), abs(self.xmax - x)))
        else:
            y_dist = min(abs(self.ymin - y), abs(self.ymax - y))
            x_dist = min(abs(self.xmin - x), abs(self.xmax - x))
            return math.sqrt(y_dist ** 2 + x_dist ** 2)


class StopDetector:

    def __init__(self):
        # minimum ratio of light area and screen area
        self.light_area_threshold = 0.00065

        self.screen_width = 800
        self.screen_height = 600

        self.max_eu_lights = 3
        # number of frames without vision of lights to clear previous states
        self.not_seen_threshold = 3
        self.prev_states = []

    def detect_actual(self, xml_file):
        """
        Detect light state based on current frame
        :param xml_file:
        :return:
        """
        objects = []
        root = ET.parse(xml_file).getroot()

        self.screen_width = int(root.find('size/width').text)
        self.screen_height = int(root.find('size/height').text)

        us_lights = False

        for object in root.findall('object'):

            name = object.find('name').text
            if "limit" in name:
                continue

            xmin = int(object.find('bndbox/xmin').text)
            ymin = int(object.find('bndbox/ymin').text)
            xmax = int(object.find('bndbox/xmax').text)
            ymax = int(object.find('bndbox/ymax').text)
            objects.append(BndBox(name, xmin, xmax, ymin, ymax))

            if "group" in name:
                us_lights = True

        if len(objects) > self.max_eu_lights:
            us_lights = True

        if us_lights:
            return self.check_us(objects)
        else:
            return self.check_eu(objects)

    def check_eu(self, lights):
        """
        Method returns current European light states
        :param lights:
        :return:
        """
        to_remove = []
        for light in lights:
            if light.area / (self.screen_height * self.screen_width) <= self.light_area_threshold:
                to_remove.append(light)
        lights -= to_remove

        # if not working replace with "vertical line check"
        if not lights:
            return None

        max_area = -1
        max_area_object = None
        for light in lights:
            if light.area > max_area:
                max_area = light.area
                max_area_object = light

        return max_area_object

    def check_us(self, lights):
        """
        Method returns current American light states
        :param lights:
        :return:
        """
        return None
