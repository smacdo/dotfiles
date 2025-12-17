#!/usr/bin/env python3
"""
A simple Sudoku puzzle solver.
"""

import argparse
import logging
import unittest
from io import TextIOWrapper
from typing import Generator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

BOX_ROWS = 3
BOX_COLS = 3
MAX_ROWS = 9
MAX_COLS = 9
MIN_DIGIT = 1
MAX_DIGIT = 9
MAX_SOLVE_ITERATIONS = 20


class SudokuException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class SudokuValidationError(SudokuException):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class SudokuInvalidCharacterError(SudokuValidationError):
    def __init__(self, char: str, index: int) -> None:
        super().__init__(
            f"unknown character {char} at index {index} when parsing sudoku"
        )


class SudokuInvalidRowCountError(SudokuValidationError):
    def __init__(self, expected_row_count: int, actual_row_count: int) -> None:
        super().__init__(
            f"expected {expected_row_count} rows but got {actual_row_count} rows"
        )


class SudokuInvalidColCountError(SudokuValidationError):
    def __init__(
        self, row: int, expected_col_count: int, actual_col_count: int
    ) -> None:
        super().__init__(
            f"expected {expected_col_count} cols but got {actual_col_count} cols at row {row}"
        )


class SudokuInvalidDigitError(SudokuValidationError):
    def __init__(
        self, digit: int, row_i: int, col_i: int, row_j: int, col_j: int
    ) -> None:
        super().__init__(
            f"digit {digit} at row {row_j} col {col_j} conflicts with row {row_i} col {col_i}"
        )


class SudokuCannotSolveError(SudokuValidationError):
    def __init__(self, iteration_count: int) -> None:
        super().__init__(f"failed to solve sudoku after {iteration_count} iterations")


def all_cells() -> Generator[tuple[int, int], None, None]:
    for r_i in range(0, MAX_ROWS):
        for c_i in range(0, MAX_COLS):
            yield r_i, c_i


def row_peers(row: int, col: int) -> Generator[tuple[int, int], None, None]:
    for c_i in range(0, MAX_COLS):
        if c_i == col:
            continue

        yield row, c_i


def col_peers(row: int, col: int) -> Generator[tuple[int, int], None, None]:
    for r_i in range(0, MAX_ROWS):
        if r_i == row:
            continue

        yield r_i, col


