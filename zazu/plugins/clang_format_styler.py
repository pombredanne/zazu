# -*- coding: utf-8 -*-
"""ClangFormatStyler plugin for zazu."""
import zazu.styler
import zazu.util

__author__ = "Nicholas Wiles"
__copyright__ = "Copyright 2017"


class ClangFormatStyler(zazu.styler.Styler):
    """ClangFormat plugin for code styling."""

    def style_file(self, path, verbose, dry_run):
        """Check a single file to see if it is within style guidelines and optionally fix it."""
        args = ['clang-format'] + self. options

        check_args = args + ['-output-replacements-xml', path]
        fix_args = args + ['-i', path]

        fix_needed = True
        if dry_run or verbose:
            output = zazu.util.check_output(check_args)
            replacements_indicator = '</replacement>'
            if replacements_indicator not in output:
                fix_needed = False
        if not dry_run and fix_needed:
            zazu.util.check_output(fix_args)
        return path, fix_needed

    @staticmethod
    def default_extensions():
        """Return the list of file extensions that are compatible with this Styler."""
        return ['*.c',
                '*.cc',
                '*.cpp',
                '*.h',
                '*.hpp',
                '*.java',
                '*.js',
                '*.proto']

    @staticmethod
    def type():
        """Return the name of this Styler."""
        return 'clang-format'
