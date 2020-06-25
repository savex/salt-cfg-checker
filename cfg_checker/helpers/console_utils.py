import sys


class Progress(object):
    _strsize = 0
    _note_size = 0

    def __init__(self, max_index, bar_size=21):
        self.total = max_index
        # bar size in symbols
        self.bar_size = bar_size

    def write_progress(self, index, note=''):
        # calc index and percent values
        _suffix = ''
        new_size = len(note)
        if self._note_size > new_size:
            _suffix = ' '*(self._note_size - new_size)
        _percent = (100 * index) // self.total
        _index = (self.bar_size * index) // self.total
        # clear the line
        sys.stdout.write('\r')
        # print new progress
        _format = "[{:"+str(self.bar_size-1)+"}] {}/{} ({}%) {}"
        _progress_string = _format.format(
            '='*_index,
            index,
            self.total,
            _percent,
            note + _suffix
        )
        sys.stdout.write(_progress_string)
        # Save new note size and whole string size
        self._strsize = len(_progress_string)
        self._note_size = new_size
        sys.stdout.flush()

    def clearline(self):
        sys.stdout.write('\r')
        sys.stdout.write(' '*self._strsize)
        sys.stdout.write('\r')
        sys.stdout.flush()

    def end(self):
        self._note_size = 0
        self._strsize = 0
        sys.stdout.write('\n')
