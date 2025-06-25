
import unittest



from killerbunny.incubator.jsonpointer.constants import JSON_SCALARS, SCALAR_TYPES, JSON_VALUES
from killerbunny.incubator.jsonpointer.pretty_printer import FormatFlags, format_scalar, _spacer, _is_empty_or_single_item, _pp_dict, _pp_list, \
    pretty_print, _pp_dict, pretty_print

class TestFormatFlags(unittest.TestCase):
    def test_as_json_format(self) -> None:
        flags = FormatFlags.as_json_format()
        self.assertTrue(flags.quote_strings)
        self.assertFalse(flags.single_quotes)
        self.assertTrue(flags.use_repr)
        self.assertTrue(flags.format_json)
        self.assertEqual(flags.indent, 2)
        self.assertFalse(flags.single_line)
        self.assertFalse(flags.omit_commas)

    def test_with_indent(self) -> None:
        flags = FormatFlags().with_indent(4)
        self.assertEqual(flags.indent, 4)
        self.assertFalse(flags.quote_strings)

    def test_with_quote_strings(self) -> None:
        flags = FormatFlags().with_quote_strings(True)
        self.assertTrue(flags.quote_strings)
        self.assertFalse(flags.single_quotes)

    def test_with_single_quotes(self) -> None:
        flags = FormatFlags().with_single_quotes(True)
        self.assertTrue(flags.single_quotes)
        self.assertFalse(flags.quote_strings)

    def test_with_use_repr(self) -> None:
        flags = FormatFlags().with_use_repr(True)
        self.assertTrue(flags.use_repr)

    def test_with_format_json(self) -> None:
        flags = FormatFlags().with_format_json(True)
        self.assertTrue(flags.format_json)

    def test_with_single_line(self) -> None:
        flags = FormatFlags().with_single_line(True)
        self.assertTrue(flags.single_line)
        self.assertFalse(flags.omit_commas)
        flags = FormatFlags().with_single_line(False)
        self.assertFalse(flags.single_line)
        self.assertFalse(flags.omit_commas)
        flags = FormatFlags().with_single_line(False).with_omit_commas(True)
        self.assertTrue(flags.omit_commas)

    def test_with_omit_commas(self) -> None:
        flags = FormatFlags().with_omit_commas(True)
        self.assertTrue(flags.omit_commas)


class TestPPScalar(unittest.TestCase):
    def test_none(self) -> None:
        self.assertEqual(format_scalar(None, FormatFlags()), "None")
        self.assertEqual(format_scalar(None, FormatFlags().with_format_json(True)), "null")

    def test_bool(self) -> None:
        self.assertEqual(format_scalar(True, FormatFlags()), "True")
        self.assertEqual(format_scalar(False, FormatFlags()), "False")
        self.assertEqual(format_scalar(True, FormatFlags().with_format_json(True)), "true")
        self.assertEqual(format_scalar(False, FormatFlags().with_format_json(True)), "false")

    def test_string(self) -> None:
        self.assertEqual(format_scalar("hello", FormatFlags()), "hello")
        self.assertEqual(format_scalar("hello", FormatFlags().with_quote_strings(True)), '"hello"')
        self.assertEqual(format_scalar("hello", FormatFlags().with_quote_strings(True).with_single_quotes(True)), "'hello'")
        self.assertEqual(format_scalar("hello", FormatFlags().with_use_repr(True)), "hello")
        self.assertEqual(format_scalar("hello", FormatFlags().with_use_repr(True).with_quote_strings(True)), '"hello"')
        self.assertEqual(format_scalar("k\"l", FormatFlags().with_use_repr(True).with_quote_strings(True)), '"k\\"l"')

    def test_number(self) -> None:
        self.assertEqual(format_scalar(123, FormatFlags()), "123")
        self.assertEqual(format_scalar(3.14, FormatFlags()), "3.14")
        self.assertEqual(format_scalar(123, FormatFlags().with_use_repr(True)), "123")
        self.assertEqual(format_scalar(3.14, FormatFlags().with_use_repr(True)), "3.14")


