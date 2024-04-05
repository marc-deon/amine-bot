import datetime

class SerializableDatetime(datetime.datetime):
    def ToDict(self):
        return {'year':         self.year,
                'month':        self.month,
                'day':          self.day,
                'hour':         self.hour,
                'second':       self.second,
                'microsecond':  self.microsecond}

def now(tzinfo=None):
    return SerializableDatetime.now(tzinfo)