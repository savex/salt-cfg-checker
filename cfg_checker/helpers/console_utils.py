from time import sleep
import sys


class Progress(object):
    def __init__(self, max_index, bar_size=21):
        self.total = max_index
        # bar size in symbols
        self.bar_size = bar_size

    def write_progress(self, index, note=''):
        #calc index and percent values
        _percent = (100 * index) / self.total
        _index = (self.bar_size * index) / self.total
        # clear the line
        sys.stdout.write('\r')
        # print new progress
        _format = "[{:"+str(self.bar_size-1)+"}] {}/{} ({}%) {}"
        sys.stdout.write(_format.format(
            '='*_index,
            index,
            self.total,
            _percent,
            note
        ))
        sys.stdout.flush()
    
    @staticmethod
    def newline():
        sys.stdout.write('\n')
