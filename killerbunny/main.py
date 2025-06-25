#  File: main.py
#  Copyright (c) 2025 Robert L. Ross
#  All rights reserved.
#  Open-source license to come.
#  Created by: Robert L. Ross
#

"""A main entry point for temp testing. This project will become a library and
not directly started by a main() method.

Python Dependencies installed:

dev/test:
pytest
      iniconfig          pkgs/main/noarch::iniconfig-1.1.1-pyhd3eb1b0_0
      packaging          pkgs/main/osx-64::packaging-24.2-py313hecd8cb5_0
      pluggy             pkgs/main/osx-64::pluggy-1.5.0-py313hecd8cb5_0
      pytest             pkgs/main/osx-64::pytest-8.3.4-py313hecd8cb5_0
MyPy
Successfully installed build-1.2.2.post1 pyproject_hooks-1.2.0





Build utils package and deploy to JPathInterpreter:
2.Rebuild the wheel: Navigate to the WordSpy directory and run python -m build --sdist --wheel . again.
This will create a new wheel file in the dist directory.
The version number in the filename might change if you've updated the version in your pyproject.toml file.
3.Reinstall the wheel: Activate your JPathInterpreter environment and install the newly built wheel using
pip install /path/to/WordSpy/dist/utils-X.Y.Z-py3-none-any.whl
(replacing /path/to/WordSpy/dist/utils-X.Y.Z-py3-none-any.whl with the actual path to your new wheel file).

"""



def main() -> None:
    pass

if __name__ == '__main__':
    main()

