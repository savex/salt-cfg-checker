from .command import cli_command


def entrypoint():
    cli_command(
        "# Mirantis Cloud Network checker",
        'network'
    )


if __name__ == '__main__':
    entrypoint()
