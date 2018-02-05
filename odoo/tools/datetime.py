# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


"""
Convenience classes to manipulate dates and datetimes
"""

import datetime as datetimelib
import json
import dateutil.relativedelta
import dateutil.rrule

from dateutil.relativedelta import relativedelta as du_relativedelta
from dateutil.rrule import rrule as du_rrule, rruleset as du_rruleset
from dateutil.parser import parser as du_parser, parserinfo as du_parserinfo
from odoo.tools import pycompat
from odoo.tools.func import monkey_patch

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT)

DATE_LENGTH = len(datetimelib.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
DATETIME_LENGTH = len(datetimelib.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))

# Python's strftime supports only the format directives
# that are available on the platform's libc, so in order to
# be cross-platform we map to the directives required by
# the C standard (1989 version), always available on platforms
# with a C standard implementation.
DATETIME_FORMATS_MAP = {
    '%C': '', # century
    '%D': '%m/%d/%Y', # modified %y->%Y
    '%e': '%d',
    '%E': '', # special modifier
    '%F': '%Y-%m-%d',
    '%g': '%Y', # modified %y->%Y
    '%G': '%Y',
    '%h': '%b',
    '%k': '%H',
    '%l': '%I',
    '%n': '\n',
    '%O': '', # special modifier
    '%P': '%p',
    '%R': '%H:%M',
    '%r': '%I:%M:%S %p',
    '%s': '', #num of seconds since epoch
    '%T': '%H:%M:%S',
    '%t': ' ', # tab
    '%u': ' %w',
    '%V': '%W',
    '%y': '%Y', # Even if %y works, it's ambiguous, so we should use %Y
    '%+': '%Y-%m-%d %H:%M:%S',

    # %Z is a special case that causes 2 problems at least:
    #  - the timezone names we use (in res_user.context_tz) come
    #    from pytz, but not all these names are recognized by
    #    strptime(), so we cannot convert in both directions
    #    when such a timezone is selected and %Z is in the format
    #  - %Z is replaced by an empty string in strftime() when
    #    there is not tzinfo in a datetime value (e.g when the user
    #    did not pick a context_tz). The resulting string does not
    #    parse back if the format requires %Z.
    # As a consequence, we strip it completely from format strings.
    # The user can always have a look at the context_tz in
    # preferences to check the timezone.
    '%z': '',
    '%Z': '',
}

POSIX_TO_LDML = {
    'a': 'E',
    'A': 'EEEE',
    'b': 'MMM',
    'B': 'MMMM',
    #'c': '',
    'd': 'dd',
    'H': 'HH',
    'I': 'hh',
    'j': 'DDD',
    'm': 'MM',
    'M': 'mm',
    'p': 'a',
    'S': 'ss',
    'U': 'w',
    'w': 'e',
    'W': 'w',
    'y': 'yy',
    'Y': 'yyyy',
    # see comments above, and babel's format_datetime assumes an UTC timezone
    # for naive datetime objects
    #'z': 'Z',
    #'Z': 'z',
}

# Set conveniences names for imports
rrulestr = dateutil.rrule.rrulestr
time = datetimelib.time
tzinfo = datetimelib.tzinfo
timezone = datetimelib.timezone
MO = dateutil.relativedelta.MO
TU = dateutil.relativedelta.TU
WE = dateutil.relativedelta.WE
TH = dateutil.relativedelta.TH
FR = dateutil.relativedelta.FR
SA = dateutil.relativedelta.SA
SU = dateutil.relativedelta.SU
weekdays = dateutil.relativedelta.weekdays
YEARLY = dateutil.rrule.YEARLY
MONTHLY = dateutil.rrule.MONTHLY
WEEKLY = dateutil.rrule.WEEKLY
DAILY = dateutil.rrule.DAILY
HOURLY = dateutil.rrule.HOURLY
MINUTELY = dateutil.rrule.MINUTELY
SECONDLY = dateutil.rrule.SECONDLY

