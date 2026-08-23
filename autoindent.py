#      StrIndent. A tool to automatically indent your strings.
#      Copyright (C) 2023 Avester
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from typing import Iterable

# TODO: add basic separator setup and etc.
class Indent:
    """Main class for auto indenting"""
    def __str__(self):
        return self.__output_string[:-1]

    def __init__(self, basic_str: str = "", separator: str = " ", basic_level: int = 0):
        """"""
        self.separator = separator
        self.basic_level = basic_level

        self.__indent_level = 0  # protection from accidental change of main values
        self.__output_string = basic_str

    def __add_to_output_string(self, string: str, indent: str = "") -> None:
        self.__output_string += f"{indent}{string}\n"
        return

    def set_indent_level(self, format_level: int) -> None:
        self.__indent_level = format_level

    def reset_indent_level(self) -> None:
        self.__indent_level = 0  # TODO: maybe it's better to contain basic_level as protected variable?

    def add(self, input_str: str | Iterable[str], format_level: int = 0,
                    increase_formatting_from: int = 0) -> None:

        indent = (self.separator * format_level)

        if isinstance(input_str, str):
            if input_str.count("\n") > 0:
                for num, curr_str in enumerate(input_str.split("\n")):
                    if num < increase_formatting_from:
                        continue

                    self.__add_to_output_string(curr_str, indent)
            else:
                self.__add_to_output_string(input_str, indent)

        else:
            for num, curr_str in enumerate(input_str):
                if num < increase_formatting_from:
                    continue

                self.__add_to_output_string(curr_str, indent)

    def get_output(self) -> str:
        return self.__output_string[:-1]

    def reset_output(self) -> None:
        self.__output_string = ""

    def replace_output(self, replacement: str) -> None:
        self.reset_output()
        self.__output_string = replacement
