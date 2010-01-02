@PYTHON -x "%~f0" %* & EXIT /B %ERRORLEVEL%
import os, sys;

def Help():
  print "Usage: py2cmd \".py file path\" [\".cmd file path\"]";
  print "";
  print "py2cmd converts a .py file into a .cmd file that executes itself as a python script.";

def Main():
  if len(sys.argv) != 2 and len(sys.argv) != 3:
    Help();
    exit(1);
  py_file = sys.argv[1];
  if not sys.argv[1].endswith(".py"):
    print >>sys.stderr, "First argument must be the name or path of a \".py\" file.";
    exit(1);
  if not os.path.isfile(py_file):
    print >>sys.stderr, "Cannot find \"%s\": conversion cancelled." % py_file;
    exit(1);
  if len(sys.argv) != 3:
    cmd_file = py_file[:-3] + ".cmd";
  else:
    cmd_file = sys.argv[2];
  if os.path.isfile(cmd_file):
    try:
      os.remove(cmd_file)
    except OSError, e:
      print >>sys.stderr, "File \"%s\" already exists and cannot be deleted." % cmd_file;
      exit(1);
  cmd_handle = open(cmd_file, "wb");
  cmd_handle.write("@PYTHON -x \"%~f0\" %* & EXIT /B %ERRORLEVEL%\r\n");
  py_handle = open(py_file, "rb");
  for line in py_handle:
    cmd_handle.write(line);
  py_handle.close();
  cmd_handle.close();

if __name__ == "__main__":
  Main();