def posix_to_ldml(fmt, locale):
    """ Converts a posix/strftime pattern into an LDML date format pattern.

    :param fmt: non-extended C89/C90 strftime pattern
    :param locale: babel locale used for locale-specific conversions (e.g. %x and %X)
    :return: unicode
    """
    buf = []
    pc = False
    quoted = []

    for c in fmt:
        # LDML date format patterns uses letters, so letters must be quoted
        if not pc and c.isalpha():
            quoted.append(c if c != "'" else "''")
            continue
        if quoted:
            buf.append("'")
            buf.append(''.join(quoted))
            buf.append("'")
            quoted = []

        if pc:
            if c == '%': # escaped percent
                buf.append('%')
            elif c == 'x': # date format, short seems to match
                buf.append(locale.date_formats['short'].pattern)
            elif c == 'X': # time format, seems to include seconds. short does not
                buf.append(locale.time_formats['medium'].pattern)
            else: # look up format char in static mapping
                buf.append(POSIX_TO_LDML[c])
            pc = False
        elif c == '%':
            pc = True
        else:
            buf.append(c)

    # flush anything remaining in quoted buffer
    if quoted:
        buf.append("'")
        buf.append(''.join(quoted))
        buf.append("'")

    return ''.join(buf)

class date(datetimelib.date):
    """
    datetime.date compatibility object with better string representation.
    """
    def __new__(cls, year, month, day, dateformat=None):
        if not dateformat:
            dateformat = DEFAULT_SERVER_DATE_FORMAT

        self = datetimelib.date.__new__(cls, year, month, day)
        self._dateformat = dateformat
        return self

    def __cmp__(self, other): # for python2 only
        if self.__lt__(self, other):
            return -1
        if self.__gt__(self, other):
            return 1
        return 0

    def __contains__(self, item):
        return item in str(self)

    def __eq__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return super(date, self).__eq__(other)

    def __ge__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return super(date, self).__ge__(other)

    def __getitem__(self, key):
        return str(self)[key]

    def __gt__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return super(date, self).__gt__(other)

    def __iter__(self):
        for char in str(self):
            yield char

    def __le__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return super(date, self).__le__(other)

    def __len__(self):
        return len(str(self))

    def __lt__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return super(date, self).__lt__(other)

    def __ne__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return super(date, self).__ne__(other)

    def __repr__(self):
        return '<date %s>' % str(self)

    def __req__(self, other):
        return self.__eq__(other)

    def __rge__(self, other):
        return self.__lt__(other)

    def __rgt__(self, other):
        return self.__le__(other)

    def __rle__(self, other):
        return self.__gt__(other)

    def __rlt__(self, other):
        return self.__ge__(other)

    def __rne__(self, other):
        return self.__ne__(other)

    def __str__(self):
        return self.strftime(self.dateformat)

    def __sub__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return super(date, self).__sub__(other)

    def decode(self, encoding='utf-8', errors='strict'):
        """ Launch decode on string form """
        return str(self).decode(encoding, errors)

    def encode(self, encoding="utf-8", errors="strict"):
        """ Launch encode on string form """
        return str(self).encode(encoding, errors)

    def endswith(self, suffix, start=None, end=None):
        """ String form ends with suffix ? """
        return str(self).endswith(suffix, start, end)

    def find(self, sub, start=None, end=None):
        """ Find in string form """
        return str(self).find(sub, start, end)

    @classmethod
    def from_date(cls, new):
        """ Create an instance from date """
        dateformat = getattr(new, 'dateformat', DEFAULT_SERVER_DATETIME_FORMAT)
        return cls(new.year, new.month, new.day, dateformat=dateformat)

    @classmethod
    def from_string(cls, string, dateformat=None):
        """
        Create an instance from string.

        @param string: String to convert
        @param dateformat: Optional date format. Try most used format if not present.
        """
        if dateformat:
            try:
                return cls.from_date(datetimelib.datetime.strptime(string, dateformat).date())
            except ValueError:
                raise

        if isinstance(string, datetimelib.date):
            return cls.from_date(string)

        formats = [ # From most used to less.
            DEFAULT_SERVER_DATE_FORMAT,
            DEFAULT_SERVER_DATETIME_FORMAT,
        ]

        for dtformat in formats:
            try:
                return cls.from_date(datetimelib.datetime.strptime(string, dtformat).date())
            except ValueError:
                pass

        return cls.from_date(du_parser().parse(string, yearfirst=True))

    def get_dateformat(self):
        """ Get date format """
        return getattr(self, '_dateformat', DEFAULT_SERVER_DATE_FORMAT)

    def get_end_month(self):
        """ Just before the end of month """
        return self.get_start_month() + relativedelta(months=1, days=-1)

    def get_end_year(self):
        """ Just before the end of year """
        return self.get_start_year() + relativedelta(years=1, days=-1)

    def get_start_month(self):
        """ Start of month """
        return self.__class__(self.year, self.month, 1, dateformat=self.dateformat)

    def get_start_year(self):
        """ Start of year """
        return self.__class__(self.year, self.month, self.day, dateformat=self.dateformat)

    def index(self, sub, start=None, end=None):
        """ Get the index of substring in string representation """
        return str(self).index(sub, start, end)

    def replace(self, *args, **kwargs):
        """ Replace old substring by a new one or create a new instance of date. """
        date_params = {'year', 'month', 'day'}
        if date_params & set(kwargs.keys()) or (args and isinstance(args[0], int)):
            result = super(date, self).replace(*args, **kwargs)
            result = self.from_date(result)
            result.dateformat = self.dateformat
            return result

        datestr = str(self)
        datestr = datestr.replace(*args, **kwargs)
        result = self.from_string(datestr)
        result.dateformat = self.dateformat
        return result

    def rfind(self, sub, start=None, end=None):
        """ Find substring from right """
        return str(self).rfind(sub, start, end)

    def rindex(self, sub, start=None, end=None):
        """ Get the index of substring, starting from right """
        return str(self).rindex(sub, start, end)

    def rsplit(self, sep=None, maxsplit=-1):
        """ Right split of string representation """
        return str(self).rsplit(sep, maxsplit)

    def rstrip(self, chars=None):
        """ Right strip of string representation """
        return str(self).rstrip(chars)

    def set_date(self, new):
        """ Set date from date object """
        self._year = new.year
        self._month = new.month
        self._day = new.day

    def set_dateformat(self, value):
        """ Set date format """
        self._dateformat = value

    def set_string(self, string):
        """ Set date from string """
        self.set_date(self.from_string(string))

    def split(self, sep=None, maxsplit=-1):
        """ Split string representation """
        return str(self).split(sep, maxsplit)

    def splitlines(self, keepends):
        """ Split lines of string representation """
        return str(self).splitlines(keepends)

    def startswith(self, prefix, start=None, end=None):
        """  Does string representation start with substring ? """
        return str(self).startswith(prefix, start, end)

    def strip(self, chars):
        """ Strip string representation """
        return str(self).strip(chars)

    def to_pydate(self):
        """
        Convert to python date.
        """
        return datetimelib.date(self.year, self.month, self.day)

    def to_string(self, dateformat=None):
        """
        Convert to string

        @param dateformat: Optional dateformat, otherwise, use default dateformat.
        """
        return self.strftime(dateformat or self.dateformat)

    dateformat = property(get_dateformat, set_dateformat)

