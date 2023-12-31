# !pip install pystac planetary_computer rioxarray odc.stac matplotlib pystac

import pystac_client
import planetary_computer
import odc.stac
import matplotlib.pyplot as plt
from pystac.extensions.eo import EOExtension as eo

from flask import Flask, send_file, render_template, abort, request
import io
import sys  # Make sure to import sys

# import mercantile  # You might need to install this package


app = Flask(__name__)


def plot_image(bbox_of_interest): 
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    # bbox_of_interest = [89.419391,22.732522,89.671905,22.853430] # Bounding box of study
    time_of_interest = "2022-01-01/2022-12-31" # Define start and end date

    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=bbox_of_interest,
        datetime=time_of_interest,
        query={"eo:cloud_cover": {"lt": 1}},
    )

    items = search.item_collection()

    selected_item = items[5] # min(items, key=lambda item: eo.ext(item).cloud_cover)
    print(
        f"Choosing {selected_item.id} from {selected_item.datetime.date()}"
        + f" with {selected_item.properties['eo:cloud_cover']}% cloud cover"
    )

    max_key_length = len(max(selected_item.assets, key=len))
    for key, asset in selected_item.assets.items():
        print(f"{key.rjust(max_key_length)}: {asset.title}")

    max_key_length = len(max(selected_item.assets, key=len))
    for key, asset in selected_item.assets.items():
        print(f"{key.rjust(max_key_length)}: {asset.title}")

    bands_of_interest = ["nir08", "red", "green", "blue", "qa_pixel"]
    data = odc.stac.stac_load(
        [selected_item], bands=bands_of_interest, bbox=bbox_of_interest
    ).isel(time=0)
    # data
    return data

    # fig, ax = plt.subplots(figsize=(10, 10))

    # data[["red", "green", "blue"]].to_array().plot.imshow(robust=True, ax=ax)
    # ax.set_title("Natural Color")


@app.route('/tiles')
def tiles():
    # Parse bbox and zoom from the query parameters
    try:
        bbox = request.args.get('bbox', type=str)
        zoom = request.args.get('zoom', type=int)

        # if not bbox or not zoom:
        #     abort(400, description="Missing bbox or zoom parameters")

        if not bbox:
            abort(400, description="Missing bbox parameters")

        # Split the bbox into individual components
        bbox = [float(coord) for coord in bbox.split(',')]

        fig, ax = plt.subplots(figsize=(10, 10))

        data = plot_image(bbox)

        data[["red", "green", "blue"]].to_array().plot.imshow(robust=True, ax=ax)

        ax.set_title("Natural Color")

        # Save the figure to a BytesIO object
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes)
        img_bytes.seek(0)
        plt.close()

        # Send the bytes in response
        return send_file(img_bytes, mimetype='image/png')

    except Exception as e:
        # Handle exceptions, such as tile out of range
        # logger.exception(f"Failed to generate tile z={z} x={x} y={y}")

        print(f"An error occurred: {e}", file=sys.stderr)
        # You can also include more details like the traceback
        import traceback
        print(traceback.format_exc(), file=sys.stderr)

        abort(404, description="Tile not found")


if __name__ == '__main__':
    app.run(debug=True)
