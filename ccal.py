#!/usr/bin/env python
"""pyccal

Python implementation to process ccal style ~/.cal.dat files"""

import datetime as dt
import copy
import calendar
import re
import curses
import sys

class fmt(dict):
    def __init__(self):
        self['_f'] = { 'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
                       'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37,
                       'reset': 39 }
        self['_b'] = { 'black': 40, 'red': 41, 'green': 42, 'yellow': 43,
                       'blue': 44, 'magenta': 45, 'cyan': 46, 'white': 47,
                       'reset': 49 }
        self['_s'] = { 'normal': 22, 'bright': 1, 'dim': 2, 'reset': 0 }
        self['f'] = self['_f']['reset']
        self['b'] = self['_b']['reset']
        self['s'] = self['_s']['normal']
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
            # guess false in case of error
            return False

    def __getattr__(self, k):
        return lambda *v: self.g(k, *v)

    def g(self, k, *v):
        if len(k) != len(v):
            raise ValueError("Needs to be of the same length")
        t = self.copy()
        for c in k:
            if c in t: t[c] = self["_%s" % c][v[k.index(c)]]
        return self.p(t['f'], t['b'], t['s'])

    @property
    def r(self):
        return self.p(self['f'], self['b'], self['s'])

    def c(self, txt):
        exp = re.compile(r'\x1B\[[0-9;]*[mK]')
        return exp.sub('', txt)

    def p(self, f, b, s):
        if self.colours:
            return '\033[%s;%s;%sm' % (f, b, s)
        return ''

fmt = fmt()

class Entry(object):
    def __new__(cls, line=''):
        now = dt.datetime.now()
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
        if yyyy < 1970: yyyy = now.year
        if mm < 1: mm = now.month
        if dd < 1 and (yyyy != now.year or mm != now.month):
            return None
        #w = dt.datetime(yyyy, mm, 1).isocalendar() 
        #cw = now.isocalendar()[1]-dt.datetime(dt.2, 8, 31).isocalendar()[1])+1
        weekday = dt.datetime.now().isoweekday()
        if w and d is not None:
            dd = dt.datetime.now().day
            self.desc += ' (Nope)'
        if w == 0 and d > 0:
            d = dt.timedelta(days=-(weekday-d))
            dd = (dt.datetime.now() + d).day
        if not dd > 0:
            return None
        #if not(w == 0 and d == 0):
        #    dd = dt.datetime.now().day
        self.dt = dt.datetime(yyyy, mm, dd)
        return self

    def __getitem__(self, item):
        return self.dt.__getattribute__(item)

    def regular(self):
        return self.dt.strftime("%%a %%e %s" % self.desc)

    def __repr__(self):
        return self.regular()

    def full(self):
        #comment = self.comm.split('\n')
        #if len(comment) > 0:
        #    comment = '%s\n%s\n' % ('\n'.join(comment[:len(comment)-1]), clr(comment[-1], 'underline'))
        #    return comment
        return self.comm
    
    def __cmp__(self, other):
        return cmp(self.dt, other.dt)

class Entries(list):
    def __init__(self, fp='.cal.dat', bdt=dt.datetime.now()):
        list.__init__(self)
        self.caldat = open(fp)
        self.bdt = bdt

        lentry = None
        for line in self.caldat:
            entry = Entry(line)
            if isinstance(entry, Entry) and entry['year'] == bdt.year and \
               entry['month'] == bdt.month:
                self.append(entry)
            if isinstance(entry, str) and lentry in self:
                self[self.index(lentry)].comm = entry
                continue
            lentry = entry

        self.sort()

    def __repr__(self):
        return ('%s\n' % fmt.r).join([fmt.bf('white', 'black') + repr(i) if not self.bdt.day == i['day'] else fmt.bf('red', 'reset') + repr(i) for i in self]) + fmt.r

    def append(self, obj):
        list.append(self, obj)
        self.sort()

def coloredCalendar(bdt=dt.datetime.now(),day=dt.date.today()):
    lines = []
    counter = 0
    for line in calendar.month(bdt.year, bdt.month).split('\n'):
        line = " %s" % line
        if len(line) == 1:
            continue
        while len(line) < 22:
            line += ' '
        if counter == 0:
            line = "%s%s" % (fmt.fb('black', 'green'), line)
            counter += 1
        elif counter == 1:
            line = "%s%s" % (fmt.fb('blue', 'cyan'), line)
            counter += 1
        else:
            dstr = ' %s ' % day.strftime("%e")
            line = "%s%s" % (fmt.bf('blue', 'white'), line.replace(dstr, "%s<%s>%s" % (fmt.bf('red', 'reset'), dstr[1:-1], fmt.bf('blue', 'white'))))
        lines.append(line)
    return "%s%s" % (('%s\n' % fmt.r).join(lines), fmt.r)

def nextTo(one, two):
    one = one.split('\n')
    two = two.split('\n')
    padding = len(fmt.c(one[0]))
    [one.append(' '*padding) for i in xrange(len(two)-len(one))]
    [two.append('') for i in xrange(len(one)-len(two))]
    if len(one) == len(two):
        for i in xrange(len(one)):
            print one[i], two[i]

def main():
    bdt = dt.datetime.now()
    entries = Entries(bdt=bdt)
    nextTo(coloredCalendar(bdt=bdt), repr(entries))
    #print coloredCalendar(bdt=bdt)

if __name__ == '__main__':
    print ''
    main()
    print ''
