#
# linter.py
# Linter for SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by Mingholy
# Copyright (c) 2018 Mingholy
# License: MIT
#

"""This module exports the Zmzlinter plugin class."""
import re
import SublimeLinter.lint

# 兼容旧版本linter
if getattr(SublimeLinter.lint, 'VERSION', 3) > 3:
    from SublimeLinter.lint import const, Linter
    ERROR = const.ERROR
    WARNING = const.WARNING
else:
    from SublimeLinter.lint import highlight, Linter
    ERROR = highlight.ERROR
    WARNING = highlight.WARNING

class Zmzlinter(Linter):
    """
    Mark up format errors and character sequences that violate ZMZ format rules.
    """
    # view.settings().get('syntax')获取
    syntax = 'srt'
    cmd = None
    # 用来从output中取得格式化的错误信息
    regex = re.compile(r'^(?P<line>\d+):(?P<col>\d+): ((?P<warning>warning)|(?P<error>error)) (?P<message>.*)')
    # 传递给linter的默认参数
    defaults = {
        '--no-empty-cue=': 1,
        '--no-trailing-spaces:': 1,
        '--no-full-width-symbols:': 1,
        '--unexpected-spaces': 1,
        '--no-brackets-in-eng-line:': 1,
        '--unformatted-dialog:': 1,
        '--max-line-length-eng-strict:': 65,
        '--max-line-length-chn-strict:': 18,
        '--max-line-length-eng:': 72,
        '--max-line-length-chn:': 20,
    }
    word_re = r'-? ?(\w+)|( +)'

    def run(self, cmd, code):

        options = {}
        type_map = {
            'no-empty-cue': 1,
            'no-trailing-spaces': 1,
            'no-full-width-symbols': 1,
            'unexpected-spaces': 1,
            'no-brackets-in-eng-line': 1,
            'unformatted-dialog': 1,
            'max-line-length-eng': 1,
            'max-line-length-chn': 1,
            'max-line-length-eng-strict': 1,
            'max-line-length-chn-strict': 1
        }
        self.build_options(options, type_map)

        output = []
        errors = []
        warnings = []

        lines = code.splitlines()

        last_english_line = None

        # lint implementation
        for i in range(len(lines)):
            line = lines[i]
            line_type = check_line_type(line)
            message = None
            # errors
            # no empty lines within a single cue && one empty line expected before and after a single cue
            if i > 0:
                pre_line_type = check_line_type(lines[i - 1])
                if line_type == 'index' and pre_line_type != 'empty':
                    message = 'Empty line expected before idstring line.'
                elif line_type == 'empty' and pre_line_type not in ['embedded', 'english', 'unknown']:
                    message = 'No empty line(s) in a single cue.\n'
                elif line_type == pre_line_type:
                    message = '{} {}'.format('Multiple lines with same type: ', line_type)
                if message:
                    errors.append((i, 1, message))
            # no-empty-cue
            if line_type == 'timestamps' and check_line_type(lines[i + 1]) not in ['embedded', 'chinese', 'unknown']:
                message = 'Violates rule: no-empty-cue.'
                errors.append((i, 1, message))
            # no-trailing-spaces
            match_trailing_spaces = check_errors(line, regexps['trim'])
            if match_trailing_spaces:
                col = match_trailing_spaces.start('error')
                message = 'Unexpected spaces.'
                errors.append((i, col, message))
            # no-full-width-symbols
            match_full_width_symbols = check_errors(line, regexps['full_width_symbols'])
            if match_full_width_symbols:
                col = match_full_width_symbols.start('error')
                message = 'Full width symbol exists.'
                errors.append((i, col, message))
            if line_type == 'chinese':
                # max-line-length-chn-exceeded
                if len(line) > options['max-line-length-chn'] - 1:
                    message = 'Max line length exceeded. (Chinese, {} character limited but got {})'.format(options['max-line-length-chn'], len(line))
                    errors.append((i, 0, message))
                # max-line-length-chn-exceeded-strict
                elif len(line) > options['max-line-length-chn-strict'] - 1:
                    message = \
                        'Max line length exceeded. (Chinese, {} character limited but got {}, strict)'.format(options['max-line-length-chn-strict'], len(line))
                    warnings.append((i, 0, message))
                # unexpected-spaces
                match_unexpected_spaces_chn = check_errors(line, regexps['spaces_chn'])
                if match_unexpected_spaces_chn:
                    col = match_unexpected_spaces_chn.start('error')
                    message = 'Unexpected spaces in Chinese line.'
                    errors.append((i, col, message))
                # Chinese dialog
                if line.startswith('-'):
                    match_spaces_in_chn_dialog = check_errors(line, regexps['spaces_in_chn_dialog'])
                    if match_spaces_in_chn_dialog:
                        col = match_spaces_in_chn_dialog.start('error')
                        message = '2 spaces expected in Chinese dialog before \'-\'.'
                        errors.append((i, col, message))
                    match_unexpected_space_in_chn_dialog = \
                        check_errors(line, regexps['unexpected_space_in_chn_dialog'])
                    if match_unexpected_space_in_chn_dialog:
                        col = match_unexpected_space_in_chn_dialog.start('error')
                        message = 'No spaces between \'-\' and character.'
                        errors.append((i, col, message))
            elif line_type == 'english':
                # max-line-length-eng-exceeded
                if len(line) > options['max-line-length-eng'] - 1:
                    message = 'Max line length exceeded. (English, {} limited but got {})'.format(options['max-line-length-eng'], len(line))
                    errors.append((i, 0, message))
                # max-line-length-eng-exceeded-strict
                elif len(line) > options['max-line-length-eng-strict'] - 1:
                    message = \
                        'Max line length exceeded. (English, {} limited but got {}, strict)'.format(options['max-line-length-eng-strict'], len(line))
                    warnings.append((i, 0, message))
                # unexpected-spaces
                match_unexpected_spaces_eng = check_errors(line, regexps['spaces_eng'])
                if match_unexpected_spaces_eng:
                    col = match_unexpected_spaces_eng.start('error')
                    message = 'Unexpected spaces in English line.'
                    errors.append((i, col, message))
                # unexpected-spaces-before-symbol
                match_unexpected_spaces_before_symbol = check_errors(line, regexps['unexpected_space_before_symbol'])
                if match_unexpected_spaces_before_symbol:
                    col = match_unexpected_spaces_before_symbol.start('error')
                    message = 'Unexpected spaces before \',.;?!%\'.'
                    errors.append((i, col, message))
                # space-expected-after-symbol
                match_space_expected_after_symbol = check_errors(line, regexps['space_expected_after_symbol'])
                if match_space_expected_after_symbol:
                    col = match_space_expected_after_symbol.start('error')
                    message = 'Space expected after \',.?;!%\'.'
                    errors.append((i, col, message))
                # English dialog
                if line.startswith('-'):
                    match_space_in_eng_dialog = check_errors(line, regexps['space_in_eng_dialog'])
                    if match_space_in_eng_dialog:
                        col = match_space_in_eng_dialog.start('error')
                        message = '1 space expected in English dialog after \'-\''
                        errors.append((i, col, message))
                # no-brackets-in-line
                match_brackets_eng = check_errors(line, regexps['brackets_eng'])
                if match_brackets_eng:
                    col = match_brackets_eng.start('error')
                    message = 'Unexpected brackets in English line.'
                    errors.append((i, col, message))



            # warnings
            # potential-illegal-character
            if line_type in ['english', 'chinese']:
                match_potential_illegal_character = check_warnings(line, regexps['potential_illegal_characters'])
                if match_potential_illegal_character:
                    col = match_potential_illegal_character.start('warning')
                    message = 'Potential illegal character exists.'
                    warnings.append((i, col, message))
            # Check capitalization
            if line_type == 'english':
                match_capital_character = check_capitalization(line, regexps['capital_characters'])
                if last_english_line and lines[last_english_line][-1] in [',', '-', '%'] and match_capital_character:
                    col = match_capital_character.start('warning')
                    message = 'Check capitalization.'
                    warnings.append((i, col, message))
                # update english line index for checking next english line capitalization
                last_english_line = i;

        for error in errors:
            output.append('{}:{}: {} {}'.format(error[0] + 1, error[1] + 1, ERROR, error[2] + '\n'))
        for warning in warnings:
            output.append('{}:{}: {} {}'.format(warning[0] + 1, warning[1] + 1, WARNING, warning[2] + '\n'))
        return ''.join(output)


