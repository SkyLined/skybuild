@ECHO OFF
:: Enable delayed environment variable expansion and command extensions, if not enabled already:
SETLOCAL ENABLEDELAYEDEXPANSION ENABLEEXTENSIONS
IF "%~1"=="x86" (
  CALL :SETENV32
) ELSE IF "%~1"=="x64" (
  CALL :SETENV64
) ELSE (
  ECHO Usage: MSBUILD architecture command arguments>&2
  ECHO Where:
  ECHO   architecture      - Target architecture ^(x86 or x64^),
  ECHO   command arguments - Command to execute ^(eg CL, LINK, DUMPBIN^) and arguments.
  ENDLOCAL
  EXIT /B 1
)
:: If no argument is specified, keep the local environment and exit:
IF "%~2" == "" IF "%2" == "" (
  CMD /K PROMPT MSBUILD $P$G
  EXIT /B 0
)
:: I would like to do a "SHIFT /1 & %*" to remove the first argument and execute arguments %2 and upwards as a command.
:: Unfortunately, SHIFT does not seem to affect %* at all, so we have to work around this by remove this first 
:: four characters from %*, because the first argument is always three characters and separated by one space from the
:: second argument:
SET command=%*
SET command=!command:~4!
!command!
IF ERRORLEVEL 1 (
  :: On Windows XP, errorlevel is not passed on correctly for unknown reasons. This means that "build.py" will not be
  :: able to detect the a problem during building. To fix this issue, a CRLF is output to stderr: if "build.py" sees
  :: ANY output to stderr, it assumes the build failed and report the problem.
  ENDLOCAL
  ECHO ERROR>&2
  EXIT /B 1
)
ENDLOCAL
EXIT /B 0

:SETENV32
  IF EXIST "%VS80COMNTOOLS%vsvars32.bat" (
    CALL "%VS80COMNTOOLS%vsvars32.bat" >nul
  ) ELSE IF EXIST "%ProgramFiles%\Microsoft SDKs\Windows\v7.0\Bin\SetEnv.cmd" (
    PUSHD "%ProgramFiles%\Microsoft SDKs\Windows\v7.0\"
    :: Some errors will get thrown because, well, this script sucks:
    CALL "%ProgramFiles%\Microsoft SDKs\Windows\v7.0\Bin\SetEnv.cmd" /x86 /xp >nul 2>nul
    :: restore color
    COLOR
    POPD
  ) ELSE (
    ECHO Could not find a known build environment ^(Visual Studio 8.0 or Windows SDK 7.0^)!>&2
    ENDLOCAL
    EXIT /B 1
  )
  EXIT /B 0

:SETENV64
  IF EXIST "%ProgramFiles%\Microsoft SDKs\Windows\v7.0\Bin\SetEnv.cmd" (
    PUSHD "%ProgramFiles%\Microsoft SDKs\Windows\v7.0\"
    :: Some errors will get thrown because, well, this script sucks:
    CALL "C:\Program Files\Microsoft SDKs\Windows\v7.0\Bin\SetEnv.cmd" /x64 /xp >nul 2>nul
    :: restore color
    COLOR
    POPD
  ) ELSE IF "%PROCESSOR_ARCHITECTURE%"=="x86" (
    :: On x86 use cross compiler if it can be found:
    IF EXIST "%ProgramFiles%\Microsoft Visual Studio 9.0\VC\bin\vcvarsx86_amd64.bat" (
      CALL "%ProgramFiles%\Microsoft Visual Studio 9.0\VC\bin\vcvarsx86_amd64.bat" >nul
    ) ELSE (
      ENDLOCAL
      ECHO Cannot find x64 cross compiler! >&2
      EXIT /B 1
    )
  ) ELSE IF "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    IF EXIST "%ProgramFiles(x86)%\Microsoft Visual Studio 8\VC\bin\amd64\vcvarsamd64.bat" (
      CALL "%ProgramFiles(x86)%\Microsoft Visual Studio 8\VC\bin\amd64\vcvarsamd64.bat" >nul
    ) ELSE (
      ENDLOCAL
      ECHO Cannot find x64 compiler! >&2
      EXIT /B 1
    )
  )
  EXIT /B 0
