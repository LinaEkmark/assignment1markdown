#!/usr/bin/python
"""
Python-Markdown Regression Tests
================================

Tests of the various APIs with the python markdown lib.

"""

from __future__ import unicode_literals
import unittest
import sys
import os
import markdown
import warnings
from markdown.__main__ import parse_options
from logging import DEBUG, WARNING, CRITICAL
import yaml
import tempfile
from io import BytesIO
from xml.etree.ElementTree import ProcessingInstruction


PY3 = sys.version_info[0] == 3


if not PY3:
    def bytes(string, encoding):
        return string.encode(encoding)


class TestMarkdownBasics(unittest.TestCase):
    """ Tests basics of the Markdown class. """

    def setUp(self):
        """ Create instance of Markdown. """
        self.md = markdown.Markdown()

    def testBlankInput(self):
        """ Test blank input. """
        self.assertEqual(self.md.convert(''), '')

    def testWhitespaceOnly(self):
        """ Test input of only whitespace. """
        self.assertEqual(self.md.convert(' '), '')

    def testSimpleInput(self):
        """ Test simple input. """
        self.assertEqual(self.md.convert('foo'), '<p>foo</p>')

    def testInstanceExtension(self):
        """ Test Extension loading with a class instance. """
        from markdown.extensions.footnotes import FootnoteExtension
        markdown.Markdown(extensions=[FootnoteExtension()])

    def testEntryPointExtension(self):
        """ Test Extension loading with an entry point. """
        markdown.Markdown(extensions=['footnotes'])

    def testDotNotationExtension(self):
        """ Test Extension loading with Name (`path.to.module`). """
        markdown.Markdown(extensions=['markdown.extensions.footnotes'])

    def testDotNotationExtensionWithClass(self):
        """ Test Extension loading with class name (`path.to.module:Class`). """
        markdown.Markdown(extensions=['markdown.extensions.footnotes:FootnoteExtension'])


class TestConvertFile(unittest.TestCase):
    """ Tests of ConvertFile. """

    def setUp(self):
        self.saved = sys.stdin, sys.stdout
        sys.stdin = BytesIO(bytes('foo', encoding='utf-8'))
        sys.stdout = BytesIO()

    def tearDown(self):
        sys.stdin, sys.stdout = self.saved

    def getTempFiles(self, src):
        """ Return the file names for two temp files. """
        infd, infile = tempfile.mkstemp(suffix='.txt')
        with os.fdopen(infd, 'w') as fp:
            fp.write(src)
        outfd, outfile = tempfile.mkstemp(suffix='.html')
        return infile, outfile, outfd

    def testFileNames(self):
        infile, outfile, outfd = self.getTempFiles('foo')
        markdown.markdownFromFile(input=infile, output=outfile)
        with os.fdopen(outfd, 'r') as fp:
            output = fp.read()
        self.assertEqual(output, '<p>foo</p>')

    def testFileObjects(self):
        infile = BytesIO(bytes('foo', encoding='utf-8'))
        outfile = BytesIO()
        markdown.markdownFromFile(input=infile, output=outfile)
        outfile.seek(0)
        self.assertEqual(outfile.read().decode('utf-8'), '<p>foo</p>')

    def testStdinStdout(self):
        markdown.markdownFromFile()
        sys.stdout.seek(0)
        self.assertEqual(sys.stdout.read().decode('utf-8'), '<p>foo</p>')


class TestBlockParser(unittest.TestCase):
    """ Tests of the BlockParser class. """

    def setUp(self):
        """ Create instance of BlockParser. """
        self.parser = markdown.Markdown().parser

    def testParseChunk(self):
        """ Test BlockParser.parseChunk. """
        root = markdown.util.etree.Element("div")
        text = 'foo'
        self.parser.parseChunk(root, text)
        self.assertEqual(
            markdown.serializers.to_xhtml_string(root),
            "<div><p>foo</p></div>"
        )

    def testParseDocument(self):
        """ Test BlockParser.parseDocument. """
        lines = ['#foo', '', 'bar', '', '    baz']
        tree = self.parser.parseDocument(lines)
        self.assertTrue(isinstance(tree, markdown.util.etree.ElementTree))
        self.assertTrue(markdown.util.etree.iselement(tree.getroot()))
        self.assertEqual(
            markdown.serializers.to_xhtml_string(tree.getroot()),
            "<div><h1>foo</h1><p>bar</p><pre><code>baz\n</code></pre></div>"
        )


