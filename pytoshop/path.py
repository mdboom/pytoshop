# -*- coding: utf-8 -*-


"""
Handle Bézier paths.
"""


from __future__ import unicode_literals, absolute_import


import struct


import six


from . import docs
from . import enums
from . import util


from typing import Any, BinaryIO, Dict, List, Optional, TYPE_CHECKING, Union  # NOQA
if TYPE_CHECKING:
    from . import core  # NOQA


def _to_float(value):  # type: (Union[float, int]) -> float
    if isinstance(value, int):
        value = float(value)

    if not isinstance(value, float):
        raise ValueError("Must be a float")

    return value


def _read_point(x, size):
    # type: (Union[float, int], Union[float, int]) -> float
    return (float(x) / (1 << 24)) * float(size)


def _write_point(x, size):
    # type: (Union[float, int], Union[float, int]) -> float
    return int((x / float(size)) * (1 << 24))


class _PathRecordMeta(type):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}  # type: Dict[int, PathRecord]

    def __new__(cls, name, parents, dct):
        new_cls = type.__new__(cls, name, parents, dct)

        if '_type' in dct:
            if dct['_type'] in cls.mapping:
                raise ValueError("Duplicate type '{}'".format(dct['_type']))
            cls.mapping[dct['_type']] = new_cls

        return new_cls


@six.add_metaclass(_PathRecordMeta)
class PathRecord(object):
    _type = -1

    @property
    def type(self):
        # type: (...) -> int
        return self._type

    def length(self, header):
        # type: (core.Header) -> int
        return 26

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        # type: (BinaryIO, core.Header) -> PathRecord
        type = util.read_value(fd, 'H')

        new_cls = _PathRecordMeta.mapping[type]

        return new_cls.read_data(fd, header)

    @classmethod
    def read_data(cls, fd, header):
        # type: (BinaryIO, core.Header) -> PathRecord
        raise NotImplementedError()

    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'H', self.type)
        self.write_data(fd, header)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        raise NotImplementedError()


class PathFillRuleRecord(PathRecord):
    _type = enums.PathRecordType.path_fill_rule_record

    @classmethod
    def read_data(cls, fd, header):
        # type: (BinaryIO, core.Header) -> PathRecord
        padding = fd.read(24)
        if padding != b'\0' * 24:  # pragma: no cover
            raise ValueError(
                "Invalid padding in path fill rule record")
        return cls()

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        fd.write(b'\0' * 24)


class InitialFillRuleRecord(PathRecord):
    def __init__(self,
                 all_pixels=False  # type: bool
                 ):  # type: (...) -> None
        self.all_pixels = all_pixels

    _type = enums.PathRecordType.initial_fill_rule_record

    @property
    def all_pixels(self):  # type: (...) -> bool
        'Fill starts with all pixels'
        return self._all_pixels

    @all_pixels.setter
    def all_pixels(self, value):  # type: (Any) -> None
        self._all_pixels = bool(value)

    @classmethod
    def read_data(cls, fd, header):
        # type: (BinaryIO, core.Header) -> PathRecord
        all_pixels = bool(util.read_value(fd, 'H'))
        padding = fd.read(22)
        if padding != b'\0' * 22:  # pragma: no cover
            raise ValueError(
                "Invalid padding in initial fill rule record")

        util.log("all_pixels: {}", all_pixels)

        return cls(all_pixels=all_pixels)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'H', self.all_pixels)
        fd.write(b'\0' * 22)


class _LengthRecord(PathRecord):
    def __init__(self,
                 num_knots=0  # type: int
                 ):  # type: (...) -> None
        self.num_knots = num_knots

    @property
    def num_knots(self):  # type: (...) -> int
        "Number of Bezier knots"
        return self._num_knots

    @num_knots.setter
    def num_knots(self, value):  # type: (int) -> None
        if (not isinstance(value, int) or
                value < 0 or value > 65535):
            raise ValueError("num_knots must be a 16-bit integer")
        self._num_knots = value

    @classmethod
    def read_data(cls, fd, header):
        # type: (BinaryIO, core.Header) -> PathRecord
        num_knots = util.read_value(fd, 'H')
        fd.read(22)
        util.log('num_knots: {}', num_knots)
        return cls(num_knots=num_knots)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        util.write_value(fd, 'H', self.num_knots)
        fd.write(b'\0' * 22)


class ClosedSubpathLengthRecord(_LengthRecord):
    _type = enums.PathRecordType.closed_subpath_length


