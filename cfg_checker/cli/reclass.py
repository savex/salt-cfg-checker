from .command import cli_command


def entrypoint():
    cli_command(
        '# Mirantis Cloud Reclass comparer"',
        'reclass'
    )


if __name__ == "__main__":
    entrypoint()
