# -*- coding: utf-8 -*-


import dbc


def main():
    cli = dbc.DropboxCLI()
    cli.start()
    cli.stop()

if __name__ == "__main__":
    main()