class OpenSubpathLengthRecord(_LengthRecord):
    _type = enums.PathRecordType.open_subpath_length


class _PointRecord(PathRecord):
    def __init__(self,
                 y0=0.0,   # type: float
                 x0=0.0,   # type: float
                 y1=None,  # type: Optional[float]
                 x1=None,  # type: Optional[float]
                 y2=None,  # type: Optional[float]
                 x2=None   # type: Optional[float]
                 ):  # type: (...) -> None
        self.y0 = y0
        self.x0 = x0
        self.y1 = y1
        self.x1 = x1
        self.y2 = y2
        self.x2 = x2

    @property
    def y0(self):  # type: (...) -> Union[int, float]
        'y of control point preceding the knot, in pixels'
        return self._y0

    @y0.setter
    def y0(self, value):  # type: (Union[int, float]) -> None
        self._y0 = _to_float(value)

    @property
    def x0(self):  # type: (...) -> Union[int, float]
        'x of control point preceding the knot, in pixels'
        return self._x0

    @x0.setter
    def x0(self, value):  # type: (Union[int, float]) -> None
        self._x0 = _to_float(value)

    @property
    def y1(self):  # type: (...) -> Optional[Union[int, float]]
        'y of anchor point of the knot'
        return self._y1

    @y1.setter
    def y1(self, value):  # type: (Optional[Union[int, float]]) -> None
        if value is None:
            self._y1 = value
        else:
            self._y1 = _to_float(value)

    @property
    def x1(self):  # type: (...) -> Optional[Union[int, float]]
        'x of anchor point of the knot'
        return self._x1

    @x1.setter
    def x1(self, value):  # type: (Optional[Union[int, float]]) -> None
        if value is None:
            self._x1 = value
        else:
            self._x1 = _to_float(value)

    @property
    def y2(self):  # type: (...) -> Optional[Union[int, float]]
        'y of control point for the segment leaving the knot, in pixels'
        return self._y2

    @y2.setter
    def y2(self, value):  # type: (Optional[Union[int, float]]) -> None
        if value is None:
            self._y2 = value
        else:
            self._y2 = _to_float(value)

    @property
    def x2(self):  # type: (...) -> Optional[Union[int, float]]
        'x of control point for the segment leaving the knot, in pixels'
        return self._x2

    @x2.setter
    def x2(self, value):  # type: (Optional[Union[int, float]]) -> None
        if value is None:
            self._x2 = value
        else:
            self._x2 = _to_float(value)

    @classmethod
    def read_data(cls, fd, header):
        # type: (BinaryIO, core.Header) -> PathRecord
        data = fd.read(24)
        y0, x0, y1, x1, y2, x2 = struct.unpack(str('>iiiiii'), data)

        y0 = _read_point(y0, header.height)
        x0 = _read_point(x0, header.width)
        y1 = _read_point(y1, header.height)
        x1 = _read_point(x1, header.width)
        y2 = _read_point(y2, header.height)
        x2 = _read_point(x2, header.width)

        util.log(
            '({}, {}) ({}, {}), ({}, {})',
            y0, x0, y1, x1, y2, x2)

        return cls(y0=y0, x0=x0, y1=y1, x1=x1, y2=y2, x2=x2)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        y0 = _write_point(self.y0, header.height)
        x0 = _write_point(self.x0, header.width)

        if self.y1 is None:
            y1 = y0
        else:
            y1 = _write_point(self.y1, header.height)
        if self.x1 is None:
            x1 = x0
        else:
            x1 = _write_point(self.x1, header.width)

        if self.y2 is None:
            y2 = y0
        else:
            y2 = _write_point(self.y2, header.height)
        if self.x2 is None:
            x2 = x0
        else:
            x2 = _write_point(self.x2, header.width)

        util.write_value(fd, 'iiiiii', y0, x0, y1, x1, y2, x2)


class ClosedSubpathBezierKnotLinked(_PointRecord):
    _type = enums.PathRecordType.closed_subpath_bezier_knot_linked


class ClosedSubpathBezierKnotUnlinked(_PointRecord):
    _type = enums.PathRecordType.closed_subpath_bezier_knot_unlinked


class OpenSubpathBezierKnotLinked(_PointRecord):
    _type = enums.PathRecordType.open_subpath_bezier_knot_linked


class OpenSubpathBezierKnotUnlinked(_PointRecord):
    _type = enums.PathRecordType.open_subpath_bezier_knot_unlinked