class TestSpacer(unittest.TestCase):
    def test_single_line(self) -> None:
        self.assertEqual(" ", _spacer(FormatFlags().with_single_line(True), 2))

    def test_multi_line(self) -> None:
        self.assertEqual(_spacer(FormatFlags().with_single_line(False), 2), "    ")
        self.assertEqual(_spacer(FormatFlags().with_single_line(False).with_indent(4), 3), "            ")


class TestIsEmptyOrSingleItem(unittest.TestCase):
    def test_scalar(self) -> None:
        self.assertTrue(_is_empty_or_single_item(1))
        self.assertTrue(_is_empty_or_single_item("hello"))

    def test_empty_list(self) -> None:
        self.assertTrue(_is_empty_or_single_item([]))

    def test_single_item_list(self) -> None:
        self.assertTrue(_is_empty_or_single_item([1]))
        self.assertTrue(_is_empty_or_single_item(["hello"]))
        self.assertTrue(_is_empty_or_single_item([[]]))
        self.assertTrue(_is_empty_or_single_item([[[[]]]]))
        self.assertTrue(_is_empty_or_single_item([[[["one"]]]]))
        self.assertTrue(_is_empty_or_single_item([{"key": "one"}]))
        self.assertTrue(_is_empty_or_single_item([{"key": [["one"]]}]))
        self.assertTrue(_is_empty_or_single_item([[{"key": [["foo"]]}]]))
        self.assertTrue(_is_empty_or_single_item([{"key1": {"key2": {"key3": "foo"}}}]))

    def test_multi_item_list(self) -> None:
        self.assertFalse(_is_empty_or_single_item([1, 2]))
        self.assertFalse(_is_empty_or_single_item(["hello", "world"]))
        self.assertFalse(_is_empty_or_single_item([["one", "two"]]))
        self.assertFalse(_is_empty_or_single_item([[[["one", "two"]]]]))
        self.assertFalse(_is_empty_or_single_item([{"key": [["one", "two"]]}]))
        self.assertFalse(_is_empty_or_single_item([[{"one": "foo", "two": "bar"}]]))

    def test_empty_dict(self) -> None:
        self.assertTrue(_is_empty_or_single_item({}))

    def test_single_item_dict(self) -> None:
        self.assertTrue(_is_empty_or_single_item({"key": 1}))
        self.assertTrue(_is_empty_or_single_item({"key": "hello"}))
        self.assertTrue(_is_empty_or_single_item({"key": []}))
        self.assertTrue(_is_empty_or_single_item({"key": [1]}))
        self.assertTrue(_is_empty_or_single_item({"key": [["one"]]}))
        self.assertTrue(_is_empty_or_single_item({"key": {}}))
        self.assertTrue(_is_empty_or_single_item({"key": {"subkey": "value"}}))
        self.assertTrue(_is_empty_or_single_item({"key1": {"key2": {"key3": "foo"}}}))

    def test_multi_item_dict(self) -> None:
        self.assertFalse(_is_empty_or_single_item({"key1": 1, "key2": 2}))
        self.assertFalse(_is_empty_or_single_item({"key": [1, 2]}))
        self.assertFalse(_is_empty_or_single_item({"key": {"subkey1": "value1", "subkey2": "value2"}}))
        self.assertFalse(_is_empty_or_single_item({"key": [[{"one": "foo", "two": "bar"}]]}))


