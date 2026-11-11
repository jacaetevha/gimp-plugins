# Signature to Alpha

Lifts a scanned or photographed signature (or any ink drawing) off its paper: the paper becomes transparent, stray specks and scanner noise are removed, and the ink is painted in a colour of your choice. Export the result as a PNG to drop onto documents.

Requires GIMP 3. See [the install instructions](../README.md#installing-a-plug-in).

## Usage

1. Open the scan. Crop it close to the signature first if there's other writing or marks on the page.
2. With the **Color Picker** tool (`O`), click on a solid part of a stroke. This sets the foreground colour, which the plug-in uses as the ink colour. Any ink colour works: black, blue, red, green.
3. Choose **Colors → Signature to Alpha…**.
4. Adjust the options and click **OK**. It changes the selected layer as a single undo step.
5. Optionally use **Image → Crop to Content**, then **File → Export As…** and save as `.png` to keep the transparency.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| Ink colour | foreground colour | Colour of the ink in the image. Use the button's colour picker to pick it from the image if you didn't before opening the dialog. |
| Output colour | foreground colour | Colour the signature is painted in. Leave it as the ink colour, or change it to recolour, e.g. pick black ink and output blue. |
| Paper cut-off | 25 % | Pixels less than this far from the paper colour towards the ink colour become fully transparent. Raise it to remove faint smudges, grey halos or paper texture. |
| Solid from | 60 % | Pixels at least this far towards the ink colour are fully opaque. Pixels between the two are partly transparent, which keeps stroke edges smooth. Lower it to make thin or faint strokes bolder. |
| Remove specks under | 50 px | Isolated blobs smaller than this many pixels are removed. Raise it for dusty scans; lower it (or use 0) if it removes the dot of an *i*. Scale it with resolution: a 600 dpi scan needs a larger value than a phone photo. |

## How it works

The paper colour is the image's median colour, since paper covers most of it. Each pixel is placed on the line from that paper colour to the ink colour, and its position along that line sets its opacity between the cut-off and the solid point. That's why the ink colour matters: a blue signature on cream paper is separated by how blue each pixel is, not just how dark.

It works on the whole layer and ignores any selection. It needs RGB or greyscale images, and a layer that is mostly paper, so the median colour is the paper. If the ink colour is too close to the paper colour, it stops and asks you to pick the colour from the signature.
