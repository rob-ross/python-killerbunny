### This is the README for killerbunny

# RFC 9535 JSONPath: Query Expressions for JSON

Home of another JSON Path query library. But better. Stronger. Faster...

uhm...

Well, at the very least, very much much another. 

This project implements RFC 9535. It passes the jsonpath-compliance-test-suite at :

https://github.com/jsonpath-standard/jsonpath-compliance-test-suite

with the exception of some I-Regexp patterns (RFC 9485) and whitespace tests.

It has no external dependencies other than PyTest for running the unit tests. 

As it is a Python package, it uses the standard re module for processing regular expression patterns via the search() and match() function extensions. It is also lenient in white space handling.

It has a very simple API at the moment. 

```python
root_value = json.load("bookstore.json")
json_path_str = '$.store.book.*'
query = WellFormedValidQuery.from_str(json_path_str)
nodelist:NodeList = query.eval(root_value)

for node in nodelist:
    print(node.jpath_str)  # the normalized path for this node
    print(node.jvalue)  # the JSON value for this path as a Python object
    

```

A NodeList also has methods for getting all the paths and values directly.

If the json_path_str does not represent a well-formed and valid query string, from_str() will raise an error.


There is also a REPL for loading json files and applying queries in killerbunny.cli.repl.py.
See the README.md in the cli directory.



