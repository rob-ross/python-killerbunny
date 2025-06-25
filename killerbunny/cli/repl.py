
#  File: repl.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#
#



"""Interactive REPL for Json path query tool. Provides commands for evaluating jsonpath queries as well as lexing,
parsing, and evaluating sub sequences of the json path query grammar.
"""



import cmd
import json
import os
from pathlib import Path
from typing import IO

from killerbunny.evaluating.well_formed_query import WellFormedValidQuery
from killerbunny.shared.errors import Error
from killerbunny.evaluating.evaluator import JPathEvaluator
from killerbunny.evaluating.runtime_result import RuntimeResult
from killerbunny.evaluating.value_nodes import VNodeList
from killerbunny.shared.json_type_defs import JSON_ValueType
from killerbunny.lexing.lexer import JPathLexer
from killerbunny.lexing.tokens import Token
from killerbunny.parsing.node_type import ASTNode
from killerbunny.parsing.parse_result import ParseResult
from killerbunny.parsing.parser import JPathParser
from killerbunny.shared.constants import SUBPARSE_NAMES, ROOT_JSON_VALUE_KEY

from killerbunny.shared.context import Context

_MODULE_DIR = Path(__file__).parent


# noinspection PyUnusedLocal
class JSONPathShell(cmd.Cmd):
    # instance declarations
    current_json_value: JSON_ValueType  # used as the root node value for evaluating json path query strings
    last_result_nodelist: VNodeList # node list returned from last successful evaluation
    last_errors_list: list[Error]
    last_ast_nodes: list[ tuple[str, ASTNode ]]  # holds the ASTNodes of the last successful parse
    
    intro:str = "JSON path query REPL tool.  Type help or ? to list commands.\n"
    prompt:str = "(jpath repl) > "
    default_display_width:int = 80
    
    def __init__(self, completekey: str = "tab", stdin: IO[str] | None = None, stdout: IO[str] | None = None):
        """Initialize superclass with arguments provided by the Cmd framework, then initialize instance variables.

        """
        super().__init__(completekey, stdin, stdout)
        self.current_json_value = None
        self.last_result_nodelist:VNodeList = VNodeList.empty_instance()
        self.last_errors_list = []
        self.last_ast_nodes = []
        
        # temp? to avoid having to load this every time while developing this module:
        self._load_json_file(_MODULE_DIR / '../bookstore.json')
    
    ####################################################################
    # FILE OPERATIONS
    ####################################################################
    
    def do_cd(self, args: str) -> None:
        """Change the current working directory.
        Usage: cd <directory_path>
        If no directory is provided, it prints the current directory (like pwd).
        Supports '..' to go to the parent directory.
        """
        target_path_str = args.strip()
        
        if not target_path_str:
            # If no argument, behave like pwd
            self.do_pwd("")
            return
        
        if target_path_str == "examples":
            # navigate to "tests" directory to load sample files
            # todo make this not this. Terrible. fragile. dumb.  works.
            #target_path_str = "/Users/robross/Documents/Development/IdeaProjects/WordSpy/packages/killerbunny/tests/test_jpath_interpreter/incubator/jpath/rfc9535_examples"
            target_path: Path = _MODULE_DIR / "../../../tests/jpath/rfc9535_examples"
            target_path_str = str(target_path.resolve())
        try:
            # os.chdir handles '..' and other relative/absolute paths correctly
            os.chdir(target_path_str)
            # Optionally, print the new current directory
            print(f"Current directory: {os.getcwd()}")
        except FileNotFoundError:
            print(f"Error: Directory not found - {target_path_str}")
        except NotADirectoryError:
            print(f"Error: Not a directory - {target_path_str}")
        except OSError as e:
            # Catch other potential OS errors (e.g., permission denied)
            print(f"Error changing directory to {target_path_str}: {e}")
        
        return
    
    # noinspection PyMethodMayBeStatic
    def do_pwd(self, args: str) -> None:
        """Display the content of the current working directory."""
        print(f"{os.getcwd()}")
        return
    
    def do_dir(self, args: str) -> None:
        """Alias for do_pwd. """
        return self.do_pwd(args)
    
    # noinspection PyMethodMayBeStatic
    def do_ls(self, args: str) -> None:
        """List the files in the argument directory, or the current directory if no argument is given."""
        target_path_str = args.strip()
        if not target_path_str:
            target_path = Path.cwd() # Current working directory
        else:
            target_path = Path(target_path_str)
        
        if not target_path.is_dir():
            print(f"Error: {target_path} is not a directory or does not exist.")
            return
        
        try:
            for entry in target_path.iterdir():
                print(entry.name) # entry is a Path object, entry.name gives the name
        except OSError as e:
            print(f"Error listing directory {target_path}: {e}")
        return
    
    
    ####################################################################
    # JSON DATA LOADING
    ####################################################################
    
    def _load_json_file(self, json_value_path: Path) -> None:
        with open(json_value_path, "r", buffering=1024*1024) as in_file:
            json_value = json.load(in_file)
            self.current_json_value = json_value
            
    def do_load(self, args: str) -> None:
        """Tries to load a json value from a json text file provided as an argument. """
        path = Path(args)
        if not path.exists():
            print(f"File {path} does not exist.\nNothing was loaded.")
            return
        
        try:
            self._load_json_file(Path(args))
            print("File loaded")
        except Exception as e:
            print(f"{e}: Failed to load {path}")

        return
    
    # noinspection PyMethodMayBeStatic
    def complete_load(self, text: str, line: str, begidx: int, endidx: int) -> list[str]:
        """
        Provides tab-completion for the 'load' command.
        Completes directory names and file names ending with '.json'.
        """
        completions: list[str] = []
        
        # 'text' is the partial path/filename the user has typed so far.
        # For example:
        # If line is "load my_dir/my_f", text is "my_dir/my_f"
        # If line is "load my_dir/", text is "my_dir/" (or "" if readline is involved and cursor is after /)
        # If line is "load f", text is "f"
        
        # Determine the directory to search in and the prefix of entries to match.
        current_path_typed = Path(text)
        
        if text.endswith(os.sep) or (current_path_typed.is_dir() and not text.endswith(os.sep) and os.path.exists(text)):
            # User has typed a directory path (e.g., "some_dir/" or "some_dir")
            # We should list the contents of this directory.
            directory_to_search = current_path_typed
            prefix_for_entries = "" # Match all entries in this directory
        else:
            # User is typing a name within a directory, or in the CWD.
            # e.g., "some_dir/partial_name" or "partial_name"
            directory_to_search = current_path_typed.parent
            prefix_for_entries = current_path_typed.name
        
        # If directory_to_search is empty (e.g., text was "filepart"), search in CWD.
        if not str(directory_to_search): # Path('') is an empty path string
            directory_to_search = Path("")
        
        try:
            if directory_to_search.is_dir():
                for entry_path in directory_to_search.iterdir():
                    entry_name = entry_path.name
                    if entry_name.startswith(prefix_for_entries):
                        if entry_path.is_dir():
                            # For cmd completion, we return the name that completes the prefix.
                            # The cmd module handles prepending the directory part of 'text'.
                            # So, if text was "my_d" and entry_name is "my_dir",
                            # we return "my_dir/". cmd will show "my_dir/".
                            # If text was "existing_dir/my_d" and entry_name is "my_dir",
                            # we return "my_dir/". cmd will show "existing_dir/my_dir/".
                            completions.append(entry_name + os.sep)
                        elif entry_name.endswith(".json"):
                            completions.append(entry_name)
        except OSError:
            # Handles cases like directory_to_search not existing or permission errors.
            # Silently ignore and return no completions from this path.
            pass
        
        return completions

        
    def do_value(self, args: str) -> None:
        """Display the currently loaded json value."""
        if args == "-l":
            msg = f"json value: {json.dumps(self.current_json_value, indent=2)}"
        else:
            msg = f"json value: {json.dumps(self.current_json_value)}"
        print(msg)
        
        return
    
    def do_result(self, args: str) -> None:
        """Print the result of the last json path query evaluation operations. use result -l to pretty print the
        json value with indent=2"""
        print()
        if self.last_result_nodelist is None:
            print(f"*** current result is None")
        else:
            self.last_result_nodelist.pretty_print(args)
        print()
        return
    
    def do_errors(self, args: str) -> None:
        """Display the errors from the last lex/parse/eval operation. """
        if not self.last_errors_list:
            print(f"Error list is empty.")
            return
        
        header_str = f"Last errors ( {len( self.last_errors_list)} ):"
        print(header_str)
        print('-'* len(header_str))
        for index, error in enumerate(self.last_errors_list):
            msg = f"error[{index}] {error.as_string()}"
            print(msg)
        print()
        
    def _display_ast_nodelist(self) -> None:
        """Display the ASTNodes from the last successful parse operation"""
        if not self.last_ast_nodes:
            print(f"ASTNode list is empty.")
            return
        for node in self.last_ast_nodes:
            print(f"ASTNode:  {node[0]}")
            print(f"    ast:  {node[1]}")
            print()
        
        
    def do_ast(self, args: str) -> None:
        """Display the ASTNodes from the last successful parse operation"""
        self._display_ast_nodelist()
        
    
    def _lex_impl(self, args: str) ->  list[Token]:
        """Run the lexer on the argument string and display the scanned tokens.
        :return list of scanned Tokens, or None if an error occurred, and return Error
        """
        print()
        lexer = JPathLexer("", args)
        tokens, error = lexer.tokenize()
        token_str = ""
        if tokens:
            token_str = ', '.join( t.__testrepr__() for t in tokens)
        print(f"lexer:    {token_str}")
        self.last_errors_list = []
        if error:
            print(f"*** lexer Error: {error.as_string()}")
            self.last_errors_list = [error]
            tokens = []  # if there were errors, don't propagate any Tokens.
        return tokens
    
    def do_lex(self, args: str) -> None:
        """Run the lexer on the argument string and display the scanned tokens. """
        self._lex_impl(args)
        return
    
    def _parse_impl(self, tokens: list[Token], production_name: str | None = None) -> list[ASTNode]:
        """Parse the token list in the `tokens` argument and display the generated AST.
        :return list[ASTNode] When parsing a well-formed json path query starting with the root node identifier $,
        this return list will contain the single ASTNode resulting from a successful parsing.
        If `production_name` is "all" then multiple grammar prouctions
        are attempted to be parsed for the same query string, so multiple ASTNode instances will be returned from
        subparse() and thus the return list will contain multiple ASTNode instances.
        """
        if not tokens:
            print(f"*** _parse_impl Error: tokens list is empty")
            return []
        
        result: ParseResult
        nodes:  list[ tuple[str, ASTNode ]]
        errors: list[ tuple[str, Error ]]
        
        parser = JPathParser(tokens)
        
        self.last_ast_nodes = []
        
        if production_name is None:
            # full parse, compliant with RFC 9535. Token list must start with root node identifier "$" to be valid.
            result =  parser.parse()
            ast_list : list[ASTNode] = []
            ast = result.node
            if ast is not None:
                ast_list = [ast]
                self.last_ast_nodes = [ ( "jsonpath_query", ast)]
                self._display_ast_nodelist()
                # print(f"ASTNode:  {type(ast).__name__}")
                # print(f"    ast:  {ast}")
                # print()
            if result.error:
                print(f"**** parser Error: {result.error.as_string()}")
                self.last_errors_list = [result.error]
            else:
                self.last_errors_list = []
            return ast_list
        else:
            nodes, errors = parser.subparse(production_name)
        
        # report subparsing successes or failures.
        if not nodes:
            print(f"*** parsing failed. No nodes returned for jpath: {tokens[0].position.text}")
        else:
            print(f"Parsing succeeded. {len(errors)} subparse errors reported.")
            self.last_ast_nodes = nodes
            self._display_ast_nodelist()
            #
            # for node in nodes:
            #     print(f"ASTNode:  {node[0]}")
            #     print(f"    ast:  {node[1]}")
            #     print()
        
        self.last_errors_list = []
        if errors:
            for err_name, error in errors:
                self.last_errors_list.append(error)
        
        if errors and not nodes:
            # only display an error here if no parsing succeeded. If at least one parsing succeeded,
            # the errors will be for the ones that didn't succeed. But we want to focus on the success here.
            # For now limit to reporting to the first error if there are multiple errors
            # user can see all errors by entering the "errors" command at the prompt
            print( f"*** parsing errors ({len(errors)}). Showing first error: ")
            print( f"errors[0]: {errors[0][1].as_string()}")
        
        # we've reported any parsing errors in this method and saved them to self.last_errors_list
        # We now return any ASTNodes from a successful parse to the caller
        return [ node[1] for node in nodes ]
    
    def do_parse(self, args: str) -> None:
        """Run the lexer and parser on the argument str, but do not invoke the evaluator. Displays the scanned tokens
        and AST parse tree. """
        tokens: list[Token] = self._lex_impl(args)
        if not tokens:
            # False tells Cmd to keep running. We return here because lexer returned no tokens to parse
            return
        self._parse_impl(tokens)
        
        return
    
    
    def _evaluate_ast_node(self, ast_node: ASTNode, context: Context | None = None) -> RuntimeResult:
        """Evaluate the AST node in the argument with the provided context. The context will have the root data node and
        may also have a value for the "current node" if evaluating a subquery that includes a current node identifier.
        If `context` is None, a new Context is created and the currently loaded json value in self.current_json_value
        is set in the new Context for key ROOT_JSON_VALUE_KEY """
        rt_result: RuntimeResult = RuntimeResult()
        if ast_node is not None:
            if context is None:
                context = self._make_root_context()
            evaluator = JPathEvaluator()
            rt_result  = evaluator.visit(ast_node, context)
            self.last_errors_list = []
            if rt_result.error:
                print(f"evaluator error: {rt_result.error.as_string()}")
                self.last_errors_list = [rt_result.error]
            if rt_result.value is not None:
                #self.last_result_nodelist = rt_result.value
                print(f"result: type = {type(rt_result.value).__name__}, {rt_result.value}")
        
        return rt_result
                
    def _make_root_context(self) -> Context:
        context = Context('<root>')
        context.set_symbol(ROOT_JSON_VALUE_KEY, self.current_json_value)
        return context
        
    def _evaluate_impl(self, args: str) -> None:
        """Evaluate the json path in the argument against the current JSON value"""
        # todo why do we have two eval impl methods? see _evaluate_ast_node. Merge them.
        tokens: list[Token] = self._lex_impl(args)
        if not tokens:
            # We return here because lexer returned no tokens to parse. _lex_impl is responsible for error reporting
            return
        
        ast_node_list: list[ASTNode] = self._parse_impl(tokens)
        if not ast_node_list:
            # _parse_impl is responsible for error reporting
            return
        # subparsing can return more than one ASTNode, but here we are calling _parse_impl
        # with no `production_name` argument, so it will produce a single ASTNode if parsing succeeds.
        ast_node = ast_node_list[0]  # this is the root of the AST, and should be a JsonPathQueryNode
        
        # using initializer directly from a testing context; we have also verified that the query string is well formed
        # and valid. Users of this library should always use WellFormedValidQuery.from_str() instead.
        jpath_query = WellFormedValidQuery(ast_node)
        result_list = jpath_query.eval(self.current_json_value)
        if result_list is None:
            raise ValueError(f"WellFormedValidQuery.eval returned None")

        if result_list is not None:
            self.last_result_nodelist = result_list
            print(f"\neval result: type: {type(result_list).__name__}")
            print(f"len: {len(result_list)}. (Type 'result' for list of result nodes)")
            
            # print(f"{result_list}")
    
    
    def do_evaluate(self, args: str) -> None:
        """Evaluate the interpreter against the current JSON Value. Equivalent to entering a json path query with no prefix command.
        """
        self._evaluate_impl(args)
        print()
        return
        
    
    def _subparse_impl(self, method_name: str, jpath_query: str) -> list[ASTNode]:
        """Lex and parse the input str against the target grammar symbol given by `method_name`.
        If `method_name` is "all", try all methods in SUBPARSE_NAMES.
        
        """
        print()
        tokens: list[Token] = self._lex_impl(jpath_query)
        if not tokens:
            # We return here because lexer returned no tokens to parse
            return []
        
        nodes: list[ASTNode] = self._parse_impl(tokens, method_name)
        # _parse_impl displays errors and saves error list to self.last_errors_list. It also displays the ASTNodes for
        # parsing successes. Here we just care about the returned ASTNodes for possible evaluation.
        return nodes
        
    def do_subparse(self, args: str) -> None:
        """Lex and parse the input str against a list of possible target symbols, and return the first AST that succeeds in
        fully parsing with no errors, using the entire argument string. If no successful parsing occurrs, display the
        error list of each attempt by grammar symbol. """
        
        # args string could be a method name followed by the jpath query, or just a jpath query
        method_name: str = "all"
        jpath_query: str = args
        line_parts = args.partition(' ')
        if line_parts[0] in SUBPARSE_NAMES:
            # user is evaluating a specific grammar production symbol.
            # e.g., at the prompt they typed 'subparse comparison_expr 1==2'
            # this method is passed 'comparison_expr 1==2' in `args`
            method_name = line_parts[0]
            jpath_query = line_parts[2]
            
        self._subparse_impl(method_name, jpath_query)

        
    def do_subeval(self, args: str) -> None:
        """Subparse the argument string then evaluate the AST with the currently loaded json value as the root node value."""
        self.do_subparse(args)
        context = self._make_root_context()
        # todo we may have to add a current root identifier for the partial query if using a relative query node
        # we probably need a cmd method to load the current node value from the current root value.
        rt_results: dict[ str, RuntimeResult] = {}
        if self.last_ast_nodes:
            for name, node in self.last_ast_nodes:
                rt_result: RuntimeResult = self._evaluate_ast_node(node, context)
                # todo saving state for multiple nodelist results
                
                
        
        
    def default(self, line: str) -> None:
        """Evaluate the interpreter against the current JSON Value"""
        line_parts = line.partition(' ')
        if line_parts[0] in SUBPARSE_NAMES:
            # user is evaluating a specific grammar production symbol, e.g. 'comparison_expr 1==1'
            self.do_subparse(line)
            # self._subparse_impl(line_parts[0], line_parts[2])
        else:
            self.do_evaluate(line)
    
    # noinspection PyMethodMayBeStatic
    def do_quit(self, arg: str) -> bool:
        """Exit the application."""
        print(f"Quitting...")
        return True
    
    def do_exit(self, arg: str) -> bool:
        """ Alias of 'quit' """
        return self.do_quit(arg)
    
if __name__ == "__main__":
    """To run this script from Terminal, cd to killerbunny dir and enter
    python -m killerbunny.cli.repl
    or
    PYTHONPATH=$(pwd) python killerbunny/cli/repl.py
    
    First line is preferred
    """
    
    JSONPathShell().cmdloop()