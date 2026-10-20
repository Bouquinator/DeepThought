import os
import sys

# Run by path (./dt): import DeepThought from this checkout, never from the
# current directory (which may contain another `deepthought` folder).
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") not in (os.path.dirname(os.path.abspath(__file__)), os.getcwd())]
sys.path.insert(0, _root)

from deepthought.cli.main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
