#!/usr/bin/env python3
"""ccal.py 0.2

Python implementation to process ccal style ~/.cal.dat files"""

# License (MIT)
#
# Copyright (c) 2012 Michael Zeltner <m@niij.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

## TODO
# -------------------------------------------------
# extend notation for date ranges:
# "YYYY MM DD WD +D" - the "+D" means "plus D days",
# starting on YYYY-MM-DD and continuing to YYYY-MM-(DD+D).
# example: "2012 12 27 00 +3 29C3" then expands to this:
# 2012 12 27 00 29C3
# 2012 12 28 00 29C3
# 2012 12 29 00 29C3
# 2012 12 30 00 29C3
#
# "the congress" is taking place on the same dates every year,
# so even the yearly entries should take a "+D" argument:
# -999 12 27 00 +3 Chaos Communication Congress
#
# allow relative dates, some arithmetic:
# 'tomorrow' and 'yesterday',
# (in) [+-] N [days/months/years] (ago)
# (in)      N [days/months/years]
#           N [days/months/years]  ago
# examples:
# in 4d, in 3m, in 2y -- 4d ago, 3m ago, 2y ago
# "in 3mon 1 year 2d"
#
# WARNING! watch for spaces and abbreviated time names!
# allow multiple occurrences of times:
# example: "1y 3m 2d 2y 1m 4d" -> "3y 4m 6d"
# (probably wont be used very often ;)
#
# add "ia" (interactive mode) which automatically updates the screen,
# possibly with some paging.
#
# setup file: ~/.ccalpy.rc ?
# Include legacy .dates format via regexp? ("legacy dates"? huh?)
#
# arguments/actions:
# general: Implement @actions properly
#
# add "add" to add new entries and comments.
# example: ccal add TODO
#
# add "del" to delete entries
# example: TODO
# (maybe add this with auto completion?)
#
# add "search" to search for entries including foo within date ranges
# example: search party vienna 2012-12-21 2013-01-05
#
# input+output:
# add output for ical (ICS files)
# allow data from stdin
# allow multiple data files
# allow short names and numbers for month
#
# color:
# add colors for each weekday
# add color  for time ranges
# add color  for places (@placename)
# add color  for URLs
#
# show color when COLORTERM is set
# options:
# add option to suppress repetitive events
# add option to suppress calendar month view
# add support for UTF-8
# -------------------------------------------------

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

def ordinal(value):
    try:
        value = int(value)
    except ValueError:
        return value

    if value % 100//10 != 1:
        if value % 10 == 1:
            ordval = "%d%s" % (value, "st")
        elif value % 10 == 2:
            ordval = "%d%s" % (value, "nd")
        elif value % 10 == 3:
            ordval = "%d%s" % (value, "rd")
        else:
            ordval = "%d%s" % (value, "th")
    else:
        ordval = "%d%s" % (value, "th")

    return ordval

