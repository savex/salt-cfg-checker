from .command import cli_command


def entrypoint():
    cli_command(
        "# Mirantis Cloud Package checker",
        'packages'
    )


if __name__ == '__main__':
    entrypoint()
