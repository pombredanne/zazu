# -*- coding: utf-8 -*-
"""astyle plugin for zazu."""
import zazu.styler
zazu.util.lazy_import(locals(), [
    'subprocess'
])

__author__ = "Nicholas Wiles"
__copyright__ = "Copyright 2017"


class AstyleStyler(zazu.styler.Styler):
    """Astyle plugin for code styling."""

    def style_file(self, path, verbose, dry_run):
        """Check a single file to see if it is within style guidelines and optionally fix it."""
        with open(path, 'r') as f:
            input_string = f.read()
            styled_string = self.style_string(input_string)
        if not dry_run:
            with open(path, 'w') as f:
                f.write(styled_string)
        changed = input_string != styled_string
        return path, changed

    def style_string(self, string):
        """Fix a string to be within style guidelines."""
        args = ['astyle'] + self.options
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(string)
        if p.returncode:
            raise subprocess.CalledProcessError(stderr)
        return stdout

    @staticmethod
    def default_extensions():
        """Return the list of file extensions that are compatible with this Styler."""
        return ['*.c',
                '*.cc',
                '*.cs',
                '*.cpp',
                '*.h',
                '*.hpp',
                '*.java']

    @staticmethod
    def type():
        """Return the string type of this Styler."""
        return 'astyle'
