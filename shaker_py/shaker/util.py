from shlex import split
from subprocess import DEVNULL, PIPE, Popen, run


def run_bash_command_with_output(command, cwd=None, shell=False):
    """
    With this helper, if any errors are raised while running the commands,
    they will be displayed on the terminal.
    """

    Popen(args=command, stdout=PIPE, cwd=cwd, shell=shell)


def subprocess_run(command, stdout=DEVNULL, stderr=DEVNULL, cwd=None):
    args = split(command)

    return run(args, stdout=stdout, stderr=stderr, cwd=cwd)


def subprocess_Popen(command, stdout=DEVNULL, stderr=DEVNULL, cwd=None):
    args = split(command)

    return Popen(args, stdout=stdout, stderr=stderr, cwd=cwd)
