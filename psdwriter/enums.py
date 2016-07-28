# -*- coding: utf-8 -*-


import enum


class Version(enum.IntEnum):
    version_1 = 1
    version_2 = 2


class ColorDepth(enum.IntEnum):
    depth1 = 1
    depth8 = 8
    depth16 = 16
    depth32 = 32


class ColorMode(enum.IntEnum):
    bitmap = 0
    grayscale = 1
    indexed = 2
    rgb = 3
    cmyk = 4
    multichannel = 7
    duotone = 8
    lab = 9


class BlendModeKey(bytes, enum.Enum):
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
    raw = 0
    rle = 1
    zip = 2
    zip_prediction = 3


class LayerMaskKind(enum.IntEnum):
    color_selected = 0
    color_protected = 1
    use_value_stored_per_layer = 128
