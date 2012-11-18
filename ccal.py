#!/usr/bin/env python
"""ccal.py 0.1

Python implementation to process ccal style ~/.cal.dat files"""

## TODO
# Floating dates per YYYY MM DD WD @D
# Implement @actions properly
# @action ls -- list (with comments)
# @action add -- new entry (with comment)
# @action search -- search for entries mentioning $value (3 month range?)
# Relative date parsing '(next) %d/m/y', 'last %d/m/y', 'tomorrow',
#  'yesterday', '4 %d/m/y ago', '(in) 2 %d/m/y'
# @action del -- delete entry (auto complete?)
# @action ia -- interactive mode (automatically update screen)
# ~/.ccalpy.rc ?
# Include legacy .dates format via regexp?

import datetime as dt
import calendar as cal
import re
import sys
import os
import argparse

now = dt.datetime.now

class fmt(dict):
    """Easy ANSI formatting

    >>> fmt = fmt()
    >>> print fmt.f('yellow'), "Yellow foreground"
    >>> print fmt.b('red'), "Yellow fg, red background"
    >>> print fmt.bfs('blue', 'magenta', 'bright')
    >>> print "Blue bg, magenta fg, bright style"
    >>> print fmt.s('normal')
    >>> print "Blue bg, magenta fg, normal style"
    >>> print fmt.r, "Everything reset to normal"
    >>> foo = "%sHello!%s" % (fmt.s('bright'), fmt.r)
    >>> print fmt.c(foo)

    Any permutation of f/b/s as well as c is a valid method to call, r is a
    static attribute to reset colouring.
    """
    def __init__(self):
        """Initialise standard colours, styles and colouring support"""
        self['f'] = { 'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
                      'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37,
                      'reset': 39 }
        self['b'] = { 'black': 40, 'red': 41, 'green': 42, 'yellow': 43,
                      'blue': 44, 'magenta': 45, 'cyan': 46, 'white': 47,
                      'reset': 49 }
        self['s'] = { 'normal': 22, 'bright': 1, 'dim': 2, 'reset': 0,
                      'transparent': 8 }
        self.colors = self.has_colors(sys.stdout)

    def has_colors(self, stream):
        """Determine if our output stream supports ANSI colouring"""
        if not hasattr(stream, "isatty"):
            return False
        if not stream.isatty():
            return False # auto color only on TTYs
        try:
            import curses
            curses.setupterm()
            return curses.tigetnum("colors") > 2
        except:
            return False # guess false in case of error

    def __getattr__(self, attr):
        """Shortcuts for easier use"""
        valid = re.compile(r'^[fbs]+$')
        if not valid.match(attr) and not attr in ('r', 'c') and \
           not attr.startswith('__'):
            raise UnboundLocalError("Method can only be a permutation of " \
                                    + "f/b/s or c, attribute can only be r " \
                                    + "('%s' given)" % attr)
        elif attr == 'r':
            return self.reset
        elif attr == 'c':
            return lambda string: self.clear(string)
        # >>> help(fmt)
        elif attr.startswith('__'):
            return dict.__getattr__(self, attr)
        return lambda *values: self.format(self.lookup(attr, *values))

    def lookup(self, keys, *names):
        """Returns values for color names"""
        if len(keys) != len(names):
            raise TypeError("Method name length and values passed need to" \
                            + "be of the same length (%s and %s given)" % \
                            (len(method), len(names)))
        values = []
        for char in keys:
            if char in self and names[keys.index(char)] in self[char]:
                values.append(self[char][names[keys.index(char)]])
            else:
                raise KeyError("Colour/style '%s' not found in '%s'" % \
                               (names[keys.index(char)] ,char))
        return values

    @property
    def reset(self):
        """ANSI escape sequence clearing all colouring"""
        return self.fbs('reset', 'reset', 'reset')

    def clear(self, string):
        """Clear ANSI coloring from a string"""
        exp = re.compile(r'\x1B\[[0-9;]*[mK]')
        return exp.sub('', string)

    def format(self, colors):
        """Format ANSI escape sequence"""
        if self.colors:
            return '\033[%sm' % ";".join([str(color) for color in colors])
        return ''

fmt = fmt() # We really don't need more than one instance here.

