"""
Python Markdown

A Python implementation of John Gruber's Markdown.

Documentation: https://python-markdown.github.io/
GitHub: https://github.com/Python-Markdown/markdown/
PyPI: https://pypi.org/project/Markdown/

Started by Manfred Stienstra (http://www.dwerg.net/).
Maintained for a few years by Yuri Takhteyev (http://www.freewisdom.org).
Currently maintained by Waylan Limberg (https://github.com/waylan),
Dmitry Shachnev (https://github.com/mitya57) and Isaac Muse (https://github.com/facelessuser).

Copyright 2007-2018 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

License: BSD (see LICENSE.md for details).
"""

import sys
import optparse
import codecs
import warnings
import markdown
try:
    # We use `unsafe_load` because users may need to pass in actual Python
    # objects. As this is only available from the CLI, the user has much
    # worse problems if an attacker can use this as an attach vector.
    from yaml import unsafe_load as yaml_load
except ImportError:  # pragma: no cover
    try:
        # Fall back to PyYAML <5.1
        from yaml import load as yaml_load
    except ImportError:
        # Fall back to JSON
        from json import load as yaml_load

import logging
from logging import DEBUG, WARNING, CRITICAL

logger = logging.getLogger('MARKDOWN')


def parse_options(args=None, values=None):
    """
    Define and parse `optparse` options for command-line usage.
    """
    usage = """%prog [options] [INPUTFILE]
       (STDIN is assumed if no INPUTFILE is given)"""
    desc = "A Python implementation of John Gruber's Markdown. " \
           "https://Python-Markdown.github.io/"
    ver = f"%prog {markdown.__version__}"

    parser = optparse.OptionParser(usage=usage, description=desc, version=ver)
    parser.add_option("-f", "--file", dest="filename", default=None,
                      help="Write output to OUTPUT_FILE. Defaults to STDOUT.",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="Encoding for input and output files.",)
    parser.add_option("-o", "--output_format", dest="output_format",
                      default='xhtml', metavar="OUTPUT_FORMAT",
                      help="Use output format 'xhtml' (default) or 'html'.")
    parser.add_option("-n", "--no_lazy_ol", dest="lazy_ol",
                      action='store_false', default=True,
                      help="Observe number of first item of ordered lists.")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help="Load extension EXTENSION.", metavar="EXTENSION")
    parser.add_option("-c", "--extension_configs",
                      dest="configfile", default=None,
                      help="Read extension configurations from CONFIG_FILE. "
                      "CONFIG_FILE must be of JSON or YAML format. YAML "
                      "format requires that a python YAML library be "
                      "installed. The parsed JSON or YAML must result in a "
                      "python dictionary which would be accepted by the "
                      "'extension_configs' keyword on the markdown.Markdown "
                      "class. The extensions must also be loaded with the "
                      "`--extension` option.",
                      metavar="CONFIG_FILE")
    parser.add_option("-q", "--quiet", default=CRITICAL,
                      action="store_const", const=CRITICAL+10, dest="verbose",
                      help="Suppress all warnings.")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=WARNING, dest="verbose",
                      help="Print all warnings.")
    parser.add_option("--noisy",
                      action="store_const", const=DEBUG, dest="verbose",
                      help="Print debug messages.")

    (options, args) = parser.parse_args(args, values)

    if len(args) == 0:
        input_file = None
    else:
        input_file = args[0]

    if not options.extensions:
        options.extensions = []

    extension_configs = {}
    if options.configfile:
        with codecs.open(
            options.configfile, mode="r", encoding=options.encoding
        ) as fp:
            try:
                extension_configs = yaml_load(fp)
            except Exception as e:
                message = f"Failed parsing extension config file: {options.configfile}"
                e.args = (message,) + e.args[1:]
                raise

    opts = {
        'input': input_file,
        'output': options.filename,
        'extensions': options.extensions,
        'extension_configs': extension_configs,
        'encoding': options.encoding,
        'output_format': options.output_format,
        'lazy_ol': options.lazy_ol
    }

    return opts, options.verbose


def run():  # pragma: no cover
    """Run Markdown from the command line."""

    # Parse options and adjust logging level if necessary
    options, logging_level = parse_options()
    if not options:
        sys.exit(2)
    logger.setLevel(logging_level)
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)
    if logging_level <= WARNING:
        # Ensure deprecation warnings get displayed
        warnings.filterwarnings('default')
        logging.captureWarnings(True)
        warn_logger = logging.getLogger('py.warnings')
        warn_logger.addHandler(console_handler)

    # Run
    markdown.markdownFromFile(**options)


if __name__ == '__main__':  # pragma: no cover
    # Support running module as a commandline command.
    # `python -m markdown [options] [args]`.
    run()