def box_peers(row: int, col: int) -> Generator[tuple[int, int], None, None]:
    start_row = (row // BOX_ROWS) * BOX_ROWS
    start_col = (col // BOX_COLS) * BOX_COLS

    for r_i in range(start_row, start_row + BOX_ROWS):
        for c_i in range(start_col, start_col + BOX_COLS):
            if r_i == row and c_i == col:
                continue

            yield r_i, c_i


def all_peers(row: int, col: int) -> Generator[tuple[int, int], None, None]:
    yield from row_peers(row, col)
    yield from col_peers(row, col)
    yield from box_peers(row, col)


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

    def solution(self) -> int:
        if len(self.digits) == 1:
            return self.digits[0]
        else:
            raise Exception(
                f"cannot get solution at row {self.row} col {self.col} because it has multiple digits ({self.digits})"
            )

    def _eliminate(self, digit: int, throw_if_missing: bool = False) -> bool:
        if digit not in self.digits:
            if throw_if_missing:
                raise Exception(
                    f"cannot eliminate digit {digit} because it is not in the list of possible digits {self.digits} at row {self.row} col {self.col}"
                )

            return False

        if len(self.digits) == 1:
            raise Exception(
                f"cannot eliminate the last digit {digit} at row {self.row} col {self.col}"
            )

        self.digits.remove(digit)
        return True

    def eliminate(self, digit: int):
        self._eliminate(digit, throw_if_missing=True)

    def try_eliminate(self, digit: int) -> bool:
        return self._eliminate(digit, throw_if_missing=False)

    def __contains__(self, item) -> bool:
        return item in self.digits

    def __len__(self) -> int:
        return len(self.digits)

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
        if len(initial_values) != MAX_ROWS:
            raise SudokuInvalidRowCountError(MAX_ROWS, len(initial_values))

        for r_i in range(0, MAX_ROWS):
            if len(initial_values[r_i]) != MAX_COLS:
                raise SudokuInvalidColCountError(
                    r_i, MAX_COLS, len(initial_values[r_i])
                )

        self.cells = [
            [
                Cell(row=row, col=col, initial_value=initial_values[row][col])
                for col in range(0, MAX_COLS)
            ]
            for row in range(0, MAX_ROWS)
        ]

    def is_solved(self) -> bool:
        return self.cells_completed() == MAX_ROWS * MAX_COLS

    def cells_completed(self) -> int:
        count = 0

        for r, c in all_cells():
            if self.cells[r][c].is_complete():
                count += 1

        return count

    def validate(self) -> None:
        for row, col in all_cells():
            cell = self.cells[row][col]

            if cell.is_complete():
                cell_value = cell.solution()

                for n_row, n_col in all_peers(row, col):
                    n_cell = self.cells[n_row][n_col]

                    if n_cell.is_complete() and cell.solution() == n_cell.solution():
                        raise Exception(
                            f"digit {cell_value} at row {n_row} col {n_col} conflicts with row {row} col {col}"
                        )

    def __getitem__(self, key: tuple[int, int]) -> Cell:
        return self.cells[key[0]][key[1]]

    def __setitem__(self, key, value) -> None:
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

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
                raise SudokuInvalidCharacterError(char, index)

    return Sudoku(rows)


def solve(sudoku: Sudoku) -> int:
    logging.debug(
        f"solve started with {sudoku.cells_completed()} initial cells provided"
    )

    for i in range(MAX_SOLVE_ITERATIONS):
        eliminations = propagate_constraints(sudoku)

        if eliminations > 0:
            logging.debug(
                f"iteration {i}: {eliminations} elimination with {sudoku.cells_completed()} completed"
            )
        elif not sudoku.is_solved():
            raise SudokuCannotSolveError(iteration_count=i + 1)
        else:
            return i

    raise SudokuCannotSolveError(iteration_count=MAX_SOLVE_ITERATIONS)


def propagate_constraints(sudoku: Sudoku) -> int:
    eliminations = 0

    for row, col in all_cells():
        eliminations += propagate_constraint_at(sudoku, row, col)

    return eliminations


def propagate_constraint_at(sudoku: Sudoku, row: int, col: int) -> int:
    eliminations = 0
    cell = sudoku.cells[row][col]

    if not cell.is_complete():
        return eliminations

    for n_row, n_col in all_peers(row, col):
        n_cell = sudoku.cells[n_row][n_col]
        if n_cell.try_eliminate(cell.solution()):
            eliminations += 1

    return eliminations


def assign(sudoku: Sudoku, row: int, col: int, digit: int) -> None:
    """
    Assigns `digit` as the single possible value for the cell at row `row` and col `col`, and remove
    other digits as possible values. The function will also remove `digit` as possible value from
    the cell's peers or raise an exception if a contradiction is encountered.
    """
    cell = sudoku[(row, col)]

    for d in cell.digits:
        if d != digit:
            eliminate(sudoku, row, col, d)

    assert cell.solution() == digit


def eliminate(sudoku: Sudoku, row: int, col: int, digit: int) -> None:
    """
    Removes `digit` as a possible solution for the requested cell.

    :param sudoku:
    :param row:
    :param col:
    :param digit:
    :return:
    """
    cell = sudoku.cells[row][col]
    assert digit in cell.digits

    # Remove the digit from `cell`'s possible solutions.
    assert cell.eliminate(digit)

    # If there is only one possible digit left for cell, then it must be the solution. Eliminate
    # this digit from the cell's peers.
    if cell.is_complete():
        assert digit == cell.solution()

        for row_j, col_j in all_peers(row, col):
            peer = sudoku.cells[row_j][col_j]
            peer.try_eliminate(digit)

    # Check this cell's row, column and box units. If there's only one location for the digit in
    # a set then assign it, otherwise if there are no locations throw an exception.
    def find_possible_cells(
        digit: int, peers: Generator[tuple[int, int], None, None]
    ) -> Generator[Cell, None, None]:
        for row_k, col_k in peers:
            if digit in sudoku.cells[row_k][col_k]:
                yield sudoku.cells[row_k][col_k]

    for peer_group_generator in [
        row_peers(row, col),
        col_peers(col, row),
        box_peers(row, col),
    ]:
        # Locate the cells in the peer group where this digit could be placed, or has been placed.
        # TODO: avoid the allocation from calling list.
        places = list(find_possible_cells(digit, peer_group_generator))

        if len(places) == 0:
            # TODO: Make specialized exception with better message
            raise Exception(
                "peer group must have a cell where digit {digit} can be placed"
            )
        elif len(places) == 1 and not places[0].is_complete():
            assign(sudoku, places[0].row, places[1].col, digit)


def load_sudoku_file(
    sudoku_file: TextIOWrapper, multi_puzzle: bool = False
) -> list[Sudoku]:
    file_contents = sudoku_file.read()

    if multi_puzzle:
        return [parse_sudoku(line) for line in file_contents.splitlines()]
    else:
        return [parse_sudoku(file_contents)]


def main():
    parser = argparse.ArgumentParser(description="A simple Sudoku puzzle solver")

    parser.add_argument(
        "-i", "--input", type=argparse.FileType("r"), required=True, help="sudoku file"
    )
    parser.add_argument(
        "-m",
        "--multi",
        action="store_true",
        help="Specify that the input file has multiple puzzles (one per line)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show additional logging output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    prevalidation_error_count = 0
    solver_error_count = 0

    for index, sudoku in enumerate(
        load_sudoku_file(parser.parse_args().input, multi_puzzle=args.multi)
    ):
        # Validate sudoku input prior to solving it.
        try:
            sudoku.validate()
        except SudokuValidationError as e:
            logging.error(
                f"Sudoku on line {index} failed validation after loading: {e}"
            )
            prevalidation_error_count += 1
            continue

        # Solve the Sudoku puzzle.
        try:
            solve(sudoku)
            sudoku.validate()

            print(sudoku.to_formatted_str(with_grid=True))
        except SudokuValidationError as e:
            print("===== SOLVER ERROR =====")
            print(sudoku.to_formatted_str(with_grid=True, show_candidates=True))
            print(f"ERROR: {e}")
            print(f" LINE: {index + 1}")
            print("========================")
            solver_error_count += 1

    if prevalidation_error_count > 0:
        logging.error(
            f"!!! Encountered {prevalidation_error_count} load validation errors!"
        )

    if solver_error_count > 0:
        logging.error(f"!!! Encountered {solver_error_count} solver errors!")


class SudokuTests(unittest.TestCase):
    def test_peer_generators(self):
        self.assertEqual(
            [x for x in row_peers(3, 6)],
            [
                (3, 0),
                (3, 1),
                (3, 2),
                (3, 3),
                (3, 4),
                (3, 5),
                (3, 7),
                (3, 8),
            ],
        )

        self.assertEqual(
            [x for x in col_peers(3, 6)],
            [
                (0, 6),
                (1, 6),
                (2, 6),
                (4, 6),
                (5, 6),
                (6, 6),
                (7, 6),
                (8, 6),
            ],
        )

        self.assertEqual(
            [x for x in box_peers(4, 6)],
            [
                (3, 6),
                (3, 7),
                (3, 8),
                (4, 7),
                (4, 8),
                (5, 6),
                (5, 7),
                (5, 8),
            ],
        )

        self.assertEqual(
            [x for x in all_peers(4, 6)],
            [x for x in row_peers(4, 6)]
            + [x for x in col_peers(4, 6)]
            + [x for x in box_peers(4, 6)],
        )


if __name__ == "__main__":
    main()
