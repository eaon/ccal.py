#!/usr/bin/env python
"""pyccal

Python implementation to process ccal style ~/.cal.dat files"""

import datetime as dt
import copy
import calendar
import re
import curses
import sys

colors = [ "underline", 4, "bgwhite", 7, "transparent", 8, "strike", 9,
           "thin", 21, "gray", 30, "red", 31, "green", 32, "yellow", 33,
           "blue", 34, "violet", 35, "lightblue", 36, "bgblack", 40,
           "bgdarkred", 41, "bgdarkgreen", 42, "bgyellow", 43, "bgblue", 44,
           "bgviolet", 45, "bgturquoise", 46, "bgdarkgray", 47, "bggray", 100,
           "bgred", 101, "bggreen", 102, "bgyellow", 103, "bgblue", 104,
           "bgviolet", 105, "bglightblue", 106, "bglightgray", 107 ]

def has_colours(stream):
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
has_colours = has_colours(sys.stdout)

def clr(txt, clr):
    if not has_colours:
        return txt
    if isinstance(clr, int):
        return '\033[1;%dm%s\033[1;m' % (clr, txt)
    return '\033[1;%dm%s\033[1;m' % (colors[colors.index(clr)+1], txt)


def clrclr(txt):
    exp = re.compile(r'\x1B\[[0-9;]*[mK]')
    return exp.sub('', txt)

class Entry(object):
    def __new__(cls, line=''):
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
        if yyyy < 0: yyyy = dt.datetime.now().year
        if mm < 0: mm = dt.datetime.now().month
        if w > 0 or d > 0:
            dd = dt.datetime.now().day
            self.desc += ' (Nope)'
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
        return '\n'.join([repr(i) for i in self])

    #def append(self, obj):
    #    list.append(self, obj)
    #    self.sort()

def coloredCalendar(bdt=dt.datetime.now()):
    lines = []
    counter = 0
    for line in calendar.month(2012, 8).split('\n'):
        line = " %s" % line
        if len(line) == 1:
            continue
        while len(line) < 22:
            line += ' '
        if counter == 0:
            lines.append(clr(clr(clr(line, 'thin'), 'bgdarkgreen'), 'gray'))
            counter += 1
            continue
        if counter == 1:
            lines.append(clr(clr(clr(line, 'thin'), 'bgturquoise'), 'blue'))
            counter += 1
            continue
        lines.append(clr(clr(line, 'thin'), 'bgblue'))
    return '\n'.join(lines)

def nextTo(one, two):
    one = one.split('\n')
    two = two.split('\n')
    padding = len(clrclr(one[0]))
    [one.append(' '*padding) for i in xrange(len(two)-len(one))]
    [two.append('') for i in xrange(len(one)-len(two))]
    if len(one) == len(two):
        for i in xrange(len(one)):
            print one[i], two[i]

def main():
    bdt = dt.datetime.now()
    entries = Entries(bdt=bdt)
    nextTo(coloredCalendar(), repr(entries))
    #print clrclr(coloredCalendar())
    
#    for entry in entries:
#        if entry['day'] == bdt.day:
#            print clr(entry, 'red')
#            continue
#        print entry, '(', entry.comm, ')'

if __name__ == '__main__':
    main()

