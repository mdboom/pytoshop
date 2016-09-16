# -*- coding: utf-8 -*-


import struct


import traitlets as t


from . import docs
from . import enums
from . import util


def _read_point(x, size):
    return (float(x) / (1 << 24)) * float(size)


def _write_point(x, size):
    return int((x / float(size)) * (1 << 24))


class _PathRecordMeta(type(t.HasTraits)):
    """
    A metaclass that builds a mapping of subclasses.
    """
    mapping = {}

    def __new__(cls, name, parents, dct):
        new_cls = super().__new__(cls, name, parents, dct)

        if 'type' in dct:
            if dct['type'] in cls.mapping:
                raise ValueError("Duplicate type '{}'".format(dct['type']))
            cls.mapping[dct['type']] = new_cls

        return new_cls


class PathRecord(t.HasTraits, metaclass=_PathRecordMeta):
    def length(self, header):
        return 26

    def total_length(self, header):
        return self.length(header)

    @classmethod
    @util.trace_read
    def read(cls, fd, header):
        type = util.read_value(fd, 'H')

        new_cls = _PathRecordMeta.mapping[type]

        return new_cls.read_data(fd, header)

    def write(self, fd, header):
        util.write_value(fd, 'H', self.type)
        self.write_data(fd, header)


class PathFillRuleRecord(PathRecord):
    type = enums.PathRecordType.path_fill_rule_record

    @classmethod
    @util.trace_read
    def read_data(cls, fd, header):
        padding = fd.read(24)
        if padding != b'\0' * 24:
            raise ValueError(
                "Invalid padding in path fill rule record")
        return cls()

    def write_data(self, fd, header):
        fd.write(b'\0' * 24)


class InitialFillRuleRecord(PathRecord):
    type = enums.PathRecordType.initial_fill_rule_record
    all_pixels = t.Bool(
        help='Fill starts with all pixels'
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, header):
        all_pixels = bool(util.read_value(fd, 'H'))
        padding = fd.read(22)
        if padding != b'\0' * 22:
            raise ValueError(
                "Invalid padding in initial fill rule record")

        util.log("all_pixels: {}", all_pixels)

        return cls(all_pixels=all_pixels)

    def write_data(self, fd, header):
        util.write_value(fd, 'H', self.all_pixels)
        fd.write(b'\0' * 22)


class _LengthRecord(PathRecord):
    num_knots = t.Int(
        help="Number of Bezier knots"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, header):
        num_knots = util.read_value(fd, 'H')
        fd.read(22)
        util.log('num_knots: {}', num_knots)
        return cls(num_knots=num_knots)

    def write_data(self, fd, header):
        util.write_value(fd, 'H', self.num_knots)
        fd.write(b'\0' * 22)


class ClosedSubpathLengthRecord(_LengthRecord):
    type = enums.PathRecordType.closed_subpath_length


class OpenSubpathLengthRecord(_LengthRecord):
    type = enums.PathRecordType.open_subpath_length


class _PointRecord(PathRecord):
    y0 = t.Float(
        help='y of control point preceding the knot, in pixels'
    )
    x0 = t.Float(
        help='x of control point preceding the knot, in pixels'
    )
    y1 = t.Float(
        None,
        allow_none=True,
        help='y of anchor point of the knot'
    )
    x1 = t.Float(
        None,
        allow_none=True,
        help='x of anchor point of the knot'
    )
    y2 = t.Float(
        None,
        allow_none=True,
        help='y of control point for the segment leaving the knot, in pixels'
    )
    x2 = t.Float(
        None,
        allow_none=True,
        help='x of control point for the segment leaving the knot, in pixels'
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, header):
        data = fd.read(24)
        y0, x0, y1, x1, y2, x2 = struct.unpack('>iiiiii', data)

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

        fd.write(struct.pack('>iiiiii', y0, x0, y1, x1, y2, x2))


class ClosedSubpathBezierKnotLinked(_PointRecord):
    type = enums.PathRecordType.closed_subpath_bezier_knot_linked


class ClosedSubpathBezierKnotUnlinked(_PointRecord):
    type = enums.PathRecordType.closed_subpath_bezier_knot_unlinked


class OpenSubpathBezierKnotLinked(_PointRecord):
    type = enums.PathRecordType.open_subpath_bezier_knot_linked


class OpenSubpathBezierKnotUnlinked(_PointRecord):
    type = enums.PathRecordType.open_subpath_bezier_knot_unlinked


class ClipboardRecord(PathRecord):
    type = enums.PathRecordType.clipboard_record

    top = t.Float(
        help="top, in pixels"
    )
    left = t.Float(
        help="left, in pixels"
    )
    bottom = t.Float(
        help="bottom, in pixels"
    )
    right = t.Float(
        help="right, in pixels"
    )
    resolution = t.Int(
        help="resolution"
    )

    @classmethod
    @util.trace_read
    def read_data(cls, fd, header):
        data = fd.read(24)
        top, left, bottom, right, resolution, _ = struct.unpack(
            '>iiiiii', data)

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
        top = _write_point(self.top, header.height)
        left = _write_point(self.left, header.width)
        bottom = _write_point(self.bottom, header.height)
        right = _write_point(self.right, header.width)

        fd.write(
            struct.pack('>iiiiii',
                        top, left, bottom, right, self.resolution, 0))


class PathResource(t.HasTraits):
    path_records = t.List(
        t.Instance(PathRecord),
        help="List of `PathRecord` instances."
    )

    def length(self, header):
        return sum(x.length(header) for x in self.path_records)
    length.__doc__ = docs.length

    def total_length(self, header):
        return self.length(header)
    total_length.__doc__ = docs.total_length

    @classmethod
    @util.trace_read
    def read(cls, fd, length, header):
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
    def from_rect(cls, top, left, bottom, right, all_pixels=True):
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
        for path_record in self.path_records:
            path_record.write(fd, header)
