import io

from PIL import Image, ImageDraw

import toga
from toga.style.pack import CENTER, COLUMN, Pack


class ImageViewApp(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title=self.name)

        box = toga.Box(
            style=Pack(
                padding=10,
                alignment=CENTER,
                direction=COLUMN,
            )
        )

        # image from relative path, specified as a string load brutus.png from
        # the package. We set the style width/height parameters; image is
        # 876x256, but we scale to height=72
        image_from_path = toga.Image("resources/pride-brutus.png")
        imageview_from_path = toga.ImageView(
            image_from_path,
            style=Pack(height=72),
        )
        box.add(imageview_from_path)

        # image from pathlib.Path object
        # same as the above image, just with a different argument type
        image_from_pathlib_path = toga.Image(
            self.paths.app / "resources" / "pride-brutus.png"
        )
        imageview_from_pathlib_path = toga.ImageView(
            image_from_pathlib_path,
            style=Pack(width=256, flex=1),
        )
        box.add(imageview_from_pathlib_path)

        # image from bytes
        # generate an image using pillow
        img = Image.new("RGBA", size=(110, 30))
        d1 = ImageDraw.Draw(img)
        d1.text((20, 10), "Pillow image", fill="green")
        # get png bytes
        buffer = io.BytesIO()
        img.save(buffer, format="png", compress_level=0)

        image_from_bytes = toga.Image(data=buffer.getvalue())
        imageview_from_bytes = toga.ImageView(image_from_bytes, style=Pack(height=72))
        box.add(imageview_from_bytes)

        # image from remote URL
        # no style parameters - we let Pack determine how to allocate
        # the space. toga.png is a 256x256 image.
        image_from_url = toga.Image(
            "https://beeware.org/project/projects/libraries/toga/toga.png"
        )
        imageview_from_url = toga.ImageView(image_from_url)
        box.add(imageview_from_url)

        # An empty imageview.
        empty_imageview = toga.ImageView()
        box.add(empty_imageview)

        self.main_window.content = box
        self.main_window.show()


def main():
    return ImageViewApp("ImageView", "org.beeware.widgets.imageview")


if __name__ == "__main__":
    app = main()
    app.main_loop()
