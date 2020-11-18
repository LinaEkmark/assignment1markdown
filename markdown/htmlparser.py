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

Copyright 2007-2020 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

License: BSD (see LICENSE.md for details).
"""

import re
import importlib
import sys


# Import a copy of the html.parser lib as `htmlparser` so we can monkeypatch it.
# Users can still do `from html import parser` and get the default behavior.
spec = importlib.util.find_spec('html.parser')
htmlparser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(htmlparser)
sys.modules['htmlparser'] = htmlparser

# Monkeypatch HTMLParser to only accept `?>` to close Processing Instructions.
htmlparser.piclose = re.compile(r'\?>')
# Monkeypatch HTMLParser to only recognize entity references with a closing semicolon.
htmlparser.entityref = re.compile(r'&([a-zA-Z][-.a-zA-Z0-9]*);')
# Monkeypatch HTMLParser to no longer support partial entities. We are always feeding a complete block,
# so the 'incomplete' functionality is unnecessary. As the entityref regex is run right before incomplete,
# and the two regex are the same, then incomplete will simply never match and we avoid the logic within.
htmlparser.incomplete = htmlparser.entityref

# Match a blank line at the start of a block of text (two newlines).
# The newlines may be preceded by additional whitespace.
blank_line_re = re.compile(r'^([ ]*\n){2}')


class HTMLExtractor(htmlparser.HTMLParser):
    """
    Extract raw HTML from text.

    The raw HTML is stored in the `htmlStash` of the Markdown instance passed
    to `md` and the remaining text is stored in `cleandoc` as a list of strings.
    """

    def __init__(self, md, *args, **kwargs):
        if 'convert_charrefs' not in kwargs:
            kwargs['convert_charrefs'] = False

        # Block tags that should contain no content (self closing)
        self.empty_tags = set(['hr'])

        # This calls self.reset
        super().__init__(*args, **kwargs)
        self.md = md

    def reset(self):
        """Reset this instance.  Loses all unprocessed data."""
        self.inraw = False
        self.intail = False
        self.stack = []  # When inraw==True, stack contains a list of tags
        self._cache = []
        self.cleandoc = []
        super().reset()

    def close(self):
        """Handle any buffered data."""
        super().close()
        if len(self.rawdata):
            # Temp fix for https://bugs.python.org/issue41989
            # TODO: remove this when the bug is fixed in all supported Python versions.
            if self.convert_charrefs and not self.cdata_elem:  # pragma: no cover
                self.handle_data(htmlparser.unescape(self.rawdata))
            else:
                self.handle_data(self.rawdata)
        # Handle any unclosed tags.
        if len(self._cache):
            self.cleandoc.append(self.md.htmlStash.store(''.join(self._cache)))
            self._cache = []

    @property
    def line_offset(self):
        """Returns char index in self.rawdata for the start of the current line. """
        if self.lineno > 1 and '\n' in self.rawdata:
            m = re.match(r'([^\n]*\n){{{}}}'.format(self.lineno-1), self.rawdata)
            if m:
                return m.end()
            else:  # pragma: no cover
                # Value of self.lineno must exceed total number of lines.
                # Find index of begining of last line.
                return self.rawdata.rfind('\n')
        return 0

    def at_line_start(self):
        """
        Returns True if current position is at start of line.

        Allows for up to three blank spaces at start of line.
        """
        if self.offset == 0:
            return True
        if self.offset > 3:
            return False
        # Confirm up to first 3 chars are whitespace
        return self.rawdata[self.line_offset:self.line_offset + self.offset].strip() == ''

    def get_endtag_text(self, tag):
        """
        Returns the text of the end tag.

        If it fails to extract the actual text from the raw data, it builds a closing tag with `tag`.
        """
        # Attempt to extract actual tag from raw source text
        start = self.line_offset + self.offset
        m = htmlparser.endendtag.search(self.rawdata, start)
        if m:
            return self.rawdata[start:m.end()]
        else:  # pragma: no cover
            # Failed to extract from raw data. Assume well formed and lowercase.
            return '</{}>'.format(tag)

    def handle_starttag(self, tag, attrs):
        # Handle tags that should always be empty and do not specify a closing tag
        if tag in self.empty_tags:
            self.handle_startendtag(tag, attrs)
            return

        if self.md.is_block_level(tag) and (self.intail or (self.at_line_start() and not self.inraw)):
            # Started a new raw block. Prepare stack.
            self.inraw = True
            self.cleandoc.append('\n')

        text = self.get_starttag_text()
        if self.inraw:
            self.stack.append(tag)
            self._cache.append(text)
        else:
            self.cleandoc.append(text)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                # This is presumably a standalone tag in a code span (see #1036).
                self.clear_cdata_mode()

    def handle_endtag(self, tag):
        text = self.get_endtag_text(tag)

        if self.inraw:
            self._cache.append(text)
            if tag in self.stack:
                # Remove tag from stack
                while self.stack:
                    if self.stack.pop() == tag:
                        break
            if len(self.stack) == 0:
                # End of raw block.
                if blank_line_re.match(self.rawdata[self.line_offset + self.offset + len(text):]):
                    # Preserve blank line and end of raw block.
                    self._cache.append('\n')
                else:
                    # More content exists after endtag.
                    self.intail = True
                # Reset stack.
                self.inraw = False
                self.cleandoc.append(self.md.htmlStash.store(''.join(self._cache)))
                # Insert blank line between this and next line.
                self.cleandoc.append('\n\n')
                self._cache = []
        else:
            self.cleandoc.append(text)

    def handle_data(self, data):
        if self.intail and '\n' in data:
            self.intail = False
        if self.inraw:
            self._cache.append(data)
        else:
            self.cleandoc.append(data)

    def handle_empty_tag(self, data, is_block):
        """ Handle empty tags (`<data>`). """
        if self.inraw or self.intail:
            # Append this to the existing raw block
            self._cache.append(data)
        elif self.at_line_start() and is_block:
            # Handle this as a standalone raw block
            if blank_line_re.match(self.rawdata[self.line_offset + self.offset + len(data):]):
                # Preserve blank line after tag in raw block.
                data += '\n'
            else:
                # More content exists after tag.
                self.intail = True
            item = self.cleandoc[-1] if self.cleandoc else ''
            # If we only have one newline before block element, add another
            if not item.endswith('\n\n') and item.endswith('\n'):
                self.cleandoc.append('\n')
            self.cleandoc.append(self.md.htmlStash.store(data))
            # Insert blank line between this and next line.
            self.cleandoc.append('\n\n')
        else:
            self.cleandoc.append(data)

    def handle_startendtag(self, tag, attrs):
        self.handle_empty_tag(self.get_starttag_text(), is_block=self.md.is_block_level(tag))

    def handle_charref(self, name):
        self.handle_empty_tag('&#{};'.format(name), is_block=False)

    def handle_entityref(self, name):
        self.handle_empty_tag('&{};'.format(name), is_block=False)

    def handle_comment(self, data):
        self.handle_empty_tag('<!--{}-->'.format(data), is_block=True)

    def handle_decl(self, data):
        self.handle_empty_tag('<!{}>'.format(data), is_block=True)

    def handle_pi(self, data):
        self.handle_empty_tag('<?{}?>'.format(data), is_block=True)

    def unknown_decl(self, data):
        end = ']]>' if data.startswith('CDATA[') else ']>'
        self.handle_empty_tag('<![{}{}'.format(data, end), is_block=True)

    # The rest has been copied from base class in standard lib to address #1036.
    # As __startag_text is private, all references to it must be in this subclass.
    # The last few lines of parse_starttag are reversed so that handle_starttag
    # can override cdata_mode in certain situations (in a code span).
    __starttag_text = None

    def get_starttag_text(self):
        """Return full source of start tag: '<...>'."""
        return self.__starttag_text

    def parse_starttag(self, i):  # pragma: no cover
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = htmlparser.tagfind_tolerant.match(rawdata, i+1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = match.group(1).lower()
        while k < endpos:
            m = htmlparser.attrfind_tolerant.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                 attrvalue[:1] == '"' == attrvalue[-1:]:  # noqa: E127
                attrvalue = attrvalue[1:-1]
            if attrvalue:
                attrvalue = htmlparser.unescape(attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = m.end()

        end = rawdata[k:endpos].strip()
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) \
                         - self.__starttag_text.rfind("\n")  # noqa: E127
            else:
                offset = offset + len(self.__starttag_text)
            self.handle_data(rawdata[i:endpos])
            return endpos
        if end.endswith('/>'):
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            # *** set cdata_mode first so we can override it in handle_starttag (see #1036) ***
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode(tag)
            self.handle_starttag(tag, attrs)
        return endpos