class TestBlockParserState(unittest.TestCase):
    """ Tests of the State class for BlockParser. """

    def setUp(self):
        self.state = markdown.blockparser.State()

    def testBlankState(self):
        """ Test State when empty. """
        self.assertEqual(self.state, [])

    def testSetSate(self):
        """ Test State.set(). """
        self.state.set('a_state')
        self.assertEqual(self.state, ['a_state'])
        self.state.set('state2')
        self.assertEqual(self.state, ['a_state', 'state2'])

    def testIsSate(self):
        """ Test State.isstate(). """
        self.assertEqual(self.state.isstate('anything'), False)
        self.state.set('a_state')
        self.assertEqual(self.state.isstate('a_state'), True)
        self.state.set('state2')
        self.assertEqual(self.state.isstate('state2'), True)
        self.assertEqual(self.state.isstate('a_state'), False)
        self.assertEqual(self.state.isstate('missing'), False)

    def testReset(self):
        """ Test State.reset(). """
        self.state.set('a_state')
        self.state.reset()
        self.assertEqual(self.state, [])
        self.state.set('state1')
        self.state.set('state2')
        self.state.reset()
        self.assertEqual(self.state, ['state1'])


class TestHtmlStash(unittest.TestCase):
    """ Test Markdown's HtmlStash. """

    def setUp(self):
        self.stash = markdown.util.HtmlStash()
        self.placeholder = self.stash.store('foo')

    def testSimpleStore(self):
        """ Test HtmlStash.store. """
        self.assertEqual(self.placeholder, self.stash.get_placeholder(0))
        self.assertEqual(self.stash.html_counter, 1)
        self.assertEqual(self.stash.rawHtmlBlocks, ['foo'])

    def testStoreMore(self):
        """ Test HtmlStash.store with additional blocks. """
        placeholder = self.stash.store('bar')
        self.assertEqual(placeholder, self.stash.get_placeholder(1))
        self.assertEqual(self.stash.html_counter, 2)
        self.assertEqual(
            self.stash.rawHtmlBlocks,
            ['foo', 'bar']
        )

    def testReset(self):
        """ Test HtmlStash.reset. """
        self.stash.reset()
        self.assertEqual(self.stash.html_counter, 0)
        self.assertEqual(self.stash.rawHtmlBlocks, [])


class Item(object):
    """ A dummy Registry item object for testing. """
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return repr(self.data)

    def __eq__(self, other):
        return self.data == other


