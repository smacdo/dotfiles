"""
A simple Sudoku puzzle solver.
"""

import argparse
from io import TextIOWrapper

BOX_ROWS = 3
BOX_COLS = 3
MAX_ROWS = 9
MAX_COLS = 9
MIN_DIGIT = 1
MAX_DIGIT = 9


class Cell:
    """
    Represents a single cell in a larger Sudoku puzzle grid.

    A cell holds a list of possible values and is considered complete when there is only one
    possible value left. Removing the last possible value from the cell is in an invalid operation
    and represents an invalid or unsolvable puzzle.
    """

    fixed: bool  # True if the cell was initialized with a single possible value.
    digits: list[int]  # A list of possible values for this cell.
    row: int  # Index of the row for this cell (0 based index).
    col: int  # Index of the col for this cell (0 based index).

    def __init__(self, row: int, col: int, initial_value: int | None = None) -> None:
        if row < 0 or row >= MAX_ROWS:
            raise ValueError(f"Row {row} is out of bounds")
        if col < 0 or col >= MAX_COLS:
            raise ValueError(f"Column {col} is out of bounds")

        if initial_value is None:
            self.fixed = False
            self.digits = list(range(MIN_DIGIT, MAX_DIGIT + 1))
        else:
            if initial_value < MIN_DIGIT or initial_value > MAX_DIGIT:
                raise ValueError(
                    f"Value {initial_value} in cell row {row} col {col} is invalid"
                )

            self.fixed = True
            self.digits = [initial_value]

    def is_complete(self) -> bool:
        return len(self.digits) == 1

    def __str__(self) -> str:
        return self.to_formatted_str()

    def to_formatted_str(
        self,
        show_candidates: bool = False,
        unknown_value: str = ".",
    ) -> str:
        if len(self.digits) == 1:
            return str(self.digits[0])
        else:
            if show_candidates:
                all_digits_str = "".join(str(x) for x in self.digits)
                return f"{{{all_digits_str}}}"
            else:
                return unknown_value


class Sudoku:
    cells: list[list[Cell]]

    def __init__(self, initial_values: list[list[int | None]]) -> None:
        self.cells = [
            [
                Cell(row=row, col=col, initial_value=initial_values[row][col])
                for col in range(0, MAX_COLS)
            ]
            for row in range(0, MAX_ROWS)
        ]

    def __str__(self) -> str:
        return self.to_formatted_str(multi_line=True)

    def to_formatted_str(
        self,
        multi_line: bool = True,
        with_grid: bool = False,
        show_candidates: bool = False,
        unknown_value: str = ".",
    ) -> str:
        output = ""
        cell_space_required = 1

        if show_candidates:
            # TODO: Calculate the maximum space required to show candidates.
            #       - use .center() just center justify all candidates.
            #       - format per cell is "{123456789}" or "3" if one value.
            for row in range(0, MAX_ROWS):
                for col in range(0, MAX_COLS):
                    space_required = len(
                        self.cells[row][col].to_formatted_str(show_candidates=True)
                    )
                    cell_space_required = max(cell_space_required, space_required)

        for row in range(0, MAX_ROWS):
            if with_grid and row % BOX_ROWS == 0 and row > 0:
                for x in range(0, BOX_COLS):
                    output += "-" * ((cell_space_required + 1) * BOX_COLS)

                    if x == BOX_COLS - 1:
                        output += "\n"
                    else:
                        output += "+-"

            for col in range(0, MAX_COLS):
                if with_grid and col % BOX_COLS == 0 and col > 0:
                    output += "| "

                cell_output = self.cells[row][col].to_formatted_str(
                    show_candidates=show_candidates,
                    unknown_value=unknown_value,
                )

                output += cell_output.center(cell_space_required)

                if with_grid and col < MAX_COLS - 1:
                    output += " "

            if multi_line:
                output += "\n"

        return output


def parse_sudoku(sudoku_text: str) -> Sudoku:
    sudoku_text = sudoku_text.replace("\r\n", "")
    sudoku_text = sudoku_text.replace("\n", "")
    sudoku_text = sudoku_text.strip()

    if len(sudoku_text) != MAX_ROWS * MAX_COLS:
        raise ValueError(
            f"sudoku input file must be {MAX_ROWS * MAX_COLS} chars in length, but was {len(sudoku_text)}"
        )

    rows = []

    for row in range(0, MAX_ROWS):
        rows.append([])

        for col in range(0, MAX_COLS):
            index = row * MAX_COLS + col
            char = sudoku_text[index]

            if char == "." or char == "0":
                rows[-1].append(None)
            elif len(char) == 1 and char.isdigit():
                rows[-1].append(int(char))
            else:
                raise ValueError(
                    f"unknown character {char} at index {index} when parsing sudoku input"
                )

    return Sudoku(rows)


def load_sudoku_file(sudoku_file: TextIOWrapper) -> Sudoku:
    return parse_sudoku(sudoku_file.read())


def main():
    parser = argparse.ArgumentParser(description="A simple Sudoku puzzle solver")

    parser.add_argument(
        "-i", "--input", type=argparse.FileType("r"), required=True, help="sudoku file"
    )

    print(
        load_sudoku_file(parser.parse_args().input).to_formatted_str(
            with_grid=True, show_candidates=True
        )
    )


if __name__ == "__main__":
    main()