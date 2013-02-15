# -*- coding: utf-8 -*-

import sys


def human_readable_size(size):
    for s in ["bytes", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return "%3.1f %s" % (size, s)
        size /= 1024.0


def print_readable_table(rows, headings=None, space="  ", indent=""):
    if headings and rows and len(headings) != len(rows):
        raise Exception("Headings and rows must have the same length")
    max_len_cols = []
    counter = 0
    for c in zip(*rows):
        max_len = len(max([str(i) for i in c], key=len))
        if headings and len(headings[counter]) > max_len:
            max_len = headings[counter]
        max_len_cols.append(max_len)
        counter += 1
    if headings:
        counter = 0
        for h in headings:
            sys.stdout.write(indent)
            sys.stdout.write(str(h) + " " * (max_len_cols[counter] - len(str(c))) + space)
            counter += 1
        sys.stdout.write("\n" + "-" * (sum(max_len_cols) + 2 * len(max_len_cols)) + "\n")

    for r in rows:
        counter = 0
        for c in r:
            sys.stdout.write(indent)
            sys.stdout.write(str(c) + " " * (max_len_cols[counter] - len(str(c))) + space)
            counter += 1
        sys.stdout.write("\n")