class ClipboardRecord(PathRecord):
    def __init__(self,
                 top=0.0,      # type: float
                 left=0.0,     # type: float
                 bottom=0.0,   # type: float
                 right=0.0,    # type: float
                 resolution=0  # type: int
                 ):  # type: (...) -> None
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right
        self.resolution = resolution

    _type = enums.PathRecordType.clipboard_record

    @property
    def top(self):  # type: (...) -> Union[int, float]
        "top, in pixels"
        return self._top

    @top.setter
    def top(self, value):  # type: (Union[int, float]) -> None
        self._top = _to_float(value)

    @property
    def left(self):  # type: (...) -> Union[int, float]
        "left, in pixels"
        return self._left

    @left.setter
    def left(self, value):  # type: (Union[int, float]) -> None
        self._left = _to_float(value)

    @property
    def bottom(self):  # type: (...) -> Union[int, float]
        "bottom, in pixels"
        return self._bottom

    @bottom.setter
    def bottom(self, value):  # type: (Union[int, float]) -> None
        self._bottom = _to_float(value)

    @property
    def right(self):  # type: (...) -> Union[int, float]
        "right, in pixels"
        return self._right

    @right.setter
    def right(self, value):  # type: (Union[int, float]) -> None
        self._right = _to_float(value)

    @property
    def resolution(self):  # type: (...) -> int
        "resolution"
        return self._resolution

    @resolution.setter
    def resolution(self, value):  # type: (int) -> None
        if not isinstance(value, int):
            raise TypeError("resolution must be an int")
        self._resolution = value

    @classmethod
    def read_data(cls, fd, header):
        # type: (BinaryIO, core.Header) -> PathRecord
        data = fd.read(24)
        top, left, bottom, right, resolution, _ = struct.unpack(
            str('>iiiiii'), data)

        top = _read_point(top, header.height)
        left = _read_point(left, header.width)
        bottom = _read_point(bottom, header.height)
        right = _read_point(right, header.width)

        util.log(
            'position: ({}, {}, {}, {}), resolution: {}',
            top, left, bottom, right, resolution)

        return cls(top=top, left=left, bottom=bottom, right=right,
                   resolution=resolution)

    def write_data(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        top = _write_point(self.top, header.height)
        left = _write_point(self.left, header.width)
        bottom = _write_point(self.bottom, header.height)
        right = _write_point(self.right, header.width)

        util.write_value(
            fd, 'iiiiii', top, left, bottom, right, self.resolution, 0
        )


class PathResource(object):
    def __init__(self,
                 path_records=[]  # List[PathRecord]
                 ):
        self.path_records = path_records

    @property
    def path_records(self):  # type: (...) -> List[PathRecord]
        "List of `PathRecord` instances."
        return self._path_records

    @path_records.setter
    def path_records(self, value):  # type: (List[PathRecord]) -> None
        util.assert_is_list_of(value, PathRecord)
        self._path_records = value

    def length(self, header):  # type: (core.Header) -> int
        return sum(x.length(header) for x in self.path_records)
    length.__doc__ = docs.length  # type: ignore

    @classmethod
    def read(cls, fd, length, header):
        # type: (BinaryIO, int, core.Header) -> PathResource
        end = fd.tell() + length

        path_records = []
        while fd.tell() + 26 <= end:
            path_records.append(
                PathRecord.read(fd, header))

        if (path_records[0].type !=
                enums.PathRecordType.path_fill_rule_record):
            raise ValueError(
                'Path resource must start with path_fill_rule_record')

        fd.seek(end - fd.tell(), 1)

        return cls(path_records=path_records)

    @classmethod
    def from_rect(cls,
                  top,             # type: Union[int, float]
                  left,            # type: Union[int, float]
                  bottom,          # type: Union[int, float]
                  right,           # type: Union[int, float]
                  all_pixels=True  # type: bool
                  ):               # type: (...) -> PathResource
        return cls(path_records=[
            PathFillRuleRecord(),
            InitialFillRuleRecord(all_pixels=False),
            OpenSubpathLengthRecord(num_knots=5),
            OpenSubpathBezierKnotLinked(y0=top, x0=left),
            OpenSubpathBezierKnotLinked(y0=top, x0=right),
            OpenSubpathBezierKnotLinked(y0=bottom, x0=right),
            OpenSubpathBezierKnotLinked(y0=bottom, x0=left),
            OpenSubpathBezierKnotLinked(y0=top, x0=left),
        ]
        )

    def write(self, fd, header):
        # type: (BinaryIO, core.Header) -> None
        for path_record in self.path_records:
            path_record.write(fd, header)