class Entry(object):
    """Calender Entry

    In some cases when we instantiate an Entry, it turns out it's not an
    entry but a comment of a previous one. In this case, we're just going
    to return the line it was instanciated with instead.

    If an entry is dynamically generated and would apply to more than one
    day, it might be expanded, in which case a list with multiple entries
    is returned.

    >>> Entry("2012 12 11 00 Foo")
    Tue 11: Foo
    >>> Entry("-999 -9 11 05 Bar")
    [Sun 16: Bar, Fri 21: Bar, Wed 26: Bar, Mon 31: Bar]
    >>> Entry("Hung out with Sven Guckes in Berlin")
    'Hung out with Sven Guckes in Berlin'
    """
    def __new__(cls, line='', bdt=now(), edt=None, exp=True):
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
        if "{" in self.desc and "}" in self.desc:
            try:
                oc = int((" %s " % self.desc).split(" {")[1].split("} ")[0])
                self.desc = self.desc.replace("{%s}" % oc, ordinal(yyyy - oc))
            except:
                pass
        self.desc = self.desc.replace("\{", "{").replace("\}", "}")
        # week/day
        try:
            fw = dt.datetime(yyyy, mm, 1)
        except:
            return line
        # every week
        if exp and w == 0 and d != 0:
            entries = []
            for i in range(5):
                n = dt.timedelta(days=d-fw.isoweekday()+7*i)
                self.dt = fw + n
                if self.dt.month == bdt.month:
                    entries.append(Entry(self.desc, bdt, self.dt))
            return entries
        # last week of the month
        if exp and w == 9 and d != 0:
            fw = dt.datetime(yyyy, mm, cal.monthrange(yyyy, mm)[1])
            n = dt.timedelta(days=d-fw.isoweekday())
            dd = (fw + n).day
        # every day, but show only once
        if exp and w == 0 and d == 0:
            dd = now().day
        # specific day/week
        elif exp and dd < 1 and w != -1 and d != 0 and fw.isoweekday() > d:
            n = dt.timedelta(days=7*w)
            w = fw + n
        elif exp and dd < 1 and w != 0:
            w = dt.datetime(yyyy, mm, (w*7)-6 if w > 0 else bdt.day)
        if exp and w != 9 and dd < 1 and d != 0:
            d = dt.timedelta(days=d-w.isoweekday())
            dd = (w + d).day
        # periodic
        if exp and w == -1 and isinstance(d, int) and dd > 0 and d > 1:
            entries = []
            self.dt = dt.datetime(yyyy, mm, dd)
            while self.dt.month <= bdt.month and self.dt.year <= bdt.year:
                self.dt = self.dt + dt.timedelta(days=d)
                if self.dt.month == bdt.month and self.dt.year == bdt.year:
                    entries.append(Entry(self.desc, bdt, self.dt))
            return entries
        # daily, but show only once
        if exp and w == -1 and isinstance(d, int) and dd > 0 and d == 1 and \
           bdt > dt.datetime(yyyy, mm, dd):
            dd = bdt.day
        # XXX dirty stuff, should probably stop earlier?
        try:
            self.dt = dt.datetime(yyyy, mm, dd)
            return self
        except:
            return

    def __getitem__(self, item):
        return self.dt.__getattribute__(item)

    def __repr__(self):
        return nextTo(self.dt.strftime("%a %e:"), self.desc)

    def full(self):
        """Show entry with comment"""
        both = "%s\n %s" % \
               (self.desc,
                ' # '.join(self.comm.split("\n")).strip().replace(" #","\n #"))
        return nextTo(self.dt.strftime("%a %e:"), both)
    
    def __lt__(self, other):
        return self.dt < other.dt

class Entries(list):
    def __init__(self, fp=os.path.expanduser('~/.cal.dat'), bdt=(now(),),
                 exp=True, comm=False):
        list.__init__(self)
        self.caldat = open(fp)
        self.bdt = bdt
        self.years = [d.year for d in bdt]
        self.months = [d.month for d in bdt]
        self.days = []
        if bdt[0].day != 1 or (now().day == 1 or '1' in sys.argv or '01' in \
           sys.argv):
            self.days = [d.day for d in bdt]
        self.comm = comm

        # It's necessary to first create a whole list of entries because
        # otherwise comments would end up on wrong entries ...
        entries = []
        for line in self.caldat:
            entry = Entry(line, bdt[0], exp=exp)
            if isinstance(entry, Entry):
                entries.append(entry) # self.append sorts, quicker that way
            elif isinstance(entry, list):
                entries.extend(entry)
                continue
            elif self.comm and isinstance(entry, str) and len(entries) > 0:
                entries[-1].comm += ('\n' + entry)
                continue

        # ... hence we filter out entries later
        for entry in entries:
            if entry['year'] in self.years and entry['month'] in self.months:
                list.append(self, entry)

        self.sort()

    def __repr__(self):
        out = ""
        for entry in self:
            e = ''
            if self.comm and entry.comm:
                e = entry.full().replace('\n', '%s\n' % fmt.r)
            if entry['day'] in self.days and entry['month'] in self.months:
                if e:
                    e = e.replace('        #',
                                  '        %s#' % fmt.bf('red', 'reset'))
                out += "%s*%s%s%s%s" % (fmt.s('transparent'), fmt.r,
                                        fmt.bf('red', 'reset'), e or entry,
                                        fmt.r)
            else:
                if e:
                    e = e.replace('        #',
                                  '        %s#' % fmt.bf('white', 'black'))
                out += " %s%s%s" % (fmt.bf('white', 'black'), e or entry,
                                    fmt.r)
            out += '\n'
        return out.strip('\n')

    def append(self, obj):
        list.append(self, obj)
        self.sort()

    def days(self):
        return [entry.day for entry in self]

