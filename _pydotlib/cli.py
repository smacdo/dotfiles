def input_field(
    message: str, default_message: str | None = None, default_value: str | None = None
) -> str | None:
    if default_message is None:
        default_message = (
            f"[{default_value}]"
            if (default_value is not None and default_value.strip() != "")
            else "(leave blank for none)"
        )
    else:
        default_message = f"({default_message})"

    input_result = input(f"{message} {default_message}: ")

    if input_result.strip() == "":
        return default_value
    else:
        return input_result