class datetime(datetimelib.datetime, date):
    """
    datetime.datetime compatibility object with better string representation.
    """
    def __eq__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return datetimelib.datetime.__eq__(self, other)

    def __ge__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return datetimelib.datetime.__ge__(self, other)

    def __new__(cls, year, month, day, hour=0, minute=0, second=0,
                microsecond=0, tzinfo=None, dateformat=None):
        if not dateformat:
            dateformat = DEFAULT_SERVER_DATETIME_FORMAT

        self = datetimelib.datetime.__new__(
            cls, year, month, day,
            hour, minute, second, microsecond, tzinfo)
        self._dateformat = dateformat
        return self

    def __gt__(self, other):
        if isinstance(other, pycompat.string_types):
            if len(other) == 10:
                other = date.from_string(other)
            else:
                other = self.from_string(other)

        if isinstance(other, datetimelib.date) and not isinstance(other, datetimelib.datetime):
            other = self.from_date(other).replace(hour=23, minute=59, second=59, microsecond=999999)

        return datetimelib.datetime.__gt__(self, other)

    def __le__(self, other):
        if isinstance(other, pycompat.string_types):
            if len(other) == 10:
                other = date.from_string(other)
            else:
                other = self.from_string(other)

        if isinstance(other, datetimelib.date) and not isinstance(other, datetimelib.datetime):
            other = self.from_date(other).replace(hour=23, minute=59, second=59, microsecond=999999)

        return datetimelib.datetime.__le__(self, other)

    def __len__(self):
        return len(str(self))

    def __lt__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return datetimelib.datetime.__lt__(self, other)

    def __ne__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return datetimelib.datetime.__ne__(self, other)

    def __repr__(self):
        return '<datetime %s>' % str(self)

    def __sub__(self, other):
        if isinstance(other, pycompat.string_types):
            other = self.from_string(other)
        return datetimelib.datetime.__sub__(self, other)

    def date(self):
        result = date.from_date(super(datetime, self).date())
        result.dateformat = self.dateformat
        return result

    def get_dateformat(self):
        """ Get date format """
        return getattr(self, '_dateformat', DEFAULT_SERVER_DATETIME_FORMAT)

    @classmethod
    def from_datetime(cls, new):
        """ Create an instance from a datetime object. """
        dateformat = getattr(new, 'dateformat', DEFAULT_SERVER_DATETIME_FORMAT)

        return cls(
            new.year, new.month, new.day,
            hour=new.hour, minute=new.minute, second=new.second, microsecond=new.microsecond,
            tzinfo=new.tzinfo, dateformat=dateformat)

    @classmethod
    def from_string(cls, string, dateformat=None):
        """
        Create an instance from string.

        @param string: String to convert
        @param dateformat: Optional date format. Try most used format if not present.
        """
        if dateformat:
            try:
                return cls.from_datetime(datetimelib.datetime.strptime(string, dateformat))
            except ValueError:
                raise

        if isinstance(string, datetimelib.datetime):
            return cls.from_datetime(string)

        if isinstance(string, datetimelib.date):
            return cls.from_date(string)

        formats = [ # From most used to less
            DEFAULT_SERVER_DATETIME_FORMAT,
            DEFAULT_SERVER_DATE_FORMAT,
        ]

        for dtformat in formats:
            try:
                return cls.from_datetime(datetimelib.datetime.strptime(string, dtformat))
            except ValueError:
                pass

        return du_parser().parse(string, default=cls.now(), yearfirst=True)

    def get_end_month(self):
        """ Just before the end of month """
        return self.get_start_month() + relativedelta(months=1, seconds=-1)

    def get_end_year(self):
        """ Just before the end of year """
        return self.get_start_year() + relativedelta(years=1, seconds=-1)

    def replace(self, *args, **kwargs):
        """ Replace old substring by a new one or create a new instance of date. """
        date_params = {
            'year', 'month', 'day',
            'hour', 'minute', 'second', 'microsecond',
            'tzinfo'}
        if date_params & set(kwargs.keys()) or (args and isinstance(args[0], int)):
            result = datetimelib.datetime.replace(self, *args, **kwargs)
            result = self.from_datetime(result)
            result.dateformat = self.dateformat
            return result

        datestr = str(self)
        datestr = datestr.replace(*args, **kwargs)
        result = self.from_string(datestr)
        result.dateformat = self.dateformat
        return result

    def set_dateformat(self, value):
        """ Set date format """
        self._dateformat = value

    def set_datetime(self, new):
        """ Set date from datetime object """
        self._year = new.year
        self._month = new.month
        self._day = new.day
        self._hour = new.hour
        self._second = new.second
        self._microsecond = new.microsecond
        self._tzinfo = new.tzinfo

    def set_string(self, string):
        """ Set date from string """
        self.set_datetime(self.from_string(string))

    def to_atom(self):
        """ Get string to send to iCal services """
        return self.strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_filename(self):
        """ Get string to compose file names """
        return self.strftime("%Y-%m-%d_%H-%M-%S")

    def to_gcal(self):
        """ Get string to send to Google Calendars """
        return self.strftime("%Y-%m-%dT%H:%M:%S.%fz")

    def to_ical(self):
        """ Get string to send to iCal services """
        return self.strftime("%Y%m%dT%H:%M:%SZ")

    def to_isoformat(self):
        """ Get string according to iso format without microseconds. """
        return self.replace(microsecond=0).isoformat()

    def to_pofile(self):
        """ Get string to generate .po headers """
        return self.strftime("%Y-%m-%d %H:%M+0000")

    def to_pydatetime(self):
        """
        Convert to python datetime.
        """
        return datetimelib.datetime(
            self.year, self.month, self.day,
            self.hour, self.minute, self.second, self.microsecond,
            tzinfo=self.tzinfo)

    def to_virtualid(self):
        """ Get virtualid string """
        return self.strftime("%Y%m%d%H%M%S")

    @classmethod
    def today(cls):
        """ Get today datetime """
        return cls.from_date(datetimelib.date.today())

    dateformat = property(get_dateformat, set_dateformat)