class Entry(object):
    def __new__(cls, line='', bdt=now(), edt=None, exp=True):
        """Calender Entry

        In some cases when we instantiate an Entry, it turns out it's not an
        entry but a comment of a previous one. In this case, we're just going
        to return the line it was instanciated with instead.

        In the future, this might return multiple Entry objects if a dynamic
        date occures more than once a month.
        """
        self = super(Entry, cls).__new__(cls)
        self.comm = ''
        line = line.strip()
        if edt:
            self.dt = edt
            self.desc = line
            return self
        if len(line) < 14 or line.count(' ') < 4:
            return line
        yyyy, mm, dd, wd = line.split(' ')[:4]
        self.desc = line[14:]
        try:
            yyyy = int(yyyy)
            mm = int(mm)
            dd = int(dd)
            # week/day
            if dd < 1:
                w = int(wd[0])
                d = int(wd[1])
            # periodic
            else:
                w = -1
                d = int(wd)
        # Must be a comment then
        except:
            return line
        if not exp and not wd.startswith("00"):
            return None
        if yyyy < 1970: yyyy = bdt.year
        if mm < 1: mm = bdt.month
        # week/day
        fw = dt.datetime(yyyy, mm, 1)
        # every week
        if exp and w == 0 and d != 0:
            entries = []
            for i in range(5):
                n = dt.timedelta(days=d-fw.isoweekday()+7*i)
                dd = (fw + n).day
                self.dt = dt.datetime(yyyy, mm, dd)
                if self.dt.month == bdt.month:
                    entries.append(Entry(self.desc, bdt, self.dt))
            return entries
        # last week
        if exp and w == 9 and d != 0:
            fw = dt.datetime(yyyy, mm, cal.monthrange(yyyy, mm)[1])
            n = dt.timedelta(days=d-fw.isoweekday())
            dd = (fw + n).day
        # specific week
        if dd < 1 and w != -1 and d != 0 and fw.isoweekday() > d:
            n = dt.timedelta(days=7*w)
            w = fw + n
        elif dd < 1:
            w = dt.datetime(yyyy, mm, (w*7)-6 if w > 0 else bdt.day)
        if w != 9 and dd < 1 and d != 0:
            d = dt.timedelta(days=d-w.isoweekday())
            dd = (w + d).day
        # periodic
        if exp and w == -1 and isinstance(d, int) and dd > 0 and d > 0:
            entries = []
            self.dt = dt.datetime(yyyy, mm, dd)
            while self.dt.month <= bdt.month and self.dt.year <= bdt.year:
                self.dt = self.dt + dt.timedelta(days=d)
                if self.dt.month == bdt.month and self.dt.year == bdt.year:
                    entries.append(Entry(self.desc, bdt, self.dt))
            return entries
        self.dt = dt.datetime(yyyy, mm, dd)
        return self

    def __getitem__(self, item):
        return self.dt.__getattribute__(item)

    def __repr__(self):
        return self.dt.strftime("%%a %%e: %s" % self.desc)

    def full(self):
        # XXX
        #comment = self.comm.split('\n')
        #if len(comment) > 0:
        #    comment = '%s\n%s\n' % ('\n'.join(comment[:len(comment)-1]),
        #                            clr(comment[-1], 'underline'))
        #    return comment
        return self.comm
    
    def __cmp__(self, other):
        return cmp(self.dt, other.dt)

class Entries(list):
    def __init__(self, fp=os.path.expanduser('~/.cal.dat'), bdt=(now(),),
                 exp=True):
        list.__init__(self)
        self.caldat = open(fp)
        self.bdt = bdt
        self.years = [d.year for d in bdt]
        self.months = [d.month for d in bdt]
        self.days = [d.day for d in bdt]

        lentry = None
        for line in self.caldat:
            entry = Entry(line, bdt[0], exp=exp)
            if isinstance(entry, Entry) and entry['year'] in self.years and \
               entry['month'] in self.months:
                list.append(self, entry) # self.append sorts, quicker that way
            elif isinstance(entry, list):
                self.extend(entry)
                continue
            elif isinstance(entry, str) and lentry in self:
                self[self.index(lentry)].comm += ('\n' + entry).strip()
                continue
            else:
                continue
            lentry = entry

        self.sort()

    def __repr__(self):
        out = ""
        for entry in self:
            if entry['day'] in self.days and now().month in self.months:
                out += "%s*%s%s%s%s" % (fmt.s('transparent'), fmt.r,
                                        fmt.bf('red', 'reset'), entry, fmt.r)
            else:
                out += " %s%s%s" % (fmt.bf('white', 'black'), entry, fmt.r)
            out += '\n'
        return out.strip('\n')

    def append(self, obj):
        list.append(self, obj)
        self.sort()

