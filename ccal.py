#!/usr/bin/env python
"""ccal.py 0.1

Python implementation to process ccal style ~/.cal.dat files"""

## TODO
# Return multiple objects per WD if it would apply to multiple days.
# Implement @actions properly
# @action ls -- list (with comments)
# @action add -- new entry (with comment)
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
import argparse

class fmt(dict):
    """Easy ANSI formatting

    fmt = fmt()
    print fmt.f('yellow'), "Yellow foreground"
    print fmt.b('red'), "Yellow fg, red background"
    print fmt.bfs('blue', 'magenta', 'bright')
    print "Blue bg, magenta fg, bright style"
    print fmt.s('normal')
    print "Blue bg, magenta fg, normal style"
    print fmt.r, "Everything reset to normal"

    Any permutation of f/b/s is a valid method to call.
    """
    def __init__(self):
        self['f'] = { 'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
                      'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37,
                      'reset': 39 }
        self['b'] = { 'black': 40, 'red': 41, 'green': 42, 'yellow': 43,
                      'blue': 44, 'magenta': 45, 'cyan': 46, 'white': 47,
                      'reset': 49 }
        self['s'] = { 'normal': 22, 'bright': 1, 'dim': 2, 'reset': 0,
                      'transparent': 8 }
        self.colours = self.has_colours(sys.stdout)

    def has_colours(self, stream):
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

    def __getattr__(self, k):
        return lambda *v: self.g(k, *v)

    def g(self, k, *v):
        a = re.compile(r'^[fbs]+$')
        if not a.match(k):
            raise UnboundLocalError("Method can only a permutation of f/b/s " \
                                    + "('%s' given)" % k)
        if len(k) != len(v):
            raise TypeError("Method name length and arguments passed need to" \
                            + "be of the same length (%s and %s given)" % \
                            (len(k), len(v)))
        t = []
        for c in k:
            if c in self: t.append(self[c][v[k.index(c)]])
        return self.p(*t)

    @property
    def r(self):
        return self.fbs('reset', 'reset', 'reset')

    def c(self, txt):
        exp = re.compile(r'\x1B\[[0-9;]*[mK]')
        return exp.sub('', txt)

    def p(self, *cs):
        if self.colours:
            return '\033[%sm' % ";".join([str(c) for c in cs])
        return ''

fmt = fmt() # We really don't need more than one instance here.

class Entry(object):
    def __new__(cls, line='', bdt=dt.datetime.now()):
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
        if len(line) < 14 or line.count(' ') < 4:
            return line
        yyyy, mm, dd, wd = line.split(' ')[:4]
        self.desc = line[14:]
        try:
            yyyy = int(yyyy)
            mm = int(mm)
            dd = int(dd)
            w = int(wd[0])
            d = int(wd[1])
        except:
            return line
        if yyyy < 1970: yyyy = bdt.year
        if mm < 1: mm = bdt.month
        if dd < 1 and (yyyy != bdt.year or mm != bdt.month):
            return None
        fw = dt.datetime(yyyy, mm, 1)
        if w == 1 and d != 0 and fw.isoweekday() > d:
            n = dt.timedelta(days=7)
            w = fw + n
        else:
            w = dt.datetime(yyyy, mm, (w*7)-6 if w > 0 else bdt.day)
        if d != 0:
            d = dt.timedelta(days=d-w.isoweekday())
            dd = (w + d).day
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
        #    comment = '%s\n%s\n' % ('\n'.join(comment[:len(comment)-1]), clr(comment[-1], 'underline'))
        #    return comment
        return self.comm
    
    def __cmp__(self, other):
        return cmp(self.dt, other.dt)

class Entries(list):
    def __init__(self, fp='.cal.dat', bdt=(dt.datetime.now(),)):
        list.__init__(self)
        self.caldat = open(fp)
        self.bdt = bdt
        self.years = [d.year for d in bdt]
        self.months = [d.month for d in bdt]
        self.days = [d.day for d in bdt]

        lentry = None
        for line in self.caldat:
            entry = Entry(line, bdt[0])
            if isinstance(entry, Entry) and entry['year'] in self.years and \
               entry['month'] in self.months:
                list.append(self, entry) # self.append sorts, quicker that way
            if isinstance(entry, str) and lentry in self:
                self[self.index(lentry)].comm = entry
                continue
            lentry = entry

        self.sort()

    def __repr__(self):
        out = ""
        for entry in self:
            if entry['day'] in self.days:
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
    def __init__(self, bdt=dt.datetime.now(), hl=(dt.date.today(),)):
        self.year = bdt.year
        self.month = bdt.month
        self.hl = hl

    def __repr__(self):
        ls = [" %s" % l for l in cal.month(self.year, self.month).split('\n')][:-1]
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
                      fmt.fs('white', 'normal'))).join(ls[i].rsplit("%s " % su, 1))
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

def main(bdt):
    entries = Entries(bdt=bdt)
    cal = Calendar(bdt[0], bdt if len(bdt) > 0 else (dt.datetime.now(),))
    nextTo(cal, repr(entries))

if __name__ == '__main__':
    # XXX
    parser = argparse.ArgumentParser()
    parser.add_argument("action", nargs="?", default="ls")
    parser.add_argument("date", nargs='*')
    parser.add_argument("-c", action="store_true")
    args = parser.parse_args()
    if args.action not in ("ls", "add", "ia"):
        args.date.insert(0, args.action)
        args.action = "ls"
    if not args.date:
        args.date = (dt.datetime.now(),)
    elif len(args.date) == 1:
        args.date = (dt.datetime(int(args.date[-1]), dt.datetime.now().month, 1),)
    elif len(args.date) == 2:
        try:
            args.date = (dt.datetime.strptime("1 %s" % " ".join(args.date), "%d %B %Y"),)
        except:
            args.date = (dt.datetime.strptime("1 %s" % " ".join(args.date), "%d %b %Y"),)
    elif len(args.date) > 2:
        month = args.date[-2:][0]
        year = args.date[-2:][1]
        args.date = tuple([dt.datetime.strptime("%s %s %s" % (day, month, year), "%d %B %Y") for day in args.date[:-2]])
    if args.c:
        fmt.colours = args.c
    print ''
    main(bdt=args.date)
    print ''

