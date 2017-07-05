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


class ColorSpace(enum.IntEnum):
    """
    Color space ids.

    Defines the meaning of the 4 color values in a color structure.

    - ``rgb``: The first three values are *red*, *green*, and *blue*.
      The are full 16-bit unsigned values as in Apple's ``RGBColor``
      data structure.

    - ``hsb``: The first three values are *hue*, *saturation*, and
      *brightness*.  The are full unsigned 16-bit values as in Apple's
      ``HSVColor`` data structure.

    - ``cmyk``: The four values are *cyan*, *magenta*, *yellow* and
      *black*.  The are full unsigned 16-bit values.  0 = 100% ink.

    - ``lab``: The first three values are *lightness*, *a
      chrominance*, and *b chrominance*.  Lightness is a 16-bit value
      from 0 to 10000.  Chrominance components are each 16-bit values
      from -12800 to 12700.  Gray values are represented by
      chrominance components of 0.

    - ``grayscale``: The first value in the color data is the gray
      value from 0 to 10000.

    Additional values are for "custom color spaces" which are not as
    well documented:

    - ``pantone``: Pantone® matching system.

    - ``focoltone``: Focoltone matching system.

    - ``trumatch``: Trumatch color.

    - ``toyo_88_colorfinder_1050``: Toyo 88 colorfinder 1050.

    - ``hks``: HKS colors.
    """
    rgb = 0
    hsb = 1
    cmyk = 2
    pantone = 3
    focoltone = 4
    trumatch = 5
    toyo_88_colorfinder_1050 = 6
    lab = 7
    grayscale = 8
    hks = 10


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


class ColorChannel(enum.IntEnum):
    """
    Color channel names, with unique values so we can check that they
    apply to the expected color mode.
    """
    bitmap = 0
    gray = 1
    default = 2
    red = 3
    green = 4
    blue = 5
    cyan = 6
    magenta = 7
    yellow = 8
    black = 9
    L = 10
    a = 11
    b = 12
    transparency = -1
    user_layer_mask = -2
    real_user_layer_mask = -3


ColorChannelMapping = {
    ColorChannel.bitmap: (ColorMode.bitmap, ChannelId.bitmap),
    ColorChannel.gray: (ColorMode.grayscale, ChannelId.gray),
    ColorChannel.default: (None, ChannelId.default),
    ColorChannel.red: (ColorMode.rgb, ChannelId.red),
    ColorChannel.green: (ColorMode.rgb, ChannelId.green),
    ColorChannel.blue: (ColorMode.rgb, ChannelId.blue),
    ColorChannel.cyan: (ColorMode.cmyk, ChannelId.cyan),
    ColorChannel.magenta: (ColorMode.cmyk, ChannelId.magenta),
    ColorChannel.yellow: (ColorMode.cmyk, ChannelId.yellow),
    ColorChannel.black: (ColorMode.cmyk, ChannelId.black),
    ColorChannel.L: (ColorMode.lab, ChannelId.L),
    ColorChannel.a: (ColorMode.lab, ChannelId.a),
    ColorChannel.b: (ColorMode.lab, ChannelId.b),
    ColorChannel.transparency: (None, ChannelId.transparency),
    ColorChannel.user_layer_mask: (None, ChannelId.user_layer_mask),
    ColorChannel.real_user_layer_mask: (None, ChannelId.real_user_layer_mask)
}


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


class ImageResourceID(enum.IntEnum):
    """
    Ids for Image Resource blocks.
    """
    mac_print_info = 1001
    mac_page_format_info = 1002
    resolution_info = 1005
    alpha_channel_names = 1006
    caption = 1008
    border_info = 1009
    background_color = 1010
    print_flags = 1011
    grayscale_and_multichannel_halftoning_info = 1012
    color_halftoning_info = 1013
    duotone_halftoning_info = 1014
    grayscale_and_multichannel_transfer_func = 1015
    color_transfer_funcs = 1016
    duotone_transfer_funcs = 1017
    duotone_image_info = 1018
    effective_black_and_white = 1019
    eps_options = 1021
    quick_mask_info = 1022
    layer_state_info = 1024
    layers_group_info = 1026
    iptc_naa = 1028
    image_mode_for_raw = 1029
    jpeg_quality = 1030
    grid_and_guides_info = 1032
    copyright_flag = 1034
    url = 1035
    thumbnail_resource = 1036
    global_angle = 1037
    icc_profile = 1039
    watermark = 1040
    icc_untagged_profile = 1041
    effects_visible = 1042
    spot_halftone = 1043
    document_specific_ids_seed_number = 1044
    unicode_alpha_names = 1045
    indexed_color_table_count = 1046
    transparency_index = 1047
    global_altitude = 1049
    slices = 1050
    workflow_url = 1051
    jump_to_xpep = 1052
    alpha_identifiers = 1053
    url_list = 1054
    version_info = 1057
    exif_data_1 = 1058
    exif_data_2 = 1059
    xmp_metadata = 1060
    caption_digest = 1061
    print_scale = 1062
    pixel_aspect_ratio = 1064
    layer_comps = 1065
    alternate_duotone_colors = 1066
    alternate_spot_colors = 1067
    layer_selection_ids = 1069
    hdr_toning_info = 1070
    print_info = 1071
    layer_groups_enabled = 1072
    color_samplers_resource = 1073
    measurement_scale = 1074
    timeline_info = 1075
    sheet_disclosure = 1076
    display_info = 1077
    onion_skins = 1078
    count_info = 1080
    print_info_cs5 = 1082
    print_style = 1083
    mac_nsprintinfo = 1084
    win_devmode = 1085
    auto_save_file_path = 1086
    auto_save_format = 1087
    path_selection_state = 1088
    name_of_clipping_path = 2999
    origin_path_info = 3000
    image_ready_variables = 7000
    image_ready_data_sets = 7001
    image_ready_default_selected_state = 7002
    image_ready_7_rollover_expanded_state = 7003
    image_ready_rollover_expanded_state = 7004
    image_ready_save_layer_settings = 7005
    image_ready_version = 7006
    lightroom_workflow = 8000
    print_flags_info = 10000


class Units(enum.IntEnum):
    inches = 1
    cm = 2
    points = 3
    picas = 4
    columns = 5


class GuideDirection(enum.IntEnum):
    vertical = 0
    horizontal = 1


class PrintScaleStyle(enum.IntEnum):
    centered = 0
    size_to_fit = 1
    user_defined = 2
