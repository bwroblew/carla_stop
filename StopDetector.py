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
        """
        Calculates the distance between point x,y and center of the box
        :param x: x parameter of point
        :param y: y parameter of point
        :return: distance from point to center of box
        """
        return math.sqrt((self.center_x - x) ** 2 + (self.center_y - y) ** 2)

    def get_min_dist(self, x, y):
        """
        Calculates the minimum distance from point x,y to object - to the closest edge or vertex of object
        :param x: x parameter of point
        :param y: y parameter of point
        :return: distance from point to the box
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

    def intersect_ratio(self, outer_group):
        """
        Returns percentage of self area being inside of outer_group area.
        :param outer_group: group to check intersect with
        :return: Percentage of self object being inside of outer_group
        """
        x_overlap = max(0, min(self.xmax, outer_group.xmax) - max(self.xmin, outer_group.xmin))
        y_overlap = max(0, min(self.ymax, outer_group.ymax) - max(self.ymin, outer_group.ymin))
        overlap_area = x_overlap * y_overlap
        return float(overlap_area) / self.area


class StopDetector:

    def __init__(self):
        # minimum ratio of light area and screen area
        self.light_area_threshold = 0.00065

        self.screen_width = 800
        self.screen_height = 600

        self.being_inside_ratio = 0.8

        self.max_eu_lights = 3
        # number of frames without vision of lights to clear previous states
        self.not_seen_threshold = 3
        self.prev_states = []

    def check_light(self, xml_file):
        """
        Detect light state based on current frame
        :param xml_file: xml file with boxes
        :return: None
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
            selected = self.check_us(objects)
        else:
            selected = self.check_eu(objects)

        selected_name = selected.name.split("_")[0]
        self.prev_states.append(selected_name)

    def check_eu(self, lights):
        """
        Method returns selected European light
        :param lights: list of all light boxes
        :return: selected box
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
        biggest_object = None
        for light in lights:
            if light.area > max_area:
                max_area = light.area
                biggest_object = light

        return biggest_object

    def check_us(self, lights):
        """
        Method returns selected American light
        :param lights: list of all light boxes
        :return: selected box
        """
        # groups of lights - us style
        groups = []
        for light in lights:
            if "group" in light.name:
                groups.append(light)
        lights -= groups

        # single lights being inside of another group
        insiders = []
        for light in lights:
            for group in groups:
                if light.intersect_ratio(group) > self.being_inside_ratio:
                    insiders.append(light)
                    break
        lights -= insiders
        lights += groups

        # minimal distance from center of the screen
        min_dist = self.screen_width * self.screen_height
        closest_light = None

        for light in lights:
            # calculate the distance from center of the screen to the closest edge/vertex of the box
            distance = light.get_min_dist(self.screen_width / 2, self.screen_height / 2)
            if distance < min_dist:
                min_dist = distance
                closest_light = light

        return closest_light

    def detect_actual(self, states=None):
        """
        Method returns actual light state based on previous light states
        :param states: list of states
        :return: current light state
        """
        if states is None:
            states = self.prev_states

        if len(states) < 3:
            return states[-1]
        else:
            # yellow - red - red
            # yellow - yellow - red
            # green - yellow - red
            if states[-1] == "red":
                if states[-2] == "red" and states[-3] == "yellow":
                    return "red"
                elif states[-2] == "yellow" and (states[-3] == "yellow" or states[-3] == "green"):
                    return "red"
            # green - green - yellow
            # red - red - yellow
            # green - yellow - yellow
            # red - yellow - yellow
            if states[-1] == "yellow":
                if (states[-2] == "red" and states[-3] == "red") or (states[-2] == "green" and states[-3] == "green"):
                    return "yellow"
                elif states[-2] == "yellow" and (states[-3] == "red" or states[-3] == "green"):
                    return "yellow"
            # yellow - green - green
            # yellow - yellow - green
            # red - yellow - green
            if states[-1] == "green":
                if (states[-2] == "green" or states[-2] == "yellow") and states[-3] == "yellow":
                    return "green"
                if states[-2] == "yellow" and states[-3] == "red":
                    return "green"

            last = {"green": 0, "yellow": 0, "red": 0}
            for i in range(1, 4):
                last[states[-i]] += 1
            # all 3 possible states in last 3 states
            if max(last.values()) - min(last.values()) == 0:
                if len(states) > 4:
                    # the most common state in last 4 is -4 state
                    return states[-4]
                else:
                    # cannot detect current light
                    return "red"
            else:
                return max(last, key=last.get)

    def light_stop(self, xml_file):
        """
        Method checking if vehicle should stop based on current traffic light conditions
        :param xml_file: file with classified boxes
        :return: True if vehicle must stop or False if not
        """
        self.check_light(xml_file)
        actual = self.detect_actual()
        if actual is "red":
            return True
        else:
            return False