def check_line_type(line):
    """
    determine the type of one line: empty/index/timestamps/emebedded/chinese/english/unknown
    :param line: code to check
    :return: line_type: type of line
    """
    regexp_timestamps = re.compile(r'^((\d{2}:){2}\d{2},\d{3}\s-->\s(\d{2}:){2}\d{2},\d{3})$')
    regexp_embedded = re.compile(r'^{\\an\d+}.*$')
    regexp_zh_cn = re.compile(r'[\u4e00-\u9fa5]')
    regexp_en_us = re.compile(r'^[A-Za-z0-9,."!;?@#$^&+=~\'`/ *\-()\[\]{}<>]+$')
    regexp_index = re.compile(r'^\d+$')

    line_type = 'empty'
    if line:
        if re.match(regexp_timestamps, line):
            line_type = 'timestamps'
        elif re.match(regexp_embedded, line):
            line_type = 'embedded'
        elif re.match(regexp_index, line):
            line_type = 'index'
        elif re.search(regexp_zh_cn, line):
            line_type = 'chinese'
        elif re.match(regexp_en_us, line):
            line_type = 'english'
        else:
            line_type = 'unknown'
    return line_type

regexps = {
    'trim': '(^ +)|( +$)',
    'full_width_symbols': '[^\x00-\xff\u4e00-\u9fa5《》·]',
    'spaces_chn': '( ){3,}|((?<=[^\s]) (?=[\w\-"《]))',
    'spaces_eng': '(  +)',
    'brackets_eng': '[\[\]\(\)\<>/]',
    'spaces_in_chn_dialog': '\w+\-[\w+《"]',
    'unexpected_space_in_chn_dialog': '- +',
    'space_in_eng_dialog': '(?<!\w)-[\w"]+',
    'unexpected_space_before_symbol': '(\s+[,\.;?!%])',
    'space_expected_after_symbol': '[,?!;%][^\s]|(?<![\.A-Z])\.(?!\.\.)[^\s]',
    'potential_illegal_characters': '[~`@#$^&_+=\(\)\{\}\[\]:]',
    'capital_characters': '[A-Z]'
}


def check_errors(line, rstr):
    regexp = re.compile('(?P<error>{})'.format(rstr))
    return regexp.search(line)


def check_warnings(line, rstr):
    regexp = re.compile('(?P<warning>{})'.format(rstr))
    return regexp.search(line)

def check_capitalization(line, rstr):
    regexp = re.compile('(?P<warning>{})'.format(rstr))
    return regexp.match(line)

# TODO: special symbols: [:@#$%^&+=/]
