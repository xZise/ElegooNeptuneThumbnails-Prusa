# Copyright (c) 2023 - 2024 Molodos
# The ElegooNeptuneThumbnails plugin is released under the terms of the AGPLv3 or higher.

import argparse
import base64
from argparse import Namespace
from array import array

from PyQt6.QtCore import Qt, QByteArray, QBuffer, QIODeviceBase
from PyQt6.QtGui import QImage

import lib_col_pic


class ElegooNeptuneThumbnails:
    """
    ElegooNeptuneThumbnails post processing script
    """

    OLD_MODELS: list[str] = ["NEPTUNE2", "NEPTUNE2D", "NEPTUNE2S", "NEPTUNEX"]
    NEW_MODELS: list[str] = ["NEPTUNE4", "NEPTUNE4PRO", "NEPTUNE4PLUS", "NEPTUNE4MAX",
                             "NEPTUNE3PRO", "NEPTUNE3PLUS", "NEPTUNE3MAX"]
    B64JPG_MODELS: list[str] = ["ORANGESTORMGIGA"]

    def __init__(self):
        args: Namespace = self._parse_args()
        self._gcode: str = args.gcode
        self._printer_model: str = args.printer
        self._thumbnail: QImage = self._get_q_image_thumbnail()

        # Find printer model from gcode if not set
        if not self._printer_model or self._printer_model not in (
                self.OLD_MODELS + self.NEW_MODELS + self.B64JPG_MODELS):
            self._printer_model = self._get_printer_model()

    @classmethod
    def _parse_args(cls) -> Namespace:
        """
        Parse arguments from prusa slicer
        """
        # Parse arguments
        parser = argparse.ArgumentParser(
            prog="ElegooNeptuneThumbnails-Prusa",
            description="A post processing script to add Elegoo Neptune thumbnails to gcode")
        parser.add_argument("-p", "--printer", help="Printer model to generate for", type=str, required=False,
                            default="")
        parser.add_argument("gcode", help="Gcode path provided by PrusaSlicer", type=str)
        return parser.parse_args()

    def _get_base64_thumbnail(self) -> str:
        """
        Read the base64 encoded thumbnail from gcode file
        """
        # Try to find thumbnail
        found: bool = False
        base64_thumbnail: str = ""
        with open(self._gcode, "r", encoding="utf8") as file:
            for line in file.read().splitlines():
                if not found and line.startswith("; thumbnail begin 600x600"):
                    found = True
                elif found and line == "; thumbnail end":
                    return base64_thumbnail
                elif found:
                    base64_thumbnail += line[2:]

        # If not found, raise exception
        raise Exception(
            "Correct size thumbnail is not present: Make sure, that your slicer generates a thumbnail with size 600x600")

    def _get_q_image_thumbnail(self) -> QImage:
        """
        Read the base64 encoded thumbnail from gcode file and parse it to a QImage object
        """
        # Read thumbnail
        base64_thumbnail: str = self._get_base64_thumbnail()

        # Parse thumbnail
        thumbnail = QImage()
        thumbnail.loadFromData(base64.decodebytes(bytes(base64_thumbnail, "UTF-8")), "PNG")
        return thumbnail

    def _get_printer_model(self) -> str:
        """
        Read the printer model from gcode file
        """
        # Try to find printer model
        with open(self._gcode, "r", encoding="utf8") as file:
            for line in file.read().splitlines():
                if line.startswith("; printer_model = "):
                    return line[len("; printer_model = "):]

        # If not found, raise exception
        raise Exception("Printer model not found")

    def is_supported_printer(self) -> bool:
        """
        Check if printer is supported
        """
        return self._is_old_thumbnail() or self._is_new_thumbnail() or self._is_b64jpg_thumbnail()

    def _is_old_thumbnail(self) -> bool:
        """
        Check if an old printer is present
        """
        return self._printer_model in self.OLD_MODELS

    def _is_new_thumbnail(self) -> bool:
        """
        Check if a new printer is present
        """
        return self._printer_model in self.NEW_MODELS

    def _is_b64jpg_thumbnail(self) -> bool:
        """
        Check if a base 64 JPG printer is present
        """
        return self._printer_model in self.B64JPG_MODELS

    def _generate_gcode_prefix(self) -> str:
        """
        Generate a g-code prefix string
        """
        # Parse to g-code prefix
        gcode_prefix: str = ""
        if self._is_old_thumbnail():
            gcode_prefix += self._parse_thumbnail_old(self._thumbnail, 100, 100, "simage")
            gcode_prefix += self._parse_thumbnail_old(self._thumbnail, 200, 200, ";gimage")
        elif self._is_new_thumbnail():
            gcode_prefix += self._parse_thumbnail_new(self._thumbnail, 200, 200, "gimage")
            gcode_prefix += self._parse_thumbnail_new(self._thumbnail, 160, 160, "simage")
        elif self._is_b64jpg_thumbnail():
            gcode_prefix += self._parse_thumbnail_b64jpg(self._thumbnail, 400, 400, "gimage")
            gcode_prefix += self._parse_thumbnail_b64jpg(self._thumbnail, 114, 114, "simage")
        if gcode_prefix:
            gcode_prefix += ';Thumbnail generated by the ElegooNeptuneThumbnails-Prusa post processing script (https://github.com/Molodos/ElegooNeptuneThumbnails-Prusa)\r' \
                            ';Just mentioning "Cura_SteamEngine X.X" to trick printer into thinking this is Cura and not Prusa gcode\r\r'

        # Return
        return gcode_prefix

    def add_thumbnail_prefix(self) -> None:
        """
        Adds thumbnail prefix to the gcode file if thumbnail doesn't already exist
        """
        # Get gcode
        g_code: str
        with open(self._gcode, "r", encoding="utf8") as file:
            g_code: str = file.read()

        # Remove mark of PrusaSlicer
        g_code = g_code.replace("PrusaSlicer", "CensoredSlicer")

        # Add prefix
        if ';gimage:' not in g_code and ';simage:' not in g_code:
            gcode_prefix: str = self._generate_gcode_prefix()
            with open(self._gcode, "w", encoding="utf8") as file:
                file.write(gcode_prefix + g_code)

    @classmethod
    def _parse_thumbnail_old(cls, img: QImage, width: int, height: int, img_type: str) -> str:
        """
        Parse thumbnail to string for old printers
        TODO: Maybe optimize at some time
        """
        img_type = f";{img_type}:"
        result = ""
        b_image = img.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio)
        img_size = b_image.size()
        result += img_type
        datasize = 0
        for i in range(img_size.height()):
            for j in range(img_size.width()):
                pixel_color = b_image.pixelColor(j, i)
                r = pixel_color.red() >> 3
                g = pixel_color.green() >> 2
                b = pixel_color.blue() >> 3
                rgb = (r << 11) | (g << 5) | b
                str_hex = "%x" % rgb
                if len(str_hex) == 3:
                    str_hex = '0' + str_hex[0:3]
                elif len(str_hex) == 2:
                    str_hex = '00' + str_hex[0:2]
                elif len(str_hex) == 1:
                    str_hex = '000' + str_hex[0:1]
                if str_hex[2:4] != '':
                    result += str_hex[2:4]
                    datasize += 2
                if str_hex[0:2] != '':
                    result += str_hex[0:2]
                    datasize += 2
                if datasize >= 50:
                    datasize = 0
            # if i != img_size.height() - 1:
            result += '\rM10086 ;'
            if i == img_size.height() - 1:
                result += "\r"
        return result

    @classmethod
    def _parse_thumbnail_new(cls, img: QImage, width: int, height: int, img_type: str) -> str:
        """
        Parse thumbnail to string for new printers
        TODO: Maybe optimize at some time
        """
        img_type = f";{img_type}:"

        result = ""
        b_image = img.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio)
        img_size = b_image.size()
        color16 = array('H')
        try:
            for i in range(img_size.height()):
                for j in range(img_size.width()):
                    pixel_color = b_image.pixelColor(j, i)
                    r = pixel_color.red() >> 3
                    g = pixel_color.green() >> 2
                    b = pixel_color.blue() >> 3
                    rgb = (r << 11) | (g << 5) | b
                    color16.append(rgb)
            output_data = bytearray(img_size.height() * img_size.width() * 10)
            result_int = lib_col_pic.ColPic_EncodeStr(color16, img_size.height(), img_size.width(), output_data,
                                                      img_size.height() * img_size.width() * 10, 1024)

            data0 = str(output_data).replace('\\x00', '')
            data1 = data0[2:len(data0) - 2]
            each_max = 1024 - 8 - 1
            max_line = int(len(data1) / each_max)
            append_len = each_max - 3 - int(len(data1) % each_max) + 10
            j = 0
            for i in range(len(output_data)):
                if output_data[i] != 0:
                    if j == max_line * each_max:
                        result += '\r;' + img_type + chr(output_data[i])
                    elif j == 0:
                        result += img_type + chr(output_data[i])
                    elif j % each_max == 0:
                        result += '\r' + img_type + chr(output_data[i])
                    else:
                        result += chr(output_data[i])
                    j += 1
            result += '\r;'
            for m in range(append_len):
                result += '0'

        except Exception as e:
            raise e

        return result + '\r'

    @classmethod
    def _parse_thumbnail_b64jpg(cls, img: QImage, width: int, height: int, img_type: str) -> str:
        """
        Parse thumbnail to string for new printers
        TODO: Maybe optimize at some time
        """
        img_type = f";{img_type}:"

        result = ""
        b_image = img.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio)

        try:
            byte_array: QByteArray = QByteArray()
            byte_buffer: QBuffer = QBuffer(byte_array)
            byte_buffer.open(QIODeviceBase.OpenModeFlag.WriteOnly)
            b_image.save(byte_buffer, "JPEG")
            base64_string: str = str(byte_array.toBase64().data(), "UTF-8")

            each_max = 1024 - 8 - 1
            max_line = int(len(base64_string) / each_max)

            for i in range(len(base64_string)):
                if i == max_line * each_max:
                    result += '\r;' + img_type + base64_string[i]
                elif i == 0:
                    result += img_type + base64_string[i]
                elif i % each_max == 0:
                    result += '\r' + img_type + base64_string[i]
                else:
                    result += base64_string[i]

        except Exception as e:
            raise e

        return result + '\r'


if __name__ == "__main__":
    """
    Init point of the script
    """
    thumbnail_generator: ElegooNeptuneThumbnails = ElegooNeptuneThumbnails()
    if thumbnail_generator.is_supported_printer():
        thumbnail_generator.add_thumbnail_prefix()
