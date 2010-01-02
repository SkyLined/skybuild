@PYTHON -x "%~f0" %* & EXIT /B %ERRORLEVEL%
# Copyright (c) 2009-2010, Berend-Jan "SkyLined" Wever <berendjanwever@gmail.com>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of the
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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
