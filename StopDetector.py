import math

default_classes_list = [
   {'id': 1, 'name': 'red'},
   {'id': 2, 'name': 'green'},
   {'id': 3, 'name': 'yellow'},
   {'id': 4, 'name': 'red_group'},
   {'id': 5, 'name': 'green_group'},
   {'id': 6, 'name': 'limit_30'},
   {'id': 7, 'name': 'limit_60'},
   {'id': 8, 'name': 'limit_90'},
   {'id': 9, 'name': 'yellow_group'}
]


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

    def check_light(self, boxes, classes, classes_list):
        """
        Detect light state based on current frame
        :param boxes: list of lists - representing list of boxes (y1, x1, y2, x2)
        :param classes: list of classes
        :param classes_list: dict describing each class, see default_classes_dict
        :return: None
        """
        objects = []

        us_lights = False

        for i in range(len(boxes)):
            ymin = boxes[i][0] * self.screen_height
            xmin = boxes[i][1] * self.screen_width
            ymax = boxes[i][2] * self.screen_height
            xmax = boxes[i][3] * self.screen_width
            name = classes_list[classes[i] - 1]["name"]

            if "limit" in name:
                continue

            objects.append(BndBox(name, xmin, xmax, ymin, ymax))

            if "group" in name:
                us_lights = True

        if len(objects) > self.max_eu_lights:
            us_lights = True

        if us_lights:
            selected = self.check_us(objects)
        else:
            selected = self.check_eu(objects)

        if selected is not None:
            selected_name = selected.name.split("_")[0]
            self.prev_states.append(selected_name)
        else:
            self.prev_states.append(None)

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
        lights = [x for x in lights if x not in to_remove]

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
        lights = [x for x in lights if x not in groups]

        # single lights being inside of another group
        insiders = []
        for light in lights:
            for group in groups:
                if light.intersect_ratio(group) > self.being_inside_ratio:
                    insiders.append(light)
                    break
        lights = [x for x in lights if x not in insiders]
        lights = lights + groups

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

        if len(self.prev_states) > 5:
            self.prev_states = self.prev_states[-5:]

        if len(states) < 3:
            return states[-1]
        else:
            # None None None
            if states[-1] is None and states[-2] is None and states[-3] is None:
                self.prev_states = []
                return None
            # yellow - red - red
            # yellow - yellow - red
            # green - yellow - red
            if states[-1] == "red":
                if states[-2] == "red" and states[-3] == "yellow":
                    return "red"
                elif states[-2] == "yellow" and (states[-3] == "yellow" or states[-3] == "green"):
                    return "red"
            # green - green - yellow
            # green - yellow - yellow
            if states[-1] == "yellow":
                if states[-2] == "green" and states[-3] == "green":
                    return "yellow"
                elif states[-2] == "yellow" and states[-3] == "green":
                    return "yellow"
            # red - red - green
            if states[-1] == "green":
                if states[-2] == "red" and states[-3] == "red":
                    return "green"

            last = {"green": 0, "yellow": 0, "red": 0}
            for i in range(1, 4):
                if states[-i] is not None:
                    last[states[-i]] += 1
            # all 3 possible states in last 3 states
            if max(last.values()) - min(last.values()) == 0:
                if len(states) > 3:
                    # the most common state in last 4 is -4 state
                    return states[-4]
                else:
                    # cannot detect current light
                    return "green"
            else:
                return max(last, key=last.get)

    def light_stop(self, boxes, classes, classes_list=None):
        """
        Method checking if vehicle should stop based on current traffic light conditions
        :param boxes: list of lists - representing list of boxes (y1, x1, y2, x2)
        :param classes: list of classes
        :param classes_list: list describing each class, see default_classes_list
        :return: True if vehicle must stop or False if not
        """
        if classes_list is None:
            classes_list = default_classes_list
        self.check_light(boxes, classes, classes_list)
        actual = self.detect_actual()
        print(actual)
        if actual == "red":
            return True
        else:
            return False