class TestPPDictNew(unittest.TestCase):
    def test_empty_dict(self) -> None:
        lines = [""]
        _pp_dict({}, FormatFlags(), lines)
        self.assertEqual(lines, ["{ }"])

    def test_single_scalar_dict(self) -> None:
        lines = [""]
        _pp_dict({"key": "value"}, FormatFlags(), lines)
        self.assertEqual(lines, ["{ key: value }"])

    def test_multi_scalar_dict(self) -> None:
        lines = [""]
        _pp_dict({"key1": "value1", "key2": "value2"}, FormatFlags(), lines)
        self.assertEqual(["{", " key1: value1,", " key2: value2", " }"],lines)

    def test_nested_list_dict(self) -> None:
        lines = [""]
        _pp_dict({"key": ["item1", "item2"]}, FormatFlags(), lines)
        self.assertEqual(['{', ' key:', ' [', ' item1,', ' item2', ' ]', ' }'], lines)

    def test_nested_dict_dict(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": "subvalue"}}, FormatFlags().with_single_line(False), lines)
        self.assertEqual(['{', '  key: { subkey: subvalue } }'], lines)

    def test_complex_dict(self) -> None:
        data: dict[str, JSON_VALUES] = {
            "key1": "value1",
            "key2": ["item1", "item2"],
            "key3": {"subkey1": "subvalue1", "subkey2": "subvalue2"},
            "key4": 123
        }
        lines = [""]
        _pp_dict(data, FormatFlags().with_single_line(False), lines)
        self.assertEqual(["{", "  key1: value1,", "  key2:", "  [", "    item1,", "    item2", "  ],", "  key3:",
                          "  {", "    subkey1: subvalue1,", "    subkey2: subvalue2", "  },", "  key4: 123", "}"], lines)

    def test_single_line_dict(self) -> None:
        lines = [""]
        _pp_dict({"key1": "value1", "key2": "value2"}, FormatFlags().with_single_line(True), lines)
        self.assertEqual(['{', ' key1: value1,', ' key2: value2', ' }'], lines)

    def test_single_item_list_in_dict(self) -> None:
        lines = [""]
        _pp_dict({"key": ["item1"]}, FormatFlags(), lines)
        self.assertEqual(['{', ' key: [ item1 ] }'], lines)

    def test_single_item_dict_in_dict(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": "subvalue"}}, FormatFlags(), lines)
        self.assertEqual(['{', ' key: { subkey: subvalue } }'], lines)

    def test_single_item_nested_list_in_dict(self) -> None:
        lines = [""]
        _pp_dict({"key": [["item1"]]}, FormatFlags(), lines)
        self.assertEqual(['{', ' key: [ [ item1 ] ] }'], lines)

    def test_single_item_nested_dict_in_dict(self) -> None:
        lines = [""]
        _pp_dict({"key": [{"subkey": "subvalue"}]}, FormatFlags(), lines)
        self.assertEqual(['{', ' key: [ { subkey: subvalue } ] }'], lines)

    def test_single_item_nested_dict_in_dict_2(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": ["subvalue"]}}, FormatFlags(), lines)
        self.assertEqual(['{', ' key:', ' {', ' subkey: [ subvalue ] } }'], lines)

    def test_single_item_nested_dict_in_dict_3(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": {"subsubkey": "subvalue"}}}, FormatFlags(), lines)
        self.assertEqual(['{', ' key:', ' {', ' subkey: { subsubkey: subvalue } } }'], lines)

    def test_single_item_nested_dict_in_dict_4(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": {"subsubkey": ["subvalue"]}}}, FormatFlags(), lines)
        self.assertEqual(['{', ' key:', ' {', ' subkey:', ' {', ' subsubkey: [ subvalue ] } } }'], lines)

    def test_single_item_nested_dict_in_dict_5(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": {"subsubkey": [{"subsubsubkey": "subvalue"}]}}}, FormatFlags().with_single_line(False), lines)
        expected = ['{',
                    '  key:',
                    '  {',
                    '    subkey:',
                    '    {',
                    '      subsubkey: [ { subsubsubkey: subvalue } ] } } }']
        self.assertEqual(expected,  lines)

    def test_single_item_nested_dict_in_dict_6(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": {"subsubkey": [{"subsubsubkey": ["subvalue"]}]}}}, FormatFlags(), lines)
        expected = ['{',
                    ' key:',
                    ' {',
                    ' subkey:',
                    ' {',
                    ' subsubkey: [ {',
                    ' subsubsubkey: [ subvalue ] } ] } } }']
        self.assertEqual(expected, lines)

    def test_single_item_nested_dict_in_dict_7(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": {"subsubkey": [{"subsubsubkey": [{"subsubsubsubkey": "subvalue"}]}]}}},
                 FormatFlags(), lines)
        expected = ['{',
                    ' key:',
                    ' {',
                    ' subkey:',
                    ' {',
                    ' subsubkey: [ {',
                    ' subsubsubkey: [ { subsubsubsubkey: subvalue } ] } ] } } }']
        self.assertEqual(expected, lines)

    def test_single_item_nested_dict_in_dict_8(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": {"subsubkey": [{"subsubsubkey": [{"subsubsubsubkey": ["subvalue"]}]}]}}},
                 FormatFlags().with_single_line(False), lines)
        expected = ['{',
                    '  key:',
                    '  {',
                    '    subkey:',
                    '    {',
                    '      subsubkey: [ {',
                    '          subsubsubkey: [ {',
                    '              subsubsubsubkey: [ subvalue ] } ] } ] } } }']
        self.assertEqual(expected, lines)

    def test_single_item_nested_dict_in_dict_9(self) -> None:
        lines = [""]
        _pp_dict({"key": {
            "subkey": {"subsubkey": [{"subsubsubkey": [{"subsubsubsubkey": [{"subsubsubsubsubkey": "subvalue"}]}]}]}}},
            FormatFlags().with_single_line(False), lines)
        expected = ['{',
                    '  key:',
                    '  {',
                    '    subkey:',
                    '    {',
                    '      subsubkey: [ {',
                    '          subsubsubkey: [ {',
                    '              subsubsubsubkey: [ { subsubsubsubsubkey: subvalue } ] } ] } ] '
                    '} } }']
        self.assertEqual(expected, lines)

    def test_single_item_nested_dict_in_dict_10(self) -> None:
        lines = [""]
        _pp_dict({"key": {"subkey": {
            "subsubkey": [{"subsubsubkey": [{"subsubsubsubkey": [{"subsubsubsubsubkey": ["subvalue"]}]}]}]}}},
            FormatFlags().with_single_line(False), lines)
        expected = ['{',
               '  key:',
               '  {',
               '    subkey:',
               '    {',
               '      subsubkey: [ {',
               '          subsubsubkey: [ {',
               '              subsubsubsubkey: [ {',
               '                  subsubsubsubsubkey: [ subvalue ] } ] } ] } ] } } }']
        self.assertEqual(expected, lines)

class TestPPList(unittest.TestCase):
    def test_empty_list(self) -> None:
        lines = [""]
        _pp_list([], FormatFlags(), lines)
        self.assertEqual(lines, ["[ ]"])

    def test_single_scalar_list(self) -> None:
        lines = [""]
        _pp_list([1], FormatFlags(), lines)
        self.assertEqual(lines, ["[ 1 ]"])

    def test_multi_scalar_list(self) -> None:
        lines = [""]
        _pp_list([1, 2, 3], FormatFlags(), lines)
        self.assertEqual(["[", "1, ", "2, ", "3", "]"], lines)

    def test_nested_list(self) -> None:
        lines = [""]
        _pp_list([[1, 2], [3, 4]], FormatFlags(), lines)
        self.assertEqual(["[ [", "1, ", "2", "], ", "[", "3, ", "4", ']', ']'], lines)

    def test_nested_dict_list(self) -> None:
        lines = [""]
        _pp_list([{"key1": "value1"}, {"key2": "value2"}], FormatFlags(), lines)
        self.assertEqual(['[ { key1: value1 }, ', '{ key2: value2 }', ']'], lines)

    def test_complex_list(self) -> None:
        data: list[JSON_VALUES] = [
            1,
            [2, 3],
            {"key1": "value1", "key2": "value2"},
            4
        ]
        lines = [""]
        _pp_list(data, FormatFlags(), lines)
        self.assertEqual(lines,
                         ["[", "  1,", "  [", "    2,", "    3", "  ],", "  {", "    key1: value1,", "    key2: value2",
                          "  },", "  4", "]"])

    def test_single_line_list(self) -> None:
        lines = [""]
        _pp_list([1, 2, 3], FormatFlags().with_single_line(True), lines)
        self.assertEqual(lines, ['[', ' 1,', ' 2,', ' 3', ' ]'])

    def test_single_item_list_in_list(self) -> None:
        lines = [""]
        _pp_list([[1]], FormatFlags(), lines)
        self.assertEqual(lines, ["[", "  [ 1 ]", "]"])

    def test_single_item_dict_in_list(self) -> None:
        lines = [""]
        _pp_list([{"key": "value"}], FormatFlags(), lines)
        self.assertEqual(lines, ["[", "  { key: value }", "]"])

    def test_single_item_nested_list_in_list(self) -> None:
        lines = [""]
        _pp_list([[[1]]], FormatFlags(), lines)
        self.assertEqual(lines, ['[ [ [ 1 ] ] ]'])

    def test_single_item_nested_dict_in_list(self) -> None:
        lines = [""]
        _pp_list([[{"key": "value"}]], FormatFlags(), lines)
        self.assertEqual(lines, ["[", "  [", "    { key: value }", "  ]", "]"])

    def test_single_item_nested_dict_in_list_2(self) -> None:
        lines = [""]
        _pp_list([{"key": [1]}], FormatFlags(), lines)
        self.assertEqual(lines, ["[", "  { key: [ 1 ] }", "]"])

    def test_single_item_nested_dict_in_list_3(self) -> None:
        lines = [""]
        _pp_list([{"key": {"subkey": "value"}}], FormatFlags(), lines)
        self.assertEqual(lines, ["[", "  { key: ", "  { subkey: value }", "  }", "]"])

    def test_single_item_nested_dict_in_list_4(self) -> None:
        lines = [""]
        _pp_list([{"key": {"subkey": [1]}}], FormatFlags(), lines)
        self.assertEqual(lines, ["[", "  { key: ", "  { subkey: [ 1 ] }", "  }", "]"])

    def test_single_item_nested_dict_in_list_5(self) -> None:
        lines = [""]
        _pp_list([{"key": {"subkey": [{"subsubkey": "value"}]}}], FormatFlags(), lines)
        self.assertEqual(lines,
                         ["[", "  { key: ", "  { subkey: ", "  [", "    { subsubkey: value }", "  ]", "  }", "  }",
                          "]"])

    def test_single_item_nested_dict_in_list_6(self) -> None:
        lines = [""]
        _pp_list([{"key": {"subkey": [{"subsubkey": [1]}]}}], FormatFlags(), lines)
        self.assertEqual(lines, ["[", "  { key: ", "  { subkey: ", "  [", "    [ 1 ]", "  ]", "  }", "  }", "]"])

    def test_single_item_nested_dict_in_list_7(self) -> None:
        lines = [""]
        _pp_list([{"key": {"subkey": [{"subsubkey": [{"subsubsubkey": "value"}]}]}}], FormatFlags(), lines)
        self.assertEqual(lines,
                         ["[", "  { key: ", "  { subkey: ", "  [", "    [", "      { subsubsubkey: value }", "    ]",
                          "  ]", "  }", "  }", "]"])

    def test_single_item_nested_dict_in_list_8(self) -> None:
        lines = [""]
        _pp_list([{"key": {"subkey": [{"subsubkey": [{"subsubsubkey": [1]}]}]}}], FormatFlags(), lines)
        self.assertEqual(lines,
                         ["[", "  { key: ", "  { subkey: ", "  [", "    [", "      [ 1 ]", "    ]", "  ]", "  }", "  }",
                          "]"])

    def test_single_item_nested_dict_in_list_9(self) -> None:
        lines = [""]
        _pp_list([{"key": {"subkey": [{"subsubkey": [{"subsubsubkey": [{"subsubsubsubkey": "value"}]}]}]}}],
                 FormatFlags(), lines)
        self.assertEqual(lines, ["[", "  { key: ", "  { subkey: ", "  [", "    [", "      [",
                                 "        { subsubsubsubkey: value }", "      ]", "    ]", "  ]", "  }", "  }", "]"])

    def test_single_item_nested_dict_in_list_10(self) -> None:
        lines = [""]
        _pp_list([{"key": {"subkey": [{"subsubkey": [{"subsubsubkey": [{"subsubsubsubkey": [1]}]}]}]}}], FormatFlags(),
                 lines)
        self.assertEqual(lines,
                         ["[", "  { key: ", "  { subkey: ", "  [", "    [", "      [", "        [ 1 ]", "      ]",
                          "    ]", "  ]", "  }", "  }", "]"])


class TestPrettyPrint2(unittest.TestCase):
    def test_scalar(self) -> None:
        self.assertEqual(pretty_print(1, FormatFlags(), []), "1")
        self.assertEqual(pretty_print("hello", FormatFlags(), []), "hello")

    def test_list(self) -> None:
        self.assertEqual(pretty_print([1, 2, 3], FormatFlags().with_single_line(False), []), "[\n  1,\n  2,\n  3\n]")
        self.assertEqual(pretty_print([1, 2, 3], FormatFlags().with_single_line(True), []), "[ 1, 2, 3 ]")

    def test_dict(self) -> None:
        self.assertEqual(pretty_print({"key1": "value1", "key2": "value2"}, FormatFlags().with_single_line(False), []),
                         "{\n  key1: value1,\n  key2: value2\n}")
        self.assertEqual(pretty_print({"key1": "value1", "key2": "value2"}, FormatFlags().with_single_line(True), []),
                         "{ key1: value1, key2: value2 }")

    def test_complex(self) -> None:
        data: dict[str, JSON_VALUES] = {
            "key1": "value1",
            "key2": [1, 2, 3],
            "key3": {"subkey1": "subvalue1", "subkey2": "subvalue2"}
        }
        expected = "{\n  key1: value1,\n  key2:\n  [\n    1,\n    2,\n    3\n  ],\n  key3:\n  {\n    subkey1: subvalue1,\n    subkey2: subvalue2\n  }\n}"
        self.assertEqual(pretty_print(data, FormatFlags().with_single_line(False), []), expected)

    def test_complex_single_line(self) -> None:
        data: dict[str, JSON_VALUES] = {
            "key1": "value1",
            "key2": [1, 2, 3],
            "key3": {"subkey1": "subvalue1", "subkey2": "subvalue2"}
        }
        expected = "{ key1: value1, key2: [ 1, 2, 3 ], key3: { subkey1: subvalue1, subkey2: subvalue2 } }"
        self.assertEqual(pretty_print(data, FormatFlags().with_single_line(True), []), expected)

    def test_empty_list(self) -> None:
        self.assertEqual(pretty_print([], FormatFlags(), []), "[ ]")

    def test_empty_dict(self) -> None:
        self.assertEqual(pretty_print({}, FormatFlags(), []), "{ }")

    def test_nested_empty_list(self) -> None:
        self.assertEqual(pretty_print([[]], FormatFlags().with_single_line(False), []), "[ [ ] ]")
        self.assertEqual(pretty_print([[]], FormatFlags().with_single_line(True), []), "[ [ ] ]")


    def test_nested_empty_dict(self) -> None:
        self.assertEqual(pretty_print([{}], FormatFlags().with_single_line(False), []), "[ { } ]")
        self.assertEqual(pretty_print([{}], FormatFlags().with_single_line(True), []), "[ { } ]")


    def test_nested_empty_list_single_line(self) -> None:
        self.assertEqual(pretty_print([[]], FormatFlags().with_single_line(True), []), "[ [ ] ]")

    def test_nested_empty_dict_single_line(self) -> None:
        self.assertEqual(pretty_print([{}], FormatFlags().with_single_line(True), []), "[ { } ]")