class timedelta(datetimelib.timedelta):
    pass

class relativedelta(du_relativedelta):
    def __add__(self, other):
        if isinstance(other, relativedelta):
            return super(relativedelta, self).__add__(other)
        elif isinstance(other, pycompat.string_types):
            other = datetime.from_string(other)

        result = super(relativedelta, self).__add__(other)

        if isinstance(other, datetimelib.date) and not isinstance(other, datetimelib.datetime):
            return date.from_date(result)
        return datetime.from_datetime(result)

class rrule(du_rrule):
    def _iter(self):
        gen = super(rrule, self)._iter()
        while True:
            try:
                value = next(gen)
                if isinstance(value, datetimelib.datetime):
                    yield datetime.from_datetime(value)
                elif isinstance(value, datetimelib.date):
                    yield date.from_date(value)
            except StopIteration:
                break

class rruleset(du_rruleset):
    def _iter(self):
        gen = super(rruleset, self)._iter()
        while True:
            try:
                value = next(gen)
                if isinstance(value, datetimelib.datetime):
                    yield datetime.from_datetime(value)
                elif isinstance(value, datetimelib.date):
                    yield date.from_date(value)
            except StopIteration:
                break

class parser(du_parser):
    def parse(self, timestr, default=None, ignoretz=False, tzinfos=None, **kwargs):
        if default is None:
            default = datetime.today()

        return super(parser, self).parse(timestr, default, ignoretz, tzinfos, **kwargs)