class Calendar(object):
    def __init__(self, bdt=now(), hl=(dt.date.today(),)):
        self.year = bdt.year
        self.month = bdt.month
        self.hl = ()
        if hl[0].day != 1 or (now().day == 1 or '1' in sys.argv or '01' in \
           sys.argv):
            self.hl = hl

    def __repr__(self):
        ls = [" %s" % l for l in cal.month(self.year, self.month).split('\n')]
        ls = ls[:-1]
        for i in range(len(ls)):
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
            if len(self.hl) > 0 and self.hl[0].year == self.year and \
               self.hl[0].month == self.month:
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
    merge = ""
    padding = len(fmt.c(one[0]))
    [one.append(' '*padding) for i in range(len(two)-len(one))]
    [two.append('') for i in range(len(one)-len(two))]
    if len(one) == len(two):
        for i in range(len(one)):
             merge += "%s %s\n" % (one[i], two[i])
    return merge.strip()

def ls(bdt, pve=7, cmt=False, fp=os.path.expanduser('~/.cal.dat'), comm=False,
       exp=True):
    entries = Entries(bdt=bdt, fp=fp, comm=comm, exp=exp)
    pvs = ""
    if pve > 0:
        pvd = bdt[0] + dt.timedelta(days=-(bdt[0].day-2)+30)
        pvs = repr(Entries(bdt=(pvd,), fp=fp, exp=False))
    if pvs:
        pvs = "%s%s" % (pvd.strftime("\n %B --\n"),
                        '\n'.join(pvs.split('\n')[:pve]))
    else:
        pvs = ""
    cal = Calendar(bdt[0], bdt if len(bdt) > 1 else (bdt[0],))
    return nextTo(cal, repr(entries)+pvs)

if __name__ == '__main__':
    # If nothing is passed, assume ls --preview
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser('parent', add_help=False)
        parser.add_argument('--version', action='version',
                            version='%(prog)s 0.1')
        parser.add_argument('-c', action='store_true',
                            help='force colored output')
        parser.add_argument('-d', '--data-file', metavar="filename", nargs="?",
                            default="~/.cal.dat",
                            help="file to load appointments from " + \
                                 "(default: ~/.cal.dat)")
        parser = argparse.ArgumentParser(parents=[parser])
        sub_p = parser.add_subparsers(help='actions')
        p_ls = sub_p.add_parser('ls', help='list calendar entries')
        p_ls.add_argument("-p", "--preview", type=int, nargs="?", default=7,
                          metavar="N",
                          help="preview next month's non-periodic entries " + \
                                "(default, if set: 7)")
        p_ls.add_argument("-C", "--comments",
                          help='include comments in listing',
                          action='store_true')
        p_ls.add_argument("-n", "--noperiodic",
                          help='do not expand periodic dates',
                          action='store_false')
        p_ls.add_argument("date", nargs='*')
        p_add = sub_p.add_parser('add', help='add calendar entry')
        p_add.add_argument("date")
        p_add.add_argument("description")
        p_add.add_argument("comment", nargs="?")
        #p_ia = sub_p.add_parser('ia', help='Interactive mode')
        args = parser.parse_args()
        if not args.date:
            args.date = (now(),)
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
            args.date = tuple([dt.datetime.strptime("%s %s %s" % \
                                                    (day, month, year),
                                                    "%d %B %Y") \
                               for day in args.date[:-2]])
        if args.c:
            fmt.colors = args.c
        dates = args.date
        if '-p' in sys.argv or '--preview' in sys.argv:
            pve = args.preview or 7
        else:
            pve = 0
        data = args.data_file
        comm = args.comments
        exp = args.noperiodic
    else:
        dates = (now(),)
        pve = 7
        data = "~/.cal.dat"
        comm = False
        exp = True
    out = ls(bdt=dates, pve=pve, fp=os.path.expanduser(data), comm=comm,
             exp=exp)
    print('')
    print(out)
    print('')