class Calendar(object):
    def __init__(self, bdt=now(), hl=(dt.date.today(),)):
        self.year = bdt.year
        self.month = bdt.month
        self.hl = hl

    def __repr__(self):
        ls = [" %s" % l for l in cal.month(self.year, self.month).split('\n')]
        ls = ls[:-1]
        for i in xrange(len(ls)):
            while len(ls[i]) < 22:
                ls[i] += ' '
            if i == 0:
                ls[i] = "%s%s" % (fmt.fb('black', 'green'), ls[i])
            elif i == 1:
                ls[i] = "%s%s" % (fmt.fb('blue', 'cyan'), ls[i])
            if i < 2:
                continue
            ls[i] = "%s%s" % (fmt.bf('blue', 'white'), ls[i])
            su = ls[i][-3:][:2]
            if self.hl[0].year == self.year and self.hl[0].month == self.month:
                for day in self.hl:
                    dstr = ' %s ' % day.strftime("%e")
                    # Replace with 1 more char than necessary so we can
                    # identify continous matches
                    dhls = "<%s> " % dstr[1:-1]
                    ls[i] = ls[i].replace(dstr, dhls)
                ls[i] = ls[i].replace("><", " ")
                ls[i] = ls[i].replace("<", "%s<" % fmt.bf('red', 'reset'))
                ls[i] = ls[i].replace("> ", ">%s" % fmt.bf('blue', 'white'))
                # Highlighted Sundays are bright/bold
                ls[i] = ls[i].replace("%s>" % su, "%s%s%s>" % \
                                      (fmt.bfs('red', 'reset', 'bright'),
                                      su, fmt.s('normal')))
            # Sundays are magenta and bright/bold
            ls[i] = ("%s%s%s " % \
                     (fmt.fs('magenta', 'bright'), su,
                      fmt.fs('white',
                             'normal'))).join(ls[i].rsplit("%s " % su, 1))
        return "%s%s" % (('%s\n' % fmt.r).join(ls), fmt.r)

    def split(self, char):
        return repr(self).split(char)

def nextTo(one, two):
    one = one.split('\n')
    two = two.split('\n')
    padding = len(fmt.c(one[0]))
    [one.append(' '*padding) for i in xrange(len(two)-len(one))]
    [two.append('') for i in xrange(len(one)-len(two))]
    if len(one) == len(two):
        for i in xrange(len(one)):
            print one[i], two[i]

def ls(bdt, pvs=""):
    entries = Entries(bdt=bdt)
    if pvs:
        pvd = bdt[0] + dt.timedelta(days=-(bdt[0].day-2)+30)
        pvs = repr(Entries(bdt=(pvd,), exp=False))
    if pvs:
        pvs = "%s%s" % (pvd.strftime("\n %B --\n"),
                        '\n'.join(pvs.split('\n')[:7]))
    else:
        pvs = ""
    cal = Calendar(bdt[0], bdt if len(bdt) > 1 else (now(),))
    nextTo(cal, repr(entries)+pvs)

if __name__ == '__main__':
    # If nothing is passed, assume ls --preview
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser('parent', add_help=False)
        parser.add_argument('--version', action='version',
                            version='%(prog)s 0.1')
        parser.add_argument('-c', action='store_true',
                            help='force colored output')
        parser.add_argument('-d', '--dates')
        parser = argparse.ArgumentParser(parents=[parser])
        sub_p = parser.add_subparsers(help='actions')
        p_ls = sub_p.add_parser('ls', help='list calendar entries')
        p_ls.add_argument("-p", "--preview",
                          help="preview next month's non-periodic entries",
                          action='store_true')
        p_ls.add_argument("-C", "--comments",
                          help='include comments in listing',
                          action='store_true')
        p_ls.add_argument("date", nargs='*')
        p_add = sub_p.add_parser('add', help='add calendar entry')
        p_add.add_argument("date")
        p_add.add_argument("description")
        p_add.add_argument("comment", nargs="?")
        #p_ia = sub_p.add_parser('ia', help='Interactive mode')
        args = parser.parse_args()
        if not args.date:
            args.date = (now(),)
            args.preview = True
        elif len(args.date) == 1:
            args.date = (dt.datetime(int(args.date[-1]), now().month, 1),)
        elif len(args.date) == 2:
            try:
                args.date = (dt.datetime.strptime("1 %s" % " ".join(args.date),
                             "%d %B %Y"),)
            except:
                args.date = (dt.datetime.strptime("1 %s" % " ".join(args.date),
                             "%d %b %Y"),)
        elif len(args.date) > 2:
            month = args.date[-2:][0]
            year = args.date[-2:][1]
            args.date = tuple([dt.datetime.strptime("%s %s %s" % (day, month,
                                                                  year),
                                                    "%d %B %Y") for day in args.date[:-2]])
        if args.c:
            fmt.colors = args.c
        dates = args.date
        pvs = args.preview
    else:
        dates = (now(),)
        pvs = True
    print ''
    ls(bdt=dates, pvs=pvs)
    print ''

