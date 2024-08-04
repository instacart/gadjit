import time
import shutil
import click
import os
from columnar import columnar

# Initialize the data with empty columns
data = [["", ""]]
headers = ["INPUT", "GPT OUTPUT"]


def print_table(data):
    # Get the current terminal size
    """
    Print a table with the given data.

    Args:
        data (list): A list of lists with the table data to be displayed.

    Returns:
        None

    Raises:
        None
    """
    terminal_size = shutil.get_terminal_size((80, 20))
    max_column_width = (
        terminal_size.columns // 2 - 2
    )  # Adjusting for borders and padding
    max_rows = 25
    # Ensure data fits in the terminal window
    data_to_display = data[-max_rows:] if len(data) > max_rows else data

    table = columnar(
        data_to_display,
        headers,
        no_borders=False,
        justify=["l", "l"],
        min_column_width=max_column_width,
    )
    print(table)


def update_data(data, new_content, side):
    """
    Update the content of a data table with new content.

    Args:
        data (list): A list of lists representing the current data table.
        new_content (str): The new content to be added to the data table.
        side (str): The side of the data table where the new content should be added ('left' or 'right').

    Returns:
        list: The updated data table with the new content added.

    Notes:
        The function uses the `click.style` method to colorize the content. The color of the new content is set to blue if added to the 'left' side and red if added to the 'right' side.

    Raises:
        None
    """
    blue = click.style(new_content, fg="blue")
    red = click.style(new_content, fg="red")
    black = click.style("", fg="black")

    # Color all existing data black
    for row in data:
        row[0] = click.style(row[0], fg="black")
        row[1] = click.style(row[1], fg="black")

    if side == "left":
        if data[-1][0] == "" and data[-1][1] == "":
            data[-1][0] = blue
        else:
            data.append([blue, ""])
    elif side == "right":
        if data[-1][0] == "" and data[-1][1] == "":
            data[-1][1] = red
        else:
            data.append(["", red])

    return data


def print_left(content):
    """
    Print the content to the left side of the screen.

    Args:
        content (str): The content to be printed.

    Returns:
        None

    Globals:
        data (list): A list of strings representing the screen data.

    Raises:
        None
    """
    global data
    data = update_data(data, "", "left")
    for char in content:
        data[-1][0] += char
        refresh_screen()
        time.sleep(0.02)


def print_right(content):
    """
    Print the content aligned to the right on the screen.

    Args:
        content (str): The content to be printed aligned to the right.

    Returns:
        None

    Globals:
        data (list): A list containing screen data to be updated.

    Raises:
        None
    """
    global data
    data = update_data(data, "", "right")
    for char in content:
        data[-1][1] += char
        refresh_screen()
        time.sleep(0.02)


def refresh_screen():
    # Clear the terminal (works for UNIX systems)
    """
    Refreshes the screen by clearing it and printing a table.

    Args:
        None

    Returns:
        None
    """
    os.system("clear")
    print_table(data)


# Example usage
# try:
#    i = 0
#    while True:
#        print_left(f"{i} Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.")
#        time.sleep(0.5)
#        print_right(f"{i} Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.")
#        time.sleep(0.5)
#        i = i + 1
# except KeyboardInterrupt:
#    print("Stopped updating.")