class RegistryTests(unittest.TestCase):
    """ Test the processor registry. """

    def testCreateRegistry(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        self.assertEqual(len(r), 1)
        self.assertTrue(isinstance(r, markdown.util.Registry))

    def testRegisterWithoutPriority(self):
        r = markdown.util.Registry()
        with self.assertRaises(TypeError):
            r.register(Item('a'))

    def testSortRegistry(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        r.register(Item('b'), 'b', 21)
        r.register(Item('c'), 'c', 20.5)
        self.assertEqual(len(r), 3)
        self.assertEqual(list(r), ['b', 'c', 'a'])

    def testIsSorted(self):
        r = markdown.util.Registry()
        self.assertFalse(r._is_sorted)
        r.register(Item('a'), 'a', 20)
        list(r)
        self.assertTrue(r._is_sorted)
        r.register(Item('b'), 'b', 21)
        self.assertFalse(r._is_sorted)
        r['a']
        self.assertTrue(r._is_sorted)
        r._is_sorted = False
        r.get_index_for_name('a')
        self.assertTrue(r._is_sorted)
        r._is_sorted = False
        repr(r)
        self.assertTrue(r._is_sorted)

    def testDeregister(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a',  20)
        r.register(Item('b'), 'b', 30)
        r.register(Item('c'), 'c', 40)
        self.assertEqual(len(r), 3)
        r.deregister('b')
        self.assertEqual(len(r), 2)
        r.deregister('c', strict=False)
        self.assertEqual(len(r), 1)
        # deregister non-existant item with strict=False
        r.deregister('d', strict=False)
        self.assertEqual(len(r), 1)
        with self.assertRaises(ValueError):
            # deregister non-existant item with strict=True
            r.deregister('e')
        self.assertEqual(list(r), ['a'])

    def testRegistryContains(self):
        r = markdown.util.Registry()
        item = Item('a')
        r.register(item, 'a', 20)
        self.assertTrue('a' in r)
        self.assertTrue(item in r)
        self.assertFalse('b' in r)

    def testRegistryIter(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        r.register(Item('b'), 'b', 30)
        self.assertEqual(list(r), ['b', 'a'])

    def testRegistryGetItemByIndex(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        r.register(Item('b'), 'b', 30)
        self.assertEqual(r[0], 'b')
        self.assertEqual(r[1], 'a')
        with self.assertRaises(IndexError):
            r[3]

    def testRegistryGetItemByItem(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        r.register(Item('b'), 'b', 30)
        self.assertEqual(r['a'], 'a')
        self.assertEqual(r['b'], 'b')
        with self.assertRaises(KeyError):
            r['c']

    def testRegistrySetItem(self):
        r = markdown.util.Registry()
        with self.assertRaises(TypeError):
            r[0] = 'a'
        # TODO: restore this when deprecated __setitem__ is removed.
        # with self.assertRaises(TypeError):
        #     r['a'] = 'a'
        # TODO: remove this when deprecated __setitem__ is removed.
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            r['a'] = Item('a')
            self.assertEqual(list(r), ['a'])
            r['b'] = Item('b')
            self.assertEqual(list(r), ['a', 'b'])

            # Check the warnings
            self.assertEqual(len(w), 2)
            self.assertTrue(all(issubclass(x.category, DeprecationWarning) for x in w))

    def testRegistryDelItem(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        with self.assertRaises(TypeError):
            del r[0]
        # TODO: restore this when deprecated __del__ is removed.
        # with self.assertRaises(TypeError):
        #     del r['a']
        # TODO: remove this when deprecated __del__ is removed.
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            r.register(Item('b'), 'b', 15)
            r.register(Item('c'), 'c', 10)
            del r['b']
            self.assertEqual(list(r), ['a', 'c'])
            del r['a']
            self.assertEqual(list(r), ['c'])
            with self.assertRaises(TypeError):
                del r['badname']
            del r['c']
            self.assertEqual(list(r), [])

            # Check the warnings
            self.assertEqual(len(w), 3)
            self.assertTrue(all(issubclass(x.category, DeprecationWarning) for x in w))

    def testRegistrySlice(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        r.register(Item('b'), 'b', 30)
        r.register(Item('c'), 'c', 40)
        slc = r[1:]
        self.assertEqual(len(slc), 2)
        self.assertTrue(isinstance(slc, markdown.util.Registry))
        self.assertEqual(list(slc), ['b', 'a'])

    def testGetIndexForName(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        r.register(Item('b'), 'b', 30)
        self.assertEqual(r.get_index_for_name('a'), 1)
        self.assertEqual(r.get_index_for_name('b'), 0)
        with self.assertRaises(ValueError):
            r.get_index_for_name('c')

    def testRegisterDupplicate(self):
        r = markdown.util.Registry()
        r.register(Item('a'), 'a', 20)
        r.register(Item('b1'), 'b', 10)
        self.assertEqual(list(r), ['a', 'b1'])
        self.assertEqual(len(r), 2)
        r.register(Item('b2'), 'b', 30)
        self.assertEqual(len(r), 2)
        self.assertEqual(list(r), ['b2', 'a'])

    def testRegistryDeprecatedAdd(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            r = markdown.util.Registry()
            # Add first item
            r.add('c', Item('c'), '_begin')
            self.assertEqual(list(r), ['c'])
            # Added to beginning
            r.add('b', Item('b'), '_begin')
            self.assertEqual(list(r), ['b', 'c'])
            # Add before first item
            r.add('a', Item('a'), '<b')
            self.assertEqual(list(r), ['a', 'b', 'c'])
            # Add before non-first item
            r.add('a1', Item('a1'), '<b')
            self.assertEqual(list(r), ['a', 'a1', 'b', 'c'])
            # Add after non-last item
            r.add('b1', Item('b1'), '>b')
            self.assertEqual(list(r), ['a', 'a1', 'b', 'b1', 'c'])
            # Add after last item
            r.add('d', Item('d'), '>c')
            self.assertEqual(list(r), ['a', 'a1', 'b', 'b1', 'c', 'd'])
            # Add to end
            r.add('e', Item('e'), '_end')
            self.assertEqual(list(r), ['a', 'a1', 'b', 'b1', 'c', 'd', 'e'])

            # Check the warnings
            self.assertEqual(len(w), 7)
            self.assertTrue(all(issubclass(x.category, DeprecationWarning) for x in w))


class TestErrors(unittest.TestCase):
    """ Test Error Reporting. """

    def setUp(self):
        # Set warnings to be raised as errors
        warnings.simplefilter('error')

    def tearDown(self):
        # Reset warning behavior back to default
        warnings.simplefilter('default')

    def testNonUnicodeSource(self):
        """ Test falure on non-unicode source text. """
        if not PY3:
            source = "foo".encode('utf-16')
            self.assertRaises(UnicodeDecodeError, markdown.markdown, source)

    def testBadOutputFormat(self):
        """ Test failure on bad output_format. """
        self.assertRaises(KeyError, markdown.Markdown, output_format='invalid')

    def testLoadExtensionFailure(self):
        """ Test failure of an extension to load. """
        self.assertRaises(
            ImportError,
            markdown.Markdown, extensions=['non_existant_ext']
        )

    def testLoadBadExtension(self):
        """ Test loading of an Extension with no makeExtension function. """
        self.assertRaises(AttributeError, markdown.Markdown, extensions=['markdown.util'])

    def testNonExtension(self):
        """ Test loading a non Extension object as an extension. """
        self.assertRaises(TypeError, markdown.Markdown, extensions=[object])

    def testDotNotationExtensionWithBadClass(self):
        """ Test Extension loading with non-existant class name (`path.to.module:Class`). """
        self.assertRaises(
            AttributeError,
            markdown.Markdown,
            extensions=['markdown.extensions.footnotes:MissingExtension']
        )

    def testBaseExtention(self):
        """ Test that the base Extension class will raise NotImplemented. """
        self.assertRaises(
            NotImplementedError,
            markdown.Markdown, extensions=[markdown.extensions.Extension()]
        )


class testETreeComments(unittest.TestCase):
    """
    Test that ElementTree Comments work.

    These tests should only be a concern when using cElementTree with third
    party serializers (including markdown's (x)html serializer). While markdown
    doesn't use ElementTree.Comment itself, we should certainly support any
    third party extensions which may. Therefore, these tests are included to
    ensure such support is maintained.
    """

    def setUp(self):
        # Create comment node
        self.comment = markdown.util.etree.Comment('foo')
        if hasattr(markdown.util.etree, 'test_comment'):
            self.test_comment = markdown.util.etree.test_comment
        else:
            self.test_comment = markdown.util.etree.Comment

    def testCommentIsComment(self):
        """ Test that an ElementTree Comment passes the `is Comment` test. """
        self.assertTrue(self.comment.tag is markdown.util.etree.test_comment)

    def testCommentIsBlockLevel(self):
        """ Test that an ElementTree Comment is recognized as BlockLevel. """
        self.assertFalse(markdown.util.isBlockLevel(self.comment.tag))

    def testCommentSerialization(self):
        """ Test that an ElementTree Comment serializes properly. """
        self.assertEqual(
            markdown.serializers.to_html_string(self.comment),
            '<!--foo-->'
        )

    def testCommentPrettify(self):
        """ Test that an ElementTree Comment is prettified properly. """
        pretty = markdown.treeprocessors.PrettifyTreeprocessor()
        pretty.run(self.comment)
        self.assertEqual(
            markdown.serializers.to_html_string(self.comment),
            '<!--foo-->\n'
        )


class testElementTailTests(unittest.TestCase):
    """ Element Tail Tests """
    def setUp(self):
        self.pretty = markdown.treeprocessors.PrettifyTreeprocessor()

    def testBrTailNoNewline(self):
        """ Test that last <br> in tree has a new line tail """
        root = markdown.util.etree.Element('root')
        br = markdown.util.etree.SubElement(root, 'br')
        self.assertEqual(br.tail, None)
        self.pretty.run(root)
        self.assertEqual(br.tail, "\n")


class testSerializers(unittest.TestCase):
    """ Test the html and xhtml serializers. """

    def testHtml(self):
        """ Test HTML serialization. """
        el = markdown.util.etree.Element('div')
        el.set('id', 'foo<&">')
        p = markdown.util.etree.SubElement(el, 'p')
        p.text = 'foo <&escaped>'
        p.set('hidden', 'hidden')
        markdown.util.etree.SubElement(el, 'hr')
        non_element = markdown.util.etree.SubElement(el, None)
        non_element.text = 'non-element text'
        script = markdown.util.etree.SubElement(non_element, 'script')
        script.text = '<&"test\nescaping">'
        el.tail = "tail text"
        self.assertEqual(
            markdown.serializers.to_html_string(el),
            '<div id="foo&lt;&amp;&quot;&gt;">'
            '<p hidden>foo &lt;&amp;escaped&gt;</p>'
            '<hr>'
            'non-element text'
            '<script><&"test\nescaping"></script>'
            '</div>tail text'
        )

    def testXhtml(self):
        """" Test XHTML serialization. """
        el = markdown.util.etree.Element('div')
        el.set('id', 'foo<&">')
        p = markdown.util.etree.SubElement(el, 'p')
        p.text = 'foo<&escaped>'
        p.set('hidden', 'hidden')
        markdown.util.etree.SubElement(el, 'hr')
        non_element = markdown.util.etree.SubElement(el, None)
        non_element.text = 'non-element text'
        script = markdown.util.etree.SubElement(non_element, 'script')
        script.text = '<&"test\nescaping">'
        el.tail = "tail text"
        self.assertEqual(
            markdown.serializers.to_xhtml_string(el),
            '<div id="foo&lt;&amp;&quot;&gt;">'
            '<p hidden="hidden">foo&lt;&amp;escaped&gt;</p>'
            '<hr />'
            'non-element text'
            '<script><&"test\nescaping"></script>'
            '</div>tail text'
        )

    def testMixedCaseTags(self):
        """" Test preservation of tag case. """
        el = markdown.util.etree.Element('MixedCase')
        el.text = 'not valid '
        em = markdown.util.etree.SubElement(el, 'EMPHASIS')
        em.text = 'html'
        markdown.util.etree.SubElement(el, 'HR')
        self.assertEqual(
            markdown.serializers.to_xhtml_string(el),
            '<MixedCase>not valid <EMPHASIS>html</EMPHASIS><HR /></MixedCase>'
        )

    def testProsessingInstruction(self):
        """ Test serialization of ProcessignInstruction. """
        pi = ProcessingInstruction('foo', text='<&"test\nescaping">')
        self.assertIs(pi.tag, ProcessingInstruction)
        self.assertEqual(
            markdown.serializers.to_xhtml_string(pi),
            '<?foo &lt;&amp;"test\nescaping"&gt;?>'
        )

    def testQNameTag(self):
        """ Test serialization of QName tag. """
        div = markdown.util.etree.Element('div')
        qname = markdown.util.etree.QName('http://www.w3.org/1998/Math/MathML', 'math')
        math = markdown.util.etree.SubElement(div, qname)
        math.set('display', 'block')
        sem = markdown.util.etree.SubElement(math, 'semantics')
        msup = markdown.util.etree.SubElement(sem, 'msup')
        mi = markdown.util.etree.SubElement(msup, 'mi')
        mi.text = 'x'
        mn = markdown.util.etree.SubElement(msup, 'mn')
        mn.text = '2'
        ann = markdown.util.etree.SubElement(sem, 'annotations')
        ann.text = 'x^2'
        self.assertEqual(
            markdown.serializers.to_xhtml_string(div),
            '<div>'
            '<math display="block" xmlns="http://www.w3.org/1998/Math/MathML">'
            '<semantics>'
            '<msup>'
            '<mi>x</mi>'
            '<mn>2</mn>'
            '</msup>'
            '<annotations>x^2</annotations>'
            '</semantics>'
            '</math>'
            '</div>'
        )

    def testQNameAttribute(self):
        """ Test serialization of QName attribute. """
        div = markdown.util.etree.Element('div')
        div.set(markdown.util.etree.QName('foo'), markdown.util.etree.QName('bar'))
        self.assertEqual(
            markdown.serializers.to_xhtml_string(div),
            '<div foo="bar"></div>'
        )

    def testBadQNameTag(self):
        """ Test serialization of QName with no tag. """
        qname = markdown.util.etree.QName('http://www.w3.org/1998/Math/MathML')
        el = markdown.util.etree.Element(qname)
        self.assertRaises(ValueError, markdown.serializers.to_xhtml_string, el)

    def testQNameEscaping(self):
        """ Test QName escaping. """
        qname = markdown.util.etree.QName('<&"test\nescaping">', 'div')
        el = markdown.util.etree.Element(qname)
        self.assertEqual(
            markdown.serializers.to_xhtml_string(el),
            '<div xmlns="&lt;&amp;&quot;test&#10;escaping&quot;&gt;"></div>'
        )

    def buildExtension(self):
        """ Build an extension which registers fakeSerializer. """
        def fakeSerializer(elem):
            # Ignore input and return hardcoded output
            return '<div><p>foo</p></div>'

        class registerFakeSerializer(markdown.extensions.Extension):
            def extendMarkdown(self, md, md_globals):
                md.output_formats['fake'] = fakeSerializer

        return registerFakeSerializer()

    def testRegisterSerializer(self):
        self.assertEqual(
            markdown.markdown(
                'baz', extensions=[self.buildExtension()], output_format='fake'
            ),
            '<p>foo</p>'
        )


class testAtomicString(unittest.TestCase):
    """ Test that AtomicStrings are honored (not parsed). """

    def setUp(self):
        md = markdown.Markdown()
        self.inlineprocessor = md.treeprocessors['inline']

    def testString(self):
        """ Test that a regular string is parsed. """
        tree = markdown.util.etree.Element('div')
        p = markdown.util.etree.SubElement(tree, 'p')
        p.text = 'some *text*'
        new = self.inlineprocessor.run(tree)
        self.assertEqual(
            markdown.serializers.to_html_string(new),
            '<div><p>some <em>text</em></p></div>'
        )

    def testSimpleAtomicString(self):
        """ Test that a simple AtomicString is not parsed. """
        tree = markdown.util.etree.Element('div')
        p = markdown.util.etree.SubElement(tree, 'p')
        p.text = markdown.util.AtomicString('some *text*')
        new = self.inlineprocessor.run(tree)
        self.assertEqual(
            markdown.serializers.to_html_string(new),
            '<div><p>some *text*</p></div>'
        )

    def testNestedAtomicString(self):
        """ Test that a nested AtomicString is not parsed. """
        tree = markdown.util.etree.Element('div')
        p = markdown.util.etree.SubElement(tree, 'p')
        p.text = markdown.util.AtomicString('*some* ')
        span1 = markdown.util.etree.SubElement(p, 'span')
        span1.text = markdown.util.AtomicString('*more* ')
        span2 = markdown.util.etree.SubElement(span1, 'span')
        span2.text = markdown.util.AtomicString('*text* ')
        span3 = markdown.util.etree.SubElement(span2, 'span')
        span3.text = markdown.util.AtomicString('*here*')
        span3.tail = markdown.util.AtomicString(' *to*')
        span2.tail = markdown.util.AtomicString(' *test*')
        span1.tail = markdown.util.AtomicString(' *with*')
        new = self.inlineprocessor.run(tree)
        self.assertEqual(
            markdown.serializers.to_html_string(new),
            '<div><p>*some* <span>*more* <span>*text* <span>*here*</span> '
            '*to*</span> *test*</span> *with*</p></div>'
        )


class TestConfigParsing(unittest.TestCase):
    def assertParses(self, value, result):
        self.assertTrue(markdown.util.parseBoolValue(value, False) is result)

    def testBooleansParsing(self):
        self.assertParses(True, True)
        self.assertParses('novalue', None)
        self.assertParses('yES', True)
        self.assertParses('FALSE', False)
        self.assertParses(0., False)
        self.assertParses('none', False)

    def testPreserveNone(self):
        self.assertTrue(markdown.util.parseBoolValue('None', preserve_none=True) is None)
        self.assertTrue(markdown.util.parseBoolValue(None, preserve_none=True) is None)

    def testInvalidBooleansParsing(self):
        self.assertRaises(ValueError, markdown.util.parseBoolValue, 'novalue')


class TestCliOptionParsing(unittest.TestCase):
    """ Test parsing of Command Line Interface Options. """

    def setUp(self):
        self.default_options = {
            'input': None,
            'output': None,
            'encoding': None,
            'output_format': 'xhtml',
            'lazy_ol': True,
            'extensions': [],
            'extension_configs': {},
        }
        self.tempfile = ''

    def tearDown(self):
        if os.path.isfile(self.tempfile):
            os.remove(self.tempfile)

    def testNoOptions(self):
        options, logging_level = parse_options([])
        self.assertEqual(options, self.default_options)
        self.assertEqual(logging_level, CRITICAL)

    def testQuietOption(self):
        options, logging_level = parse_options(['-q'])
        self.assertTrue(logging_level > CRITICAL)

    def testVerboseOption(self):
        options, logging_level = parse_options(['-v'])
        self.assertEqual(logging_level, WARNING)

    def testNoisyOption(self):
        options, logging_level = parse_options(['--noisy'])
        self.assertEqual(logging_level, DEBUG)

    def testInputFileOption(self):
        options, logging_level = parse_options(['foo.txt'])
        self.default_options['input'] = 'foo.txt'
        self.assertEqual(options, self.default_options)

    def testOutputFileOption(self):
        options, logging_level = parse_options(['-f', 'foo.html'])
        self.default_options['output'] = 'foo.html'
        self.assertEqual(options, self.default_options)

    def testInputAndOutputFileOptions(self):
        options, logging_level = parse_options(['-f', 'foo.html', 'foo.txt'])
        self.default_options['output'] = 'foo.html'
        self.default_options['input'] = 'foo.txt'
        self.assertEqual(options, self.default_options)

    def testEncodingOption(self):
        options, logging_level = parse_options(['-e', 'utf-8'])
        self.default_options['encoding'] = 'utf-8'
        self.assertEqual(options, self.default_options)

    def testOutputFormatOption(self):
        options, logging_level = parse_options(['-o', 'html'])
        self.default_options['output_format'] = 'html'
        self.assertEqual(options, self.default_options)

    def testNoLazyOlOption(self):
        options, logging_level = parse_options(['-n'])
        self.default_options['lazy_ol'] = False
        self.assertEqual(options, self.default_options)

    def testExtensionOption(self):
        options, logging_level = parse_options(['-x', 'markdown.extensions.footnotes'])
        self.default_options['extensions'] = ['markdown.extensions.footnotes']
        self.assertEqual(options, self.default_options)

    def testMultipleExtensionOptions(self):
        options, logging_level = parse_options([
            '-x', 'markdown.extensions.footnotes',
            '-x', 'markdown.extensions.smarty'
        ])
        self.default_options['extensions'] = [
            'markdown.extensions.footnotes',
            'markdown.extensions.smarty'
        ]
        self.assertEqual(options, self.default_options)

    def create_config_file(self, config):
        """ Helper to create temp config files. """
        if not isinstance(config, markdown.util.string_type):
            # convert to string
            config = yaml.dump(config)
        fd, self.tempfile = tempfile.mkstemp('.yml')
        with os.fdopen(fd, 'w') as fp:
            fp.write(config)

    def testExtensionConfigOption(self):
        config = {
            'markdown.extensions.wikilinks': {
                'base_url': 'http://example.com/',
                'end_url': '.html',
                'html_class': 'test',
            },
            'markdown.extensions.footnotes:FootnotesExtension': {
                'PLACE_MARKER': '~~~footnotes~~~'
            }
        }
        self.create_config_file(config)
        options, logging_level = parse_options(['-c', self.tempfile])
        self.default_options['extension_configs'] = config
        self.assertEqual(options, self.default_options)

    def textBoolExtensionConfigOption(self):
        config = {
            'markdown.extensions.toc': {
                'title': 'Some Title',
                'anchorlink': True,
                'permalink': True
            }
        }
        self.create_config_file(config)
        options, logging_level = parse_options(['-c', self.tempfile])
        self.default_options['extension_configs'] = config
        self.assertEqual(options, self.default_options)

    def testExtensonConfigOptionAsJSON(self):
        config = {
            'markdown.extensions.wikilinks': {
                'base_url': 'http://example.com/',
                'end_url': '.html',
                'html_class': 'test',
            },
            'markdown.extensions.footnotes:FootnotesExtension': {
                'PLACE_MARKER': '~~~footnotes~~~'
            }
        }
        import json
        self.create_config_file(json.dumps(config))
        options, logging_level = parse_options(['-c', self.tempfile])
        self.default_options['extension_configs'] = config
        self.assertEqual(options, self.default_options)

    def testExtensonConfigOptionMissingFile(self):
        self.assertRaises(IOError, parse_options, ['-c', 'missing_file.yaml'])

    def testExtensonConfigOptionBadFormat(self):
        config = """
[footnotes]
PLACE_MARKER= ~~~footnotes~~~
"""
        self.create_config_file(config)
        self.assertRaises(yaml.YAMLError, parse_options, ['-c', self.tempfile])


class TestEscapeAppend(unittest.TestCase):
    """ Tests escape character append. """

    def testAppend(self):
        """ Test that appended escapes are only in the current instance. """
        md = markdown.Markdown()
        md.ESCAPED_CHARS.append('|')
        self.assertEqual('|' in md.ESCAPED_CHARS, True)
        md2 = markdown.Markdown()
        self.assertEqual('|' not in md2.ESCAPED_CHARS, True)


class TestAncestorExclusion(unittest.TestCase):
    """ Tests exclusion of tags in ancestor list. """

    class AncestorExample(markdown.inlinepatterns.SimpleTagInlineProcessor):
        """ Ancestor Test. """

        ANCESTOR_EXCLUDES = ('a',)

        def handleMatch(self, m, data):
            """ Handle match. """
            el = markdown.util.etree.Element(self.tag)
            el.text = m.group(2)
            return el, m.start(0), m.end(0)

    class AncestorExtension(markdown.Extension):

        def __init__(self, *args, **kwargs):
            """Initialize."""

            self.config = {}

        def extendMarkdown(self, md, md_globals):
            """Modify inline patterns."""

            pattern = r'(\+)([^\+]+)\1'
            md.inlinePatterns.register(TestAncestorExclusion.AncestorExample(pattern, 'strong'), 'ancestor-test', 0)

    def setUp(self):
        """Setup markdown object."""
        self.md = markdown.Markdown(extensions=[TestAncestorExclusion.AncestorExtension()])

    def test_ancestors(self):
        """ Test that an extension can exclude parent tags. """
        test = """
Some +test+ and a [+link+](http://test.com)
"""
        result = """<p>Some <strong>test</strong> and a <a href="http://test.com">+link+</a></p>"""

        self.md.reset()
        self.assertEqual(self.md.convert(test), result)

    def test_ancestors_tail(self):
        """ Test that an extension can exclude parent tags when dealing with a tail. """
        test = """
[***+em+*+strong+**](http://test.com)
"""
        result = """<p><a href="http://test.com"><strong><em>+em+</em>+strong+</strong></a></p>"""

        self.md.reset()
        self.assertEqual(self.md.convert(test), result)
