#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Signature to Alpha: lift ink off paper.
#
# Every pixel of the layer is placed on the line from the paper colour to the
# ink colour. Pixels near the paper end become transparent, pixels near the
# ink end opaque, with a soft ramp between so stroke edges stay smooth. Small
# isolated blobs left over (dust, scanner noise, JPEG speckle) are removed,
# and what remains is painted in a single output colour.
#
# The ink colour defaults to the foreground colour, so pick it from the
# signature with the Color Picker tool before running. The paper colour is
# taken from the image itself: the median colour, since paper dominates.

import sys

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl
gi.require_version('Babl', '0.1')
from gi.repository import Babl
from gi.repository import GObject
from gi.repository import GLib

PROC_NAME = "python-fu-signature-to-alpha"
FORMAT = "R'G'B'A u8"


class SignatureToAlpha(Gimp.PlugIn):
    def do_set_i18n(self, procname):
        return False

    def do_query_procedures(self):
        return [PROC_NAME]

    def do_create_procedure(self, name):
        Gegl.init(None)

        procedure = Gimp.ImageProcedure.new(self, name,
                                            Gimp.PDBProcType.PLUGIN,
                                            self.run, None)
        procedure.set_image_types("RGB*, GRAY*")
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE)
        procedure.set_menu_label("_Signature to Alpha...")
        procedure.add_menu_path("<Image>/Colors")
        procedure.set_documentation(
            "Make the paper around ink transparent, remove specks and "
            "recolour the ink",
            "Pixels close to the paper colour become transparent and pixels "
            "close to the ink colour opaque, with smooth edges. Isolated "
            "blobs smaller than the speck size are removed. The ink is "
            "painted in the output colour.",
            name)
        procedure.set_attribution("Jason Rogers", "Jason Rogers", "2026")

        procedure.add_color_argument("ink", "_Ink colour",
                                     "Colour of the ink in the image "
                                     "(starts as the foreground colour)",
                                     False, Gegl.Color.new("black"),
                                     GObject.ParamFlags.READWRITE)
        procedure.add_color_argument("output", "_Output colour",
                                     "Colour to paint the ink "
                                     "(starts as the foreground colour)",
                                     False, Gegl.Color.new("black"),
                                     GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("cutoff", "Paper _cut-off",
                                   "How far from paper to ink (%) a pixel "
                                   "must be before it shows at all",
                                   0, 99, 25, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("solid", "_Solid from",
                                   "How far from paper to ink (%) a pixel "
                                   "must be to be fully opaque",
                                   1, 100, 60, GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("speck", "_Remove specks under",
                                   "Remove isolated blobs with fewer pixels "
                                   "than this (0 keeps everything)",
                                   0, 100000, 50, GObject.ParamFlags.READWRITE)
        return procedure

    def run(self, procedure, run_mode, image, drawables, config, data):
        if len(drawables) != 1 or not isinstance(drawables[0], Gimp.Layer):
            return error(procedure, "Select a single layer")
        layer = drawables[0]

        if run_mode == Gimp.RunMode.INTERACTIVE:
            # Start from whatever was just picked with the Color Picker.
            foreground = Gimp.context_get_foreground()
            config.set_property("ink", foreground)
            config.set_property("output", foreground)

            GimpUi.init(PROC_NAME)
            dialog = GimpUi.ProcedureDialog.new(procedure, config,
                                                "Signature to Alpha")
            dialog.fill(None)
            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL,
                                                   GLib.Error())
            dialog.destroy()

        cutoff = config.get_property("cutoff")
        solid = config.get_property("solid")
        if cutoff >= solid:
            return error(procedure, "Paper cut-off must be below Solid from")

        width, height = layer.get_width(), layer.get_height()
        rect = Gegl.Rectangle.new(0, 0, width, height)
        pixels = layer.get_buffer().get(rect, 1.0, FORMAT,
                                        Gegl.AbyssPolicy.CLAMP)

        Gimp.progress_init("Lifting the signature")
        try:
            result = lift(pixels, width, height,
                          rgb(config.get_property("ink")),
                          rgb(config.get_property("output")),
                          cutoff / 100, solid / 100,
                          config.get_property("speck"),
                          Gimp.progress_update)
        except ValueError as e:
            return error(procedure, str(e))

        image.undo_group_start()
        try:
            layer.add_alpha()
            shadow = layer.get_shadow_buffer()
            shadow.set(rect, FORMAT, result)
            shadow.flush()
            layer.merge_shadow(True)
            layer.update(0, 0, width, height)
        finally:
            image.undo_group_end()

        Gimp.progress_end()
        Gimp.displays_flush()
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS,
                                           GLib.Error())


def error(procedure, message):
    return procedure.new_return_values(
        Gimp.PDBStatusType.CALLING_ERROR,
        GLib.Error.new_literal(Gimp.PlugIn.error_quark(), message, 0))


def rgb(color):
    """A Gegl.Color as 0-255 sRGB channels."""
    return tuple(color.get_bytes(Babl.format("R'G'B' u8")).get_data())


def lift(pixels, width, height, ink, output, cutoff, solid, speck,
         progress=lambda fraction: None):
    """Turn R'G'B'A u8 pixels of ink on paper into the output colour on
       transparency. Returns the new pixels."""
    paper = median_colour(pixels)
    alpha = ink_alpha(pixels, paper, ink, cutoff, solid, progress)
    if speck > 0:
        remove_specks(alpha, width, height, speck)

    result = bytearray(len(pixels))
    result[0::4] = bytes([output[0]]) * len(alpha)
    result[1::4] = bytes([output[1]]) * len(alpha)
    result[2::4] = bytes([output[2]]) * len(alpha)
    result[3::4] = alpha
    return bytes(result)


def median_colour(pixels):
    """The median of each colour channel over (a sample of) the pixels."""
    count = len(pixels) // 4
    step = max(1, count // 20000) * 4
    return tuple(sorted(pixels[channel::step])[len(pixels[channel::step]) // 2]
                 for channel in range(3))


def ink_alpha(pixels, paper, ink, cutoff, solid, progress):
    """For each pixel, how far it lies from paper towards ink, ramped from
       transparent at cutoff to opaque at solid and scaled by its own alpha."""
    direction = [i - p for i, p in zip(ink, paper)]
    length = sum(d * d for d in direction)
    if length < 30 * 30:
        raise ValueError("The ink colour is too close to the paper colour "
                         "%s; pick it from the signature" % (paper,))

    # Position along paper -> ink, in units where cutoff is 0 and solid 255:
    # a per-channel lookup table each, plus a constant.
    scale = 255 / ((solid - cutoff) * length)
    tables = [[value * d * scale for value in range(256)] for d in direction]
    offset = -sum(p * d for p, d in zip(paper, direction)) * scale - cutoff * 255 / (solid - cutoff)
    red, green, blue = tables

    count = len(pixels) // 4
    alpha = bytearray(count)
    chunk = max(1, count // 100)
    for start in range(0, count, chunk):
        for n in range(start, min(count, start + chunk)):
            i = n * 4
            level = red[pixels[i]] + green[pixels[i + 1]] + blue[pixels[i + 2]] + offset
            if level > 0:
                alpha[n] = (255 if level >= 255 else int(level + 0.5)) * pixels[i + 3] // 255
        progress(start / count)
    return alpha


def remove_specks(alpha, width, height, speck):
    """Clear 8-connected blobs of non-transparent pixels smaller than
       speck pixels."""
    seen = bytearray(len(alpha))
    for n in range(len(alpha)):
        if not alpha[n] or seen[n]:
            continue
        seen[n] = 1
        blob, stack = [], [n]
        while stack:
            m = stack.pop()
            blob.append(m)
            y, x = divmod(m, width)
            for ny in (y - 1, y, y + 1):
                if 0 <= ny < height:
                    for nx in (x - 1, x, x + 1):
                        if 0 <= nx < width:
                            k = ny * width + nx
                            if alpha[k] and not seen[k]:
                                seen[k] = 1
                                stack.append(k)
        if len(blob) < speck:
            for m in blob:
                alpha[m] = 0


if __name__ == "__main__":
    Gimp.main(SignatureToAlpha.__gtype__, sys.argv)
