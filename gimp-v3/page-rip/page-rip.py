#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Page Rip: cut a band out of an image and join what's left with a torn edge.
#
# Select a band that runs border to border: a rectangle, parallelogram or
# trapezoid, horizontal or vertical. The band is removed and the two pieces
# either side of it are joined, each with a ragged torn edge and a thin
# paper-coloured fringe, separated by a gap showing the background. The
# visible layers are merged and ripped in place (one undo step), or in a new
# image if asked.
#
# Each piece is torn along its own edge of the band, so slanted bands give
# slanted tears. When the band's edges aren't parallel (a trapezoid) the
# pieces can't meet evenly: they are brought together until they touch at the
# band's narrowest point, leaving a wedge-shaped gap elsewhere.

import random
import sys

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl
from gi.repository import GObject
from gi.repository import GLib

PROC_NAME = "python-fu-page-rip"

# Mask bytes at or above 128 count as selected.
SELECTED = bytes(int(value >= 128) for value in range(256))


class PageRip(Gimp.PlugIn):
    def do_set_i18n(self, procname):
        return False

    def do_query_procedures(self):
        return [PROC_NAME]

    def do_create_procedure(self, name):
        Gegl.init(None)

        procedure = Gimp.ImageProcedure.new(self, name,
                                            Gimp.PDBProcType.PLUGIN,
                                            self.run, None)
        procedure.set_image_types("*")
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE |
                                       Gimp.ProcedureSensitivityMask.DRAWABLES |
                                       Gimp.ProcedureSensitivityMask.NO_DRAWABLES)
        procedure.set_menu_label("_Page Rip...")
        procedure.add_menu_path("<Image>/Filters/Decor")
        procedure.set_documentation(
            "Cut the selected band out of the image and join the rest "
            "with a torn-paper edge",
            "The selected band (rectangle, parallelogram or trapezoid running "
            "border to border) is removed. The visible layers are merged and "
            "the remaining pieces joined with ragged torn edges and a gap "
            "showing the background, in this image or a new one.",
            name)
        procedure.set_attribution("Jason Rogers", "Jason Rogers", "2026")

        direction = Gimp.Choice.new()
        direction.add("auto", 0, "Auto", "Guess from the selection's shape")
        direction.add("horizontal", 1, "Horizontal band",
                      "Remove a band running left to right, join top and bottom")
        direction.add("vertical", 2, "Vertical band",
                      "Remove a band running top to bottom, join left and right")
        procedure.add_choice_argument("direction", "_Direction",
                                      "Which way the removed band runs",
                                      direction, "auto",
                                      GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("gap", "_Gap", "Gap between the pieces (pixels)",
                                   0, 500, 16, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("depth", "Tear de_pth",
                                   "How ragged the torn edges are (pixels)",
                                   0, 200, 10, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("fringe", "Paper _fringe",
                                   "Width of the torn paper fringe (pixels)",
                                   0, 50, 4, GObject.ParamFlags.READWRITE)
        procedure.add_color_argument("paper", "Pape_r colour",
                                     "Colour of the torn paper fringe",
                                     True, Gegl.Color.new("white"),
                                     GObject.ParamFlags.READWRITE)
        procedure.add_color_argument("background", "_Background",
                                     "Colour showing through the gap "
                                     "(fully transparent for none)",
                                     True, Gegl.Color.new("white"),
                                     GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument("new-image", "Create a _new image",
                                       "Leave this image alone and put the "
                                       "result in a new one",
                                       False, GObject.ParamFlags.READWRITE)
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, data):
        _, has_selection, x1, y1, x2, y2 = Gimp.Selection.bounds(image)
        if not has_selection:
            return error(procedure, "Select the band to cut out first")

        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init(PROC_NAME)
            dialog = GimpUi.ProcedureDialog.new(procedure, config, "Page Rip")
            dialog.fill(None)
            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL,
                                                   GLib.Error())
            dialog.destroy()

        vertical = is_vertical(config.get_property("direction"),
                               x2 - x1, y2 - y1,
                               image.get_width(), image.get_height())

        # Measure the band before touching anything, so a bad selection
        # fails without leaving a half-ripped image behind.
        try:
            band = measure_band(image, vertical)
        except ValueError as e:
            return error(procedure, str(e))

        Gimp.context_push()
        if config.get_property("new-image"):
            target = image.duplicate()
            target.undo_disable()
            try:
                rip(target, vertical, band, config, drop_hidden=True)
            except Exception:
                target.delete()
                raise
            finally:
                Gimp.context_pop()
            target.undo_enable()
            if run_mode == Gimp.RunMode.INTERACTIVE:
                Gimp.Display.new(target)
        else:
            image.undo_group_start()
            try:
                rip(image, vertical, band, config, drop_hidden=False)
            finally:
                image.undo_group_end()
                Gimp.context_pop()

        Gimp.displays_flush()
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS,
                                           GLib.Error())


def error(procedure, message):
    return procedure.new_return_values(
        Gimp.PDBStatusType.CALLING_ERROR,
        GLib.Error.new_literal(Gimp.PlugIn.error_quark(), message, 0))


def is_vertical(direction, band_width, band_height, width, height):
    """A band spanning the full height is vertical; full width, horizontal.
       Otherwise go by whichever way the selection reaches further."""
    if direction != "auto":
        return direction == "vertical"
    if band_height == height and band_width < width:
        return True
    if band_width == width and band_height < height:
        return False
    return band_height / height > band_width / width


def rip(image, vertical, band, config, drop_hidden):
    """Remove the measured band from the image and join the pieces either
       side of it with a torn gap."""
    gap = config.get_property("gap")
    depth = config.get_property("depth")
    fringe = config.get_property("fringe")
    xs, band_tops, band_bottoms = band

    Gimp.Selection.none(image)
    piece = flatten_visible(image, drop_hidden)

    # Work on vertical bands as horizontal ones by turning the image on
    # its side: rotating 90° clockwise turns column x into row x.
    if vertical:
        image.rotate(Gimp.RotationType.DEGREES90)

    width, height = image.get_width(), image.get_height()

    # Bring the bottom piece up by the band's narrowest thickness, so the
    # pieces touch there (plus the gap) and never overlap anywhere else.
    shift = min(bottom - top for top, bottom in zip(band_tops, band_bottoms))
    new_height = height - shift + gap

    bottom = piece
    top = piece.copy()
    image.insert_layer(top, piece.get_parent(), image.get_item_position(piece))
    top.set_name("Left" if vertical else "Top")
    bottom.set_name("Right" if vertical else "Bottom")
    bottom.set_offsets(0, gap - shift)
    image.resize(width, new_height, 0, 0)

    # Each tear wanders back into its own piece's content, never into the
    # band, so nothing from the removed band shows.
    top_tear = [(x, y - offset) for x, y, offset in
                zip(xs, band_tops, wander(len(xs), depth))]
    bottom_tear = [(x, y - shift + gap + offset) for x, y, offset in
                   zip(xs, band_bottoms, wander(len(xs), depth))]
    paper = config.get_property("paper")
    tear(image, top, top_tear, fringe, paper, keep_above=True)
    tear(image, bottom, bottom_tear, fringe, paper, keep_above=False)

    # The foreground colour ignores alpha, so the background colour's
    # alpha becomes the layer's opacity instead.
    background_color = config.get_property("background")
    background = Gimp.Layer.new(image, "Background", width, new_height,
                                Gimp.ImageType.RGBA_IMAGE,
                                100 * background_color.get_rgba().alpha,
                                Gimp.LayerMode.NORMAL)
    image.insert_layer(background, piece.get_parent(),
                       image.get_item_position(piece) + 1)
    Gimp.Selection.none(image)
    Gimp.context_set_foreground(background_color)
    background.edit_fill(Gimp.FillType.FOREGROUND)

    for layer in (top, bottom):
        layer.resize_to_image_size()

    if vertical:
        image.rotate(Gimp.RotationType.DEGREES270)


def flatten_visible(image, drop_hidden):
    """Merge the visible layers into one layer with alpha, optionally
       dropping the hidden ones."""
    merged = image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
    if drop_hidden:
        for layer in image.get_layers():
            if layer != merged:
                image.remove_layer(layer)
    merged.add_alpha()
    return merged


def sample_columns(width):
    """Irregularly spaced columns from 0 to width: the tear's corners."""
    xs = [0]
    while xs[-1] < width:
        xs.append(min(width, xs[-1] + random.randint(3, 9)))
    return xs


def measure_band(image, vertical):
    """Sample the selected band's edges across the image, as if the image
       were turned so the band runs horizontally (90° clockwise, for a
       vertical band). Returns the sampled columns and, at each, the band's
       first and one-past-last row."""
    width, height = image.get_width(), image.get_height()
    mask = image.get_selection().get_buffer().get(
        Gegl.Rectangle.new(0, 0, width, height), 1.0, "Y u8",
        Gegl.AbyssPolicy.CLAMP)

    if vertical:
        # Turned clockwise, column x reads along original row height-1-x.
        length, depth = height, width
        def line(x):
            row = height - 1 - min(x, height - 1)
            return mask[row * width:(row + 1) * width]
    else:
        length, depth = width, height
        def line(x):
            return mask[min(x, width - 1)::width]

    xs = sample_columns(length)
    tops, bottoms = band_edges([line(x).translate(SELECTED) for x in xs])
    if all(top == 0 for top in tops) or all(bottom == depth for bottom in bottoms):
        raise ValueError("The band must leave something on both sides "
                         "to join; it touches the image edge")
    return xs, tops, bottoms


def band_edges(lines):
    """The first and one-past-last selected entry of each line. Lines the
       selection doesn't reach copy their nearest neighbour, so a band that
       stops short of the border is carried out to it."""
    edges = []
    for line in lines:
        top = line.find(1)
        edges.append(None if top < 0 else (top, line.rfind(1) + 1))

    found = [i for i, edge in enumerate(edges) if edge]
    if not found:
        raise ValueError("Select the band to cut out first")
    edges = [edge or edges[min(found, key=lambda f: abs(f - i))]
             for i, edge in enumerate(edges)]
    return [top for top, _ in edges], [bottom for _, bottom in edges]


def wander(count, depth):
    """A random walk of count steps between 0 and depth."""
    offsets = []
    offset = random.uniform(0, depth)
    for _ in range(count):
        offsets.append(offset)
        offset += random.uniform(-depth / 3, depth / 3)
        offset = max(0, min(depth, offset))
    return offsets


def tear(image, layer, line, fringe, paper, keep_above):
    """Clear the layer on the far side of the torn line, leaving a strip of
       paper colour of varying width along the edge."""
    away = 1 if keep_above else -1
    outer = [(x, y + away * random.uniform(min(1, fringe), fringe))
             for x, y in line]

    # Everything past the outer line goes. Pad far beyond the image so the
    # polygon covers all of the layer, wherever it is offset.
    far = away * 10 * (image.get_height() + image.get_width())
    beyond = outer + [(outer[-1][0], far), (outer[0][0], far)]
    image.select_polygon(Gimp.ChannelOps.REPLACE, flat(beyond))
    layer.edit_clear()

    if fringe > 0:
        strip = line + list(reversed(outer))
        image.select_polygon(Gimp.ChannelOps.REPLACE, flat(strip))
        Gimp.context_set_foreground(paper)
        layer.edit_fill(Gimp.FillType.FOREGROUND)


def flat(points):
    return [coordinate for point in points for coordinate in point]


Gimp.main(PageRip.__gtype__, sys.argv)
