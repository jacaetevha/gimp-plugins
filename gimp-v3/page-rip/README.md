# Page Rip

Cuts a band out of an image and joins the two remaining pieces with ragged, torn-paper edges, as if a strip had been ripped out of a printed page. Useful for shortening a long screenshot or document scan without hiding that something was removed.

Requires GIMP 3. See [the install instructions](../README.md#installing-a-plug-in).

## Usage

1. Select the band you want to remove. It should run from one edge of the image to the opposite edge:
   - a **rectangle** for a straight tear,
   - a **parallelogram** (made with the Free Select tool) for a slanted tear,
   - a **trapezoid** if the two tears should be at different angles.

   The band can run left-to-right (horizontal) or top-to-bottom (vertical). If the selection stops short of the image border, it's extended out to the border. It must leave something on both sides; a band touching the top or bottom of the image (or left or right, for a vertical band) has nothing to join.
2. Choose **Filters → Decor → Page Rip…**.
3. Adjust the options and click **OK**.

The visible layers are merged and the result replaces them in the current image as a single undo step. Tick **Create a new image** to leave the original untouched.

The result is three layers: **Top** and **Bottom** (or **Left** and **Right**) for the two torn pieces, and **Background** showing through the gap, so you can still adjust them afterwards.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| Direction | Auto | Which way the band runs. Auto picks the direction the selection spans; set Horizontal or Vertical if it guesses wrong. |
| Gap | 16 px | Space between the two torn edges. 0 makes the pieces touch. |
| Tear depth | 10 px | How far the ragged edge wanders. 0 gives a straight cut. |
| Paper fringe | 4 px | Width of the light paper-coloured strip along each torn edge. 0 for none. |
| Paper colour | white | Colour of the fringe. |
| Background | white | Colour showing through the gap. Set its alpha to 0 for a transparent gap. |
| Create a new image | off | Put the result in a new image instead of changing this one. Hidden layers are left out of the new image. |

The tear is random, so running it again gives a different edge. Undo and rerun if you don't like the first one.

## Notes

- Each piece is torn along its own edge of the band and the tear only eats into that piece, so nothing from the removed band shows.
- With a trapezoid the two edges aren't parallel, so the pieces can't meet evenly. They're brought together until they touch (plus the gap) at the band's narrowest point, leaving a wedge-shaped gap elsewhere.
- Running it with no selection stops with "Select the band to cut out first".
