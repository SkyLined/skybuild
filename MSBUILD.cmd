::@ECHO OFF
:: Copyright (c) 2009-2010, Berend-Jan "SkyLined" Wever <berendjanwever@gmail.com>
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
CALL :SETENV %1
IF NOT ERRORLEVEL 1 (
  :: I would like to do a "SHIFT /1 & %*" to remove the first argument and execute arguments %2 and upwards as a command.
  :: Unfortunately, SHIFT does not seem to affect %* at all, so we have to work around this by remove this first 
  :: four characters from %*, because the first argument is always three characters and separated by one space from the
  :: second argument:
  SET command=
  :ARGS_LOOP
    IF "%~2" == "" GOTO :ARGS_DONE
    SET command=!command! %2
    ECHO ** !command!
    SHIFT
    GOTO :ARGS_LOOP
  :ARGS_DONE
  IF "!command!" == "" (
    :: If no argument is specified, start a new shell:
    SET command=CMD /K PROMPT MSBUILD !envtype! $P$G
  )
  ECHO [[!command!]]
  CALL !command!
)
SET result=%ERRORLEVEL%
IF NOT result == 0 (
  :: On Windows XP, errorlevel is not passed on correctly for unknown reasons. This means that "build.py" will not be
  :: able to detect the a problem during building. To fix this issue, a CRLF is output to stderr: if "build.py" sees
  :: ANY output to stderr, it assumes the build failed and report the problem.
  ECHO ERROR>&2
)

:: Once we ENDLOCAL we will lose all state, so the EXIT needs to be on the same line to allow %result% to be used:
ENDLOCAL & EXIT /B %result%

:SETENV
  IF "%PROCESSOR_ARCHITECTURE%"=="x86" (
    SET envtype32="x86"
    SET vcvars32="VC\bin\vcvars32.bat"
    SET SDKs32="%ProgramFiles%\Microsoft SDKs\Windows"
    SET envtype64="x64 on x86"
    SET vcvars64="VC\bin\x86_amd64\vcvarsx86_amd64.bat"
    SET SDKs64=:*:
  ) ELSE IF "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    SET envtype32="x86 on x64"
    SET vcvars32="VC\bin\vcvars32.bat"
    SET SDKs32="%ProgramFiles(x86)%\Microsoft SDKs\Windows"
    SET envtype64="x64"
    SET vcvars64="VC\bin\amd64\vcvarsamd64.bat"
    SET SDKs64="%ProgramFiles%\Microsoft SDKs\Windows"
  )

  IF "%~1"=="x86" (
    CALL :SETENV32
  ) ELSE IF "%~1"=="x64" (
    CALL :SETENV64
  ) ELSE IF "%~1"=="x86:VS8.0" (
    CALL :SETENV_VS80 !envtype32! !vcvars32!
  ) ELSE IF "%~1"=="x86:VS9.0" (
    CALL :SETENV_VS90 !envtype32! !vcvars32!
  ) ELSE IF "%~1"=="x86:VS10.0" (
    CALL :SETENV_VS100 !envtype32! !vcvars32!
  ) ELSE IF "%~1"=="x64:VS8.0" (
    CALL :SETENV_VS80 !envtype64! !vcvars64!
  ) ELSE IF "%~1"=="x64:VS9.0" (
    CALL :SETENV_VS90 !envtype64! !vcvars64!
  ) ELSE IF "%~1"=="x64:VS10.0" (
    CALL :SETENV_VS100 !envtype64! !vcvars64!
  ) ELSE IF "%~1"=="x86:SDK6.0A" (
    CALL :SETENV_SDK60A !envtype32! "x86"
  ) ELSE IF "%~1"=="x86:SDK7.0" (
    CALL :SETENV_SDK70 !envtype32! "x86"
  ) ELSE IF "%~1"=="x86:SDK7.1" (
    CALL :SETENV_SDK71 !envtype32! "x86"
  ) ELSE IF "%~1"=="x64:SDK6.0A" (
    CALL :SETENV_SDK60A !envtype64! "x64"
  ) ELSE IF "%~1"=="x64:SDK7.0" (
    CALL :SETENV_SDK70 !envtype64! "x64"
  ) ELSE IF "%~1"=="x64:SDK7.1" (
    CALL :SETENV_SDK71 !envtype64! "x64"
  ) ELSE (
    ECHO Usage: MSBUILD architecture[:environment] command arguments>&2
    ECHO Where:
    ECHO   architecture      - Target architecture ^(x86 or x64^),
    ECHO   environment       - Specify build environment and version ^(optional^).
    ECHO   command arguments - Command to execute ^(eg CL, LINK, DUMPBIN^) and arguments.
    ECHO.
    ECHO MSBUILD will automatically look for Visual Studio 8.0, 9.0, 10.0 and Windows
    ECHO SDK 6.0A, 7.0, 7.1 build environments and use the latest. If you have multiple
    ECHO build environments installed, you can specify which one to use together with
    ECHO the target architecture
    EXIT /B 1
  )
  IF ERRORLEVEL 1 (
    ECHO Could not find a suitable build environment!>&2
    EXIT /B %ERRORLEVEL%
  )
  EXIT /B 0

