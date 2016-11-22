# -*- coding: utf-8 -*-


"""
Enumerated values used throughout the library.
"""


from __future__ import unicode_literals, absolute_import


import enum


class Version(enum.IntEnum):
    """
    The PSD file version.

    Version 1 is the classic "PSD" file.

    Version 2 is the large document format "PSB" file which supports
    documents up to 300,000 pixels in any dimension.
    """
    version_1 = 1
    version_2 = 2
    psd = 1
    psb = 2


class ColorDepth(enum.IntEnum):
    """
    Color depth (bits-per-pixel-per-channel).

    Supported values are 1, 8, 16, and 32.
    """
    depth1 = 1
    depth8 = 8
    depth16 = 16
    depth32 = 32


class ColorMode(enum.IntEnum):
    """
    Color mode.
    """
    bitmap = 0
    grayscale = 1
    indexed = 2
    rgb = 3
    cmyk = 4
    multichannel = 7
    duotone = 8
    lab = 9


class BlendMode(bytes, enum.Enum):
    """
    Layer blend mode.
    """
    pass_through = b'pass'
    normal = b'norm'
    dissolve = b'diss'
    darken = b'dark'
    multiply = b'mul '
    color_burn = b'idiv'
    linear_burn = b'lbrn'
    darker_color = b'dkCl'
    lighten = b'lite'
    screen = b'scrn'
    color_dodge = b'div '
    linear_dodge = b'lddg'
    lighter_color = b'lgCl'
    overlay = b'over'
    soft_light = b'sLit'
    hard_light = b'hLit'
    vivid_light = b'vLit'
    linear_light = b'lLit'
    pin_light = b'pLit'
    hard_mix = b'hMix'
    difference = b'diff'
    exclusion = b'smud'
    subtract = b'fsub'
    divide = b'fdiv'
    hue = b'hue '
    saturation = b'sat '
    color = b'colr'
    luminosity = b'lum '


class Compression(enum.IntEnum):
    """
    Compression mode.

    - ``raw``: raw image data.

    - ``rle``: Run length encoded (RLE) compressed.  The RLE
      compression is the same compression algorithm used by the
      Macintosh ROM routine PackBits, and the TIFF standard.

    - ``zip``: Zip (zlib) without prediction.

    - ``zip_prediction``: Zip (zlib) with prediction.
    """
    raw = 0
    rle = 1
    zip = 2
    zip_prediction = 3


class LayerMaskKind(enum.IntEnum):
    """
    Layer mask kind.

    According to the spec, only ``use_value_stored_per_layer`` is
    preferred.  The other are retained for backward compatibility
    only.
    """
    color_selected = 0
    color_protected = 1
    use_value_stored_per_layer = 128


class ChannelId(enum.IntEnum):
    """
    Channel id.

    Used to map channel data to image planes in layers.

    The meaning of the positive numbers depends on the `ColorMode` in
    effect.
    """
    bitmap = 0

    gray = 0

    default = 0

    red = 0
    green = 1
    blue = 2

    cyan = 0
    magenta = 1
    yellow = 2
    black = 3

    L = 0
    a = 1
    b = 2

    transparency = -1
    user_layer_mask = -2
    real_user_layer_mask = -3


class SectionDividerSetting(enum.IntEnum):
    """
    Section divider setting.

    Used for the mode of grouped layers.

    - ``any_other``: any other type of layer

    - ``open``: Display an open folder

    - ``closed``: Display a closed folder

    - ``bounding``: Bounding section divider, hidden in GUI.
    """
    any_other = 0
    open = 1
    closed = 2
    bounding = 3


class PathRecordType(enum.IntEnum):
    closed_subpath_length = 0
    closed_subpath_bezier_knot_linked = 1
    closed_subpath_bezier_knot_unlinked = 2
    open_subpath_length = 3
    open_subpath_bezier_knot_linked = 4
    open_subpath_bezier_knot_unlinked = 5
    path_fill_rule_record = 6
    clipboard_record = 7
    initial_fill_rule_record = 8
