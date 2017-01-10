# -*- coding: utf-8 -*-
import click
import conftest
import zazu.cli
import zazu.style
import test_util
import os


def test_style(repo_with_style):
    dir = repo_with_style.working_tree_dir
    with conftest.working_directory(dir):
        test_util.touch_file('temp.c')
        test_util.touch_file('temp.cpp')
        test_util.touch_file('temp.hpp')
        test_util.touch_file('temp.h')
        test_util.touch_file('temp.py')
        runner = click.testing.CliRunner()
        result = runner.invoke(zazu.cli.cli, ['style'])
        assert result.exit_code == 0
        assert result.output == '0 files fixed in 5 files\n'


def test_style_no_config(repo_with_no_zazu_file):
    dir = repo_with_no_zazu_file.working_tree_dir
    with conftest.working_directory(dir):
        runner = click.testing.CliRunner()
        result = runner.invoke(zazu.cli.cli, ['style'])
        assert result.output == 'Error: unable to parse config file\n'
        assert result.exit_code == -1


def test_style_no_config(repo_with_missing_style):
    dir = repo_with_missing_style.working_tree_dir
    with conftest.working_directory(dir):
        runner = click.testing.CliRunner()
        result = runner.invoke(zazu.cli.cli, ['style'])
        assert result.output == 'no style settings found\n'
        assert result.exit_code == 0
