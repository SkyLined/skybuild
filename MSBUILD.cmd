@ECHO OFF
:: Copyright (c) 2009-2013, Berend-Jan "SkyLined" Wever <berendjanwever@gmail.com>
:: All rights reserved.
:: 
:: Redistribution and use in source and binary forms, with or without
:: modification, are permitted provided that the following conditions are met:
::     * Redistributions of source code must retain the above copyright
::       notice, this list of conditions and the following disclaimer.
::     * Redistributions in binary form must reproduce the above copyright
::       notice, this list of conditions and the following disclaimer in the
::       documentation and/or other materials provided with the distribution.
::     * Neither the name of the copyright holder nor the names of the
::       contributors may be used to endorse or promote products derived from
::       this software without specific prior written permission.
:: 
:: THIS SOFTWARE IS PROVIDED ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
:: INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
:: AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
:: COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
:: INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
:: NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
:: DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
:: THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
:: (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
:: SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

:: Enable delayed environment variable expansion and command extensions, if not enabled already:
SETLOCAL ENABLEDELAYEDEXPANSION ENABLEEXTENSIONS
CALL :MAIN %*
SET result=%ERRORLEVEL%
IF ERRORLEVEL 1 (
  :: On Windows XP, errorlevel is not passed on correctly for unknown reasons. This means that "build.py" will not be
  :: able to detect the a problem during building. To fix this issue, a CRLF is output to stderr: if "build.py" sees
  :: ANY output to stderr, it assumes the build failed and report the problem.
  ECHO ERROR>&2
) ELSE IF "%~2" == "" IF "%2" == "" (
  :: If no argument is specified, start a new shell:
  CMD /K PROMPT MSBUILD $P$G
  SET result=%ERRORLEVEL%
)
:: Once we ENDLOCAL we will lose all state, so the EXIT needs to be on the same line to allow %result% to be used:
ENDLOCAL & EXIT /B %result%

:MAIN
  IF "%~1"=="x86" (
    CALL :SETENV32
    IF ERRORLEVEL 1 EXIT /B %ERRORLEVEL%
  ) ELSE IF "%~1"=="x64" (
    CALL :SETENV64
    IF ERRORLEVEL 1 EXIT /B %ERRORLEVEL%
  ) ELSE (
    ECHO Usage: MSBUILD architecture command arguments>&2
    ECHO Where:
    ECHO   architecture      - Target architecture ^(x86 or x64^),
    ECHO   command arguments - Command to execute ^(eg CL, LINK, DUMPBIN^) and arguments.
    EXIT /B 1
  )
  
  :: I would like to do a "SHIFT /1 & %*" to remove the first argument and execute arguments %2 and upwards as a command.
  :: Unfortunately, SHIFT does not seem to affect %* at all, so we have to work around this by remove this first 
  :: four characters from %*, because the first argument is always three characters and separated by one space from the
  :: second argument:
  SET command=%*
  ECHO MSBUILD %~1 EXECUTING: !command:~4!
  !command:~4!
  EXIT /B %ERRORLEVEL%

:SETENV32
  CALL :FINDANDCALL "Visual Studio 12" "%VS120COMNTOOLS%..\..\" "VC\bin\vcvars32.bat"
  IF ERRORLEVEL == 1 EXIT /B 0
  CALL :FINDANDCALL "Visual Studio 11" "%VS110COMNTOOLS%..\..\" "Common7\Tools\vsvars32.bat"
  IF ERRORLEVEL == 1 EXIT /B 0
  CALL :FINDANDCALL "Visual Studio 2010" "%VS100COMNTOOLS%..\..\" "Common7\Tools\vsvars32.bat"
  IF ERRORLEVEL == 1 EXIT /B 0
  CALL :FINDANDCALL "Visual Studio 2008" "%VS90COMNTOOLS%..\..\" "Common7\Tools\vsvars32.bat"
  IF ERRORLEVEL == 1 EXIT /B 0
  CALL :FINDANDCALL "Visual Studio 2005" "%VS80COMNTOOLS%..\..\" "Common7\Tools\vsvars32.bat"
  IF ERRORLEVEL == 1 EXIT /B 0
  CALL :FINDANDCALL "Microsoft SDK 7.1" "%ProgramFiles%\Microsoft SDKs\Windows\v7.1\" "Bin\SetEnv.cmd" /x86 /xp
  IF ERRORLEVEL == 1 EXIT /B 0
  CALL :FINDANDCALL "Microsoft SDK 7.0" "%ProgramW6432%\Microsoft SDKs\Windows\v7.0\" "Bin\SetEnv.cmd" /x86 /xp
  IF ERRORLEVEL == 1 EXIT /B 0
  ECHO Could not find a known x86 build environment!>&2
  EXIT /B 1

:SETENV64
  CALL :FINDANDCALL "Visual Studio 12" "%VS120COMNTOOLS%..\..\" "VC\bin\x86_amd64\vcvarsx86_amd64.bat"
  IF ERRORLEVEL == 1 EXIT /B 0
  CALL :FINDANDCALL "Visual Studio 11" "%VS110COMNTOOLS%..\..\" "VC\bin\x86_amd64\vcvarsx86_amd64.bat"
  IF ERRORLEVEL == 1 EXIT /B 0
  IF "%PROCESSOR_ARCHITECTURE%"=="x86" (
    CALL :FINDANDCALL "Visual Studio 2010" "%VS100COMNTOOLS%..\..\" "VC\bin\vcvarsx86_amd64.bat"
    IF ERRORLEVEL == 1 EXIT /B 0
    CALL :FINDANDCALL "Visual Studio 2008" "%VS90COMNTOOLS%..\..\" "VC\bin\vcvarsx86_amd64.bat"
    IF ERRORLEVEL == 1 EXIT /B 0
    CALL :FINDANDCALL "Visual Studio 2005" "%VS80COMNTOOLS%..\..\" "VC\bin\vcvarsx86_amd64.bat"
    IF ERRORLEVEL == 1 EXIT /B 0
  ) ELSE IF "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    CALL :FINDANDCALL "Visual Studio 2010" "%VS100COMNTOOLS%..\..\" "VC\bin\vcvarsamd64.bat"
    IF ERRORLEVEL == 1 EXIT /B 0
    CALL :FINDANDCALL "Visual Studio 2008" "%VS90COMNTOOLS%..\..\" "VC\bin\vcvarsamd64.bat"
    IF ERRORLEVEL == 1 EXIT /B 0
    CALL :FINDANDCALL "Visual Studio 2005" "%VS80COMNTOOLS%..\..\" "VC\bin\vcvarsamd64.bat"
    IF ERRORLEVEL == 1 EXIT /B 0
  ) ELSE (
    ECHO Unknown processor architecture %PROCESSOR_ARCHITECTURE%! >&2
    EXIT /B 1
  )
  CALL :FINDANDCALL "Microsoft SDK 7.1" "%ProgramFiles%\Microsoft SDKs\Windows\v7.1\" "Bin\SetEnv.cmd" /x64 /xp
  IF ERRORLEVEL == 1 EXIT /B 0
  CALL :FINDANDCALL "Microsoft SDK 7.0" "%ProgramFiles%\Microsoft SDKs\Windows\v7.0\" "Bin\SetEnv.cmd" /x64 /xp
  IF ERRORLEVEL == 1 EXIT /B 0
  ECHO Could not find a known x64 build environment!>&2
  EXIT /B 1

:FINDANDCALL
  IF EXIST "%~2%~3" (
    ECHO MSBUILD: Using %~1 @ "%~f2"
    PUSHD "%~2\"
    :: Some errors will get thrown because, well, this script sucks:
    CALL "%~2%~3" %4 %5 %6 %7 %8 %9 >nul 2>nul
    :: restore color
    COLOR
    POPD
    EXIT /B 1
  ) ELSE (
    EXIT /B 0
  )