:SETENV32
  CALL :SETENV_VS !envtype32! !vcvars32!
  IF NOT ERRORLEVEL 1 EXIT /B 0
  CALL :SETENV32_SDK !envtype32! "x86"
  EXIT /B %ERRORLEVEL%

:SETENV64
  CALL :SETENV_VS !envtype64! !vcvars64!
  IF NOT ERRORLEVEL 1 EXIT /B 0
  CALL :SETENV_SDK !envtype64! "x64"
  EXIT /B %ERRORLEVEL%

:SETENV_VS
  CALL :SETENV_VS100 %1 %2
  IF NOT ERRORLEVEL 1 EXIT /B 0
  CALL :SETENV_VS90 %1 %2
  IF NOT ERRORLEVEL 1 EXIT /B 0
  CALL :SETENV_VS80 %1 %2
  EXIT /B %ERRORLEVEL%
:SETENV_VS100
  CALL :SETENV_VS_ "10.0" %1 "%VS100COMNTOOLS%..\..\" %2
  EXIT /B %ERRORLEVEL%
:SETENV_VS90
  CALL :SETENV_VS_ "9.0" %1 "%VS90COMNTOOLS%..\..\" %2
  EXIT /B %ERRORLEVEL%
:SETENV_VS80
  CALL :SETENV_VS_ "8.0" %1 "%VS80COMNTOOLS%..\..\" %2
  EXIT /B %ERRORLEVEL%
:SETENV_VS_
  CALL :FINDANDCALL "Visual Studio %~1 (%~2)" "%~3" %4
  EXIT /B %ERRORLEVEL%

:SETENV_SDK
  CALL :SETENV_SDK71 %1 %2
  IF NOT ERRORLEVEL 1 EXIT /B 0
  CALL :SETENV_SDK70 %1 %2
  IF NOT ERRORLEVEL 1 EXIT /B 0
  CALL :SETENV_SDK60A %1 %2
  EXIT /B %ERRORLEVEL%
:SETENV_SDK71
  CALL :SETENV_SDK_ "7.1" %1 "v7.1\" %2
  EXIT /B %ERRORLEVEL%
:SETENV_SDK70
  CALL :SETENV_SDK_ "7.0" %1 "v7.0\" %2
  EXIT /B %ERRORLEVEL%
:SETENV_SDK60A
  CALL :SETENV_SDK_ "6.0A" %1 "v6.0A\" %2
  EXIT /B %ERRORLEVEL%
:SETENV_SDK_
  CALL :FINDANDCALL "WinSDK %~1 (%~2)" "%ProgramFiles%\Microsoft SDKs\Windows\%~3" "Bin\SetEnv.cmd" /%~4 /xp
  EXIT /B %ERRORLEVEL%

:FINDANDCALL
  IF EXIST "%~2%~3" (
    PUSHD "%~2"
    :: Some errors will get thrown because, well, this script sucks:
    SET envtype=%1
    CALL "%~2%~3" %4 %5 %6 %7 %8 %9 >nul 2>nul
    :: restore color
    COLOR
    POPD
    EXIT /B 0
  ) ELSE (
    ECHO * Not found: "%~2%~3"
    EXIT /B 1
  )