DEFAULTPARSER = parser()

def parse(timestr, parserinfo=None, **kwargs):
    """
    Call the dateutil parser, like dateutil.parse.
    Return Odoo datetime object by default.
    """
    if parserinfo:
        return parser(parserinfo).parse(timestr, **kwargs)
    return DEFAULTPARSER.parse(timestr, **kwargs)

class DatetimeContext(object):
    """ Convenience class for a safer eval in XML """
    datetime = datetime
    date = date
    time = time
    relativedelta = relativedelta
    timedelta = timedelta
    parser = parser

    @classmethod
    def from_string(cls, string, dateformat=None):
        """ Get datetime from string """
        return datetime.from_string(string, dateformat)

    @classmethod
    def now(cls, with_microsecond=False):
        """ Get current datetime """
        result = datetime.now()
        if not with_microsecond:
            return result.replace(microsecond=False)
        return result

    @classmethod
    def today(cls):
        """ Get current day """
        return datetime.today()

    @classmethod
    def utcnow(cls, with_microsecond=False):
        """ Get current datetime in UTC """
        result = datetime.utcnow()
        if not with_microsecond:
            return result.replace(microsecond=False)
        return result

date_types = (datetimelib.date, date, datetimelib.datetime, datetime)
datetime_types = (datetimelib.datetime, datetime)

@monkey_patch(json.JSONEncoder)
def default(self, o):
    if isinstance(o, date):
        return str(o)
    return default.super(self, o)
