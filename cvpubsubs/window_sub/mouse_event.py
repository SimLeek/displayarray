class MouseEvent(object):
    def __init__(self, event, x, y, flags, param):
        self.event = event
        self.x = x
        self.y = y
        self.flags = flags
        self.param = param

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "event:{}\nx,y:{},{}\nflags:{}\nparam:{}\n".format(self.event, self.x, self.y, self.flags, self.param)
