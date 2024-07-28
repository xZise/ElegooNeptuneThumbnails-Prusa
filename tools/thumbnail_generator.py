from typing import Callable, List
import math


class SliceData:
    """
    Result data from slicing
    """

    def __init__(self, time_seconds: int, printer_model: str, model_height: float, filament_grams: float,
                 filament_cost: float, currency: str = None):
        self.printer_model: str = printer_model
        self.time_seconds: int = time_seconds
        self.model_height: float = model_height
        self.filament_grams: float = filament_grams
        self.filament_cost: float = filament_cost
        self.currency: str = currency if currency else "€"


class ThumbnailGenerator:
    _corner_choices: dict[str, Callable[[SliceData], str]]

    @staticmethod
    def _nothing(slice_data: SliceData) -> str:
        return ""

    @staticmethod
    def _time_estimate(slice_data: SliceData) -> str:
        time_minutes: int = math.floor(slice_data.time_seconds / 60)
        return f"⧖ {time_minutes // 60}:{time_minutes % 60:02d}h"

    @staticmethod
    def _filament_grams_estimate(slice_data: SliceData) -> str:
        return f"⭗ {round(slice_data.filament_grams)}g"

    @staticmethod
    def _model_height(slice_data: SliceData) -> str:
        if slice_data.model_height < 0:
            return f"⭱ N/A"
        else:
            return f"⭱ {round(slice_data.model_height, 2)}mm"

    @staticmethod
    def _filament_cost_estimate(slice_data: SliceData) -> str:
        return f"⛁ {round(slice_data.filament_cost, 2):.02f}{slice_data.currency}"

    @classmethod
    def available_options(cls) -> List[str]:
        return list(cls._corner_choices)

    @classmethod
    def calculate_option(cls, option: str, slice_data: SliceData) -> str:
        func = cls._corner_choices.get(option, None)
        if func is not None:
            return func(slice_data)
        else:
            return ""

    @classmethod
    def generate_option_lines(cls, corner_options, slice_data: SliceData) -> list[str]:
        """
        Generate the texts for the corners from settings
        """
        lines: list[str] = []
        for option in corner_options:
            line = cls.calculate_option(option, slice_data)
            lines.append(line)
        return lines

ThumbnailGenerator._corner_choices = {
    "nothing": ThumbnailGenerator._nothing,
    "time_estimate": ThumbnailGenerator._time_estimate,
    "filament_grams_estimate": ThumbnailGenerator._filament_grams_estimate,
    "model_height": ThumbnailGenerator._model_height,
    "filament_cost_estimate": ThumbnailGenerator._filament_cost_estimate,
}