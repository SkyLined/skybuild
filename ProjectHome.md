Requirements:
  * Builds .asm files using [nasm](http://www.nasm.us/)
  * Compile C/C++ files and link using [Visual Studio](http://www.microsoft.com/visualstudio/en-us/default.mspx) 8 (2005) and 9 (2008), and [Windows SDK](http://msdn.microsoft.com/en-us/windows/bb980924.aspx) 7.0.
File format support/features:
  * Supports .c, .cpp, .asm, .def and .obj sources
  * Supports .bin, .dll, .exe and .obj output.
  * Supports recursive builds of sub-folders.
  * Supports wrapping .py files into self-executing .cmd files.
Build features:
  * Store build configuration information in build\_config.py:
    * Debug build (yes/no)
    * global DEFINES
    * Version number (passed as DEFINE during build).
    * dependencies between files
    * pre/postbuild commands to execute before/after building each file
    * test commands to test the result of a build
    * finish commands to finish a build
  * Automatically incremented build number and build timestamp stored in build\_info.txt file and also passed as DEFINE during build.
  * Convert .py files to .cmd files using py2cmd.cmd.
