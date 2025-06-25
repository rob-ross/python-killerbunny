#  File: constants.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

"""General constants used in this package. """

ONE_MEBIBYTE = 1*1024*1024
UTF8 = "utf-8"

JPATH_DATA_SEPARATOR = "  :  "  # used in test files to delimit a json path from result data

# SUBPARSE_NAMES: used in JPathParser.subparse() and the repl to parse particular grammar productions for testing
SUBPARSE_NAMES = [
    "function_expr",
    "singular_query", "comparable", "filter_query", "test_expr", "comparison_expr", "basic_expr",
    "selector", "bracketed_selection", "identifier", "string_literal",
    "segment", "jsonpath_query",
]

# key names for retrieving json values from a Context
ROOT_JSON_VALUE_KEY             = "root.json_value"
SEGMENT_INPUT_NODELIST_KEY      = "segment_input_nodelist"
FILTER_SELECTOR_INPUT_NODE_KEY  = "filter_selector_input_node"
CURRENT_NODE_KEY                = "current_node"
JPATH_QUERY_RESULT_NODE_KEY     = "jpath_query.output_nodelist"
