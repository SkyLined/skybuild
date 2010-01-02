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
import os, re, subprocess, sys, time;
import command_line_options;

g_verbose_output = False;
g_loop_on_error = False;
g_create_build_config_files = False;

def find_in_path(filename):
  for path in os.environ["PATH"].split(";"):
    filepath = os.path.join(path, filename);
    if os.path.isfile(filepath):
      return filepath;
  print >>sys.stderr, "\"%s\" not found." % filename;
  exit(1);

LOCAL_PATH = os.path.dirname(sys.argv[0]);         # Path of build.py
NASM = find_in_path("nasm.exe");
MSBUILD = find_in_path("MSBUILD.cmd");

BUILD_SCRIPTS = ["build.cmd", "build.sh"];
BUILD_CONFIG_FILE = "build_config.py";
BUILD_INFO_FILE = "build_info.txt";
BUILD_NUMBER_HEADER = "build number:";
TIMESTAMP_HEADER = "Timestamp:";
DEFAULT_VERSION = "0.1 alpha";

valid_build_options = {
    "version": None, 
    "verbose": [True, False], 
    "folders": None, 
    "projects": None, 
    "architecture": ["x86", "x64"],
    "debug": [True, False],
    "defines": None,
    "prebuild commands": None, 
    "postbuild commands": None,
    "test commands": None, 
    "finish commands": None
};
required_build_options = [];
valid_project_options = {
    "version": None, 
    "files": None, 
    "dependencies": None,
    "architecture": ["x86", "x64"],
    "debug": [True, False],
    "defines": None,
    "prebuild commands": None, 
    "postbuild commands": None,
    "test commands": None, 
    "finish commands": None
};
required_project_options = [
    "files"
];
valid_file_options = {
    "sources": None,
    "entry point": None, 
    "architecture": ["x86", "x64"],
    "subsystem": ["windows", "console"],
    "cleanup": [True, False],
    "debug": [True, False],
    "defines": None,
    "prebuild commands": None, 
    "postbuild commands": None,
    "test commands": None, 
    "finish commands": None
};
required_file_options = [
    "sources"
];

def GetOption(name, default_value, *configs):
  for config in configs:
    if config and name in config:
      return config[name];
  return default_value;

def CheckConfigOptions(config, name, required_options, valid_options):
  # Check if required options are there:
  if required_options:
    for required_option in required_options:
      # We can require one option or one of a set of options, the later is handled here:
      if type(required_option) == type([]):
        for require_one_of_option in required_option:
          if require_one_of_option in config:
            break;
        else:
          missing_options = "\"%s\" or \"%s\"" % ("\", \"".join(required_option[:-1]), required_option[-1]);
          print >>sys.stderr, "  * Missing at least one of %s options for %s." % (missing_options, name);
          return False;
      # ...the former is handled here:
      elif required_option not in config:
        print >>sys.stderr, "  * Missing \"%s\" option for %s." % (required_option, name);
        return False;
  # Check if there are any unknown options:
  if valid_options:
    for option_name in config:
      if option_name not in valid_options.keys():
        print >>sys.stderr, "  * Unknown option \"%s\" for %s." % (option_name, name);
        return False;
      if valid_options[option_name] and config[option_name] not in valid_options[option_name]:
        print >>sys.stderr, "  * Invalid option \"%s\"=%s for %s." % (option_name, config[option_name], name);
        return False;
  return True;

def LongPath(path = None, *sub_paths):
  if not path or path == ".":
    path = os.getcwdu();
  for sub_path in sub_paths:
    path = os.path.join(path, sub_path);
  # Turn relative paths into absolute paths and normalize the path
  path = os.path.abspath(path);
  # Win32 has issues with paths > MAX_PATH. The string '\\?\' allows us to work
  # around MAX_PATH limitations in most cases. One example for which this does 
  # not work is os.chdir(). No other limitations are currently known.
  # http://msdn.microsoft.com/en-us/gozerlib.ary/aa365247.aspx
  if (sys.platform == "win32") and not path.startswith(u"\\\\?\\"):
    path = u"\\\\?\\" + path;
    if not path.endswith(os.sep) and os.path.isdir(path):
      # os.listdir does not work if the path is not terminated with a slash:
      path += os.sep;
  return path;

def ShortName(path = None, *sub_paths):
  if not path or path == ".":
    path = os.getcwdu();
  for sub_path in sub_paths:
    path = os.path.join(path, sub_path);
  # Turn relative paths into absolute paths and normalize the path
  path = os.path.abspath(path);
  if path.endswith(os.sep):
    path = path[:-1];
  if path.find(os.sep) == path.rfind(os.sep):
    if path.startswith(u"\\\\?\\"):
      return path[4:];
    if path == "":
      return os.sep;
    return path;
  return path[path.rfind(os.sep) + 1:];

def ShortPath(path, *sub_paths):
  path = LongPath(path, *sub_paths);
  if sys.platform == "win32":
    if path.startswith(u"\\\\?\\"):   # Long path marker?
      path = path[4:];                # Yes: strip
    if path[:2] != os.getcwd()[:2]:   # Different drive?
      return path;                    # Yes: absolute path
  return os.path.relpath(path, os.getcwd());

def ReadFile(path):
  assert os.path.isfile(path), "File \"%s\" not found!" % path;
  fd = open(path, "rb");
  try:
    return fd.read();
  finally:
    fd.close();

def WriteFile(path, contents):
  fd = open(path, "wb");
  try:
    return fd.write(contents);
  finally:
    fd.close();

def Main():
  global g_verbose_output, g_loop_on_error, g_create_build_config_files;
  options = command_line_options.CommandLineOptions(
    application_name = 'build',
    help_message = """
build - builds all projects in the current or given path, according to a build
configuration found in the %s file in each folder. If no build configuration
file is found, a default build configuration is generated and used.""",
    help_notes = """
Notes:
  The default build configuration that is generated will build all .asm files
  into .bin files and all .c files into .exe files, unles there is a .asm file
  and a .c file with the same name, in that case it will build both files into
  one .exe file.""",
    arguments = {
      'path': {
        'help': 'Path of the folder to build.',
        'initial': os.getcwd(), 
        'required': False
      }
    },
    switches = {
      'verbose': {
        'short': 'v',
        'help': 'Output verbose information while building.',
        'initial': 'false', 
        'default': 'true',
        'valid': command_line_options.BOOLEAN_SWITCH_VALUES
      },
      'loop': {
        'short': 'l',
        'help': ('If there is an error during build, pause to allow the '
                 'user to fix the issue and then press ENTER to attempt '
                 'building again.'),
        'initial': 'true',
        'default': 'true',
        'valid': command_line_options.BOOLEAN_SWITCH_VALUES
      },
      'create': {
        'short': 'c',
        'help': 'If no build config file or script is found, create one.',
        'initial': 'true',
        'default': 'true',
        'valid': command_line_options.BOOLEAN_SWITCH_VALUES
      }
    }
  );
  valid_arguments, continue_execution = options.ParseArguments(sys.argv[1:]);
  if not continue_execution:
    return valid_arguments;
  path = LongPath(options.GetArgumentValue('path'));
  g_verbose_output            = options.GetSwitchValue('verbose');
  g_loop_on_error             = options.GetSwitchValue('loop');
  g_create_build_config_files = options.GetSwitchValue('create');

  while (1):
    if not BuildFolder(path):
      print "@ Build failed.";
      if not g_loop_on_error:
        return False;
    else:
      print "@ Build successful.";
      return True;
    print "Press CTRL+C to terminate or ENTER to retry...";
    raw_input();

def ReadWriteBuildInfo(path):
  if os.path.isfile(os.path.join(path, BUILD_INFO_FILE)):
    build_timestamp_txt = ReadFile(os.path.join(path, BUILD_INFO_FILE));
    build_number_start = build_timestamp_txt.find(BUILD_NUMBER_HEADER);
    if build_number_start == -1:
      print >>sys.stderr, "  * %s is missing build number." % (BUILD_INFO_FILE, ShortName(path));
      return False;
    build_number_start += len(BUILD_NUMBER_HEADER);
    try:
      previous_build_number = int(re.sub(r"^\s*(\d+)[\s\S]*$", r"\1", build_timestamp_txt[build_number_start:]));
    except ValueError:
      print >>sys.stderr, "  * %s has corrupt build number." % (BUILD_INFO_FILE, ShortName(path));
      return False;
    build_number = previous_build_number + 1;
  else:
    build_number = 1;
  timestamp = time.strftime("%a, %d %b %Y %H:%M:%S (UTC)", time.gmtime());
  WriteFile(os.path.join(path, BUILD_INFO_FILE),
      "This file is automatically generated by the build system to keep track of the\r\n" +
      "build number and save the timestamp of the last build.\r\n" +
      "%s %s\r\n" % (BUILD_NUMBER_HEADER, build_number) +
      "%s %s\r\n" % (TIMESTAMP_HEADER, timestamp));
  return {"number": "%s" % build_number, "timestamp": timestamp};

def ReadBuildConfig(path):
  if not os.path.isfile(os.path.join(path, BUILD_CONFIG_FILE)):
    build_config = GenerateBuildConfig(path)
    if not build_config:
      return None;
  else:
    print >>sys.stderr, "  @ Reading build configuration.";
    build_config_py = re.sub(r"[\r\n]+", "\n", ReadFile(os.path.join(path, BUILD_CONFIG_FILE)));
    build_config_exec_result = {};
    try:
      exec(build_config_py, build_config_exec_result);
    except SyntaxError, e:
      try:
        # Try to construct a human readable error message
        error_messages = [
            "  * Syntax error in \"%s\" on line #%s, character %s:" % (
                os.path.join(ShortName(path), BUILD_CONFIG_FILE), e.lineno, e.offset),
            "    ->%s" % re.sub(r"[\r\n]*$", "", e.text) ];
      except:
        print >>sys.stderr, "  * Syntax error in \"%s\":" % BUILD_CONFIG_FILE;
        # Something went wrong, re-raise the original exception
        raise e;
      else:
        for error_message in error_messages:
          print >>sys.stderr, error_message;
        return None;
    if not CheckConfigOptions(build_config_exec_result, "\"%s\"" % BUILD_CONFIG_FILE, ["build_config"], None):
      return None;
    build_config = build_config_exec_result["build_config"];
    if not CheckConfigOptions(build_config, "\"%s\"" % BUILD_CONFIG_FILE, required_build_options, valid_build_options):
      return None;
  return build_config;

def GenerateBuildConfig(path, sub_folder = False):
  folders = []; folders_lines = [];
  files   = {}; files_lines = [];
  if not sub_folder:
    print "  @ Generating build configuration.";
  folder_has_targets = False;
  for file_or_folder in os.listdir(path):
    if os.path.isfile(os.path.join(path, file_or_folder)):
      source_filename = file_or_folder;
      source_filename_without_extension = re.sub(r"\.[^\.]+$", "", source_filename);
      if source_filename.endswith(".asm"):
        if os.path.isfile(os.path.join(path, source_filename_without_extension + ".c")):
          # Both .c and .asm exist; assume they need to be build and linked into one .exe:
          target = source_filename_without_extension + "_asm.obj"
        else:
          target = source_filename_without_extension + ".bin"
      elif source_filename.endswith(".c") or source_filename.endswith(".cpp"):
        if os.path.isfile(os.path.join(path, source_filename_without_extension + ".asm")):
          # Both .c/.cpp and .asm exist; assume they need to be build and linked into one .exe:
          target = source_filename_without_extension + "_c.obj";
          sources2 = [target, source_filename_without_extension + "_asm.obj"];
        else:
          target = source_filename_without_extension + ".obj";
          sources2 = [target];
        target2 = source_filename_without_extension + ".exe";
        files[target2] = {"sources": sources2};
        files_lines += ["        %s: {" % repr(target2)];
        files_lines += ["          \"sources\": %s" % repr(sources2)];
        files_lines += ["        },"];
      else:
        continue;
      files[target] = {"sources": [source_filename]};
      files_lines += ["        %s: {" % repr(target)];
      files_lines += ["          \"sources\": [%s]" % repr(source_filename)];
      files_lines += ["        },"];
      folder_has_targets = True;
    elif os.path.isdir(os.path.join(path, file_or_folder)):
      child_folder = file_or_folder;
      # We do not want to add ".svn" folders and such!
      if not child_folder.startswith("."):
        # Only if there is something to build in the child folder or its children, do we add it to the build config:
        for build_script in BUILD_SCRIPTS:
          # Does the child folder have a build script?
          if os.path.isfile(os.path.join(path, child_folder, build_script)):
            folders += [child_folder];
            folders_lines += ["    %s," % repr(child_folder)];
            folder_has_targets = True;
            break;
        else:
          # Does the child folder have a BUILD_CONFIG_FILE or can we create one (only returns true if there is something
          # to build in the child folder or its children):
          if (os.path.isfile(os.path.join(path, child_folder, BUILD_CONFIG_FILE))
              or GenerateBuildConfig(os.path.join(path, child_folder), sub_folder = True)):
            folders += [child_folder];
            folders_lines += ["    %s," % repr(child_folder)];
            folder_has_targets = True;
    else:
      print >>sys.stderr, "  * \"%s\" is neither a file or a folder!?" % ShortPath(os.path.join(path, file_or_folder));
      return False;
  if not folder_has_targets:
    if sub_folder:
      # If this is request to create a build config for a sub-folder and there is nothing to build in this folder or
      # any of its sub-folders, we will not create a build config:
      return None;
    print >>sys.stderr, "  * Found nothing to build in \"%s\"." % ShortPath(path);
    return None;
  project_name = ShortPath(path);
  if project_name == ".":
    project_name = ShortName(path);
  build_config = {}
  build_config_lines = ["build_config = {"];
  if not sub_folder:
    build_config["version"] = DEFAULT_VERSION;
    build_config_lines += ["  \"version\": %s," % repr(DEFAULT_VERSION)];
  if folders_lines:
    folders_lines[-1] = folders_lines[-1][:-1]; # last line has a comma that we'll remove.
    build_config["folders"] = folders;
    build_config_lines += [
      "  \"folders\": ["] + folders_lines + [
      "  ],"];
  if files_lines:
    build_config_lines += [
      "  \"projects\": {",
      "    %s: {" % repr(project_name)];
    build_config["projects"] = {project_name: {"files": files}};
    files_lines[-1] = files_lines[-1][:-1];     # last line has a comma that we'll remove.
    build_config_lines += [
      "      \"files\": {"] + files_lines + [
      "      }",
      "    }",
      "  },"];
  build_config_lines[-1] = build_config_lines[-1][:-1]; # last line has a comma that we'll remove.
  build_config_lines += [
    "}"];
  if g_create_build_config_files:
    build_config_py = open(os.path.join(path, BUILD_CONFIG_FILE), "wb");
    if build_config_py is None:
      print >>sys.stderr, "  * Creating file \"%s\" failed." % os.path.join(path, BUILD_CONFIG_FILE);
      return False;
    try:
      build_config_py.write("\r\n".join(build_config_lines + [""]));
    except:
      print >>sys.stderr, "  * Creating file \"%s\" failed." % os.path.join(path, BUILD_CONFIG_FILE);
      return False;
    finally:
      build_config_py.close();
  return build_config;

def BuildFolder(path, build_info = None, root_folder_build_config = None):
  global g_verbose_output;
  saved_path = os.getcwd();
  short_path = ShortPath(path);
  print "== %s ==" % ShortName(path);
  if not os.path.isdir(short_path):
    print >>sys.stderr, "  @ Folder \"%s\" not found!" % short_path;
    return False;
  os.chdir(short_path);
  try:
    if build_info is None:
      # Read build info and update build number and timestamp:
      build_info = ReadWriteBuildInfo(path);
      if not build_info:
        print >>sys.stderr, "  * Getting/setting build number and timestamp failed.";
        return False;
    for build_script in BUILD_SCRIPTS:
      if os.path.isfile(build_script):
        return RunApplication(build_script, [build_info["number"], build_info["timestamp"]], pipe_stdout = False);
    build_config = ReadBuildConfig(path);
    if build_config is None:
      return False;
    build_info["version"] = GetOption("version", DEFAULT_VERSION, build_config, root_folder_build_config);
    print "  @ Version %s, build %s, started at %s" % (
        build_info["version"], build_info["number"], build_info["timestamp"])
    if not root_folder_build_config:
      root_folder_build_config = build_config;
    # Switch on g_verbose_output output if requested.
    if "g_verbose_output" in build_config:
      g_verbose_output = build_config["g_verbose_output"];
    # See if we need to build sub-folders:
    child_folders = GetOption("folders", None, build_config);
    if child_folders is not None:
      print "  @ Building child folders:";
      for child_folder in child_folders:
        if not BuildFolder(os.path.join(path, child_folder), build_info, root_folder_build_config):
          return False;
      print "== %s ==" % ShortName(path);
      print "  @ Child folders built successful.";
    # Start building this folder:
    # Optionally run prebuild commands:
    if not DoPrebuildCommands(build_config, "  "):
      return False;
    project_configs = GetOption("projects", [], build_config);
    projects_built = [];
    while (len(projects_built) < len(project_configs)):
      progress = False;
      # For each project in the build configuration:
      for project_name, project_config in project_configs.items():
        # If this project has already been built, continue with the next project:
        if project_name in projects_built: continue;
        # Check if all options are valid
        if not CheckConfigOptions(project_config, "project \"%s\"" % project_name, 
            required_project_options, valid_project_options):
          CleanupFolder(path, build_info, build_config, clean_all = True);
          return False;
        # For each project that this project depends on:
        wait_for_dependencees = False;
        if "dependencies" in project_config:
          for dependee_project_name in project_config["dependencies"]:
            # The dependee must be a project in the build configuration, or it can never be build:
            if dependee_project_name not in project_configs:
              print >>sys.stderr, "    * Unknown dependee project \"%s\" for project \"%s\"." % (
                  dependee_project_name, project_name);
              CleanupFolder(path, build_info, build_config, clean_all = True);
              return False;
            # Check if the dependee has already been built:
            elif not dependee_project_name in projects_built:
              # No; we cannot built this project yet until the dependee is built.
              if g_verbose_output: print "    - Waiting for \"%s\"..." % dependee_project_name;
              wait_for_dependencees = True;
              break;
        if not wait_for_dependencees:
          # All dependees have been built; we can build this project:
          if not BuildProject(path, build_info, build_config, project_config, project_name):
            CleanupFolder(path, build_info, build_config, clean_all = True);
            print "    @ Project build failed.";
            return False;
          print "    @ Project build successful.";
          # Mark the project as built:
          projects_built += [project_name];
          progress = True;
      # If there are circular dependencies, this loop will stop making progress before all projects have been build:
      if not progress:
        # Show information about the circular dependencies found and exit:
        # For each project in the build configuration:
        for project_name, project_config in project_configs.items():
          # If it has not been built, it must have circular dependencies:
          if project_name not in projects_built:
            print >>sys.stderr, "  * Circular dependencies for project \"%s\":" % project_name;
            # For each dependee project for this project:
            for dependee_project_name in project_config["dependencies"]:
              # Projects mentioned in the build configuration that have not been built cause circular dependencies:
              if not dependee_project_name in projects_built:
                print >>sys.stderr, "    * %s:" % dependee_project_name;
        CleanupFolder(path, build_info, build_config, clean_all = True);
        return False;
    # Optionally run postbuild/test/finish commands:
    if not DoPostbuildTestFinishCommands(build_config, "  "):
      CleanupFolder(path, build_info, build_config, clean_all = True);
      return False;
    CleanupFolder(path, build_info, build_config, clean_all = False);
    return True;
  finally:
    os.chdir(saved_path);

def CleanupFolder(path, build_info, build_config, clean_all = False):
  if clean_all:
    project_configs = GetOption("projects", None, build_config);
    for project_name, project_config in project_configs.items():
      CleanupProject(path, build_info, build_config, project_config, project_name, clean_all = True);
  for pdb_file_name in ["vc80.pdb", "vc90.pdb"]:
    if os.path.isfile(os.path.join(path, pdb_file_name)):
      print "  - Cleanup: %s" % pdb_file_name;
      try:
        os.remove(os.path.join(path, pdb_file_name));
      except OSError:
        print >>sys.stderr, "    * Cannot cleanup intermediate file \"%s\"." % pdb_file_name;
        return False;
  return True;

def BuildProject(path, build_info, build_config, project_config, project_name):
  print "  [%s]" % project_name;
  build_info["project"] = project_name;
  project_version = GetOption("version", None, project_config);
  if project_version:
    build_info["version"] = project_version;
    print "    @ Version %s" % build_info["version"];
  else:
    build_info["version"] = GetOption("version", None, build_config);
  # Optionally run prebuild commands:
  if not DoPrebuildCommands(project_config, "    "):
    return False;
  file_configs = GetOption("files", None, project_config);
  files_built = [];
  while (len(files_built) < len(file_configs)):
    progress = False;
    # For each file in the build configuration:
    for file_name, file_config in file_configs.items():
      # If this file has already been built, continue with the next file:
      if file_name in files_built: continue;
      # Check if all options are valid
      if not CheckConfigOptions(file_config, "file \"%s\"" % file_name, required_file_options, valid_file_options):
        return False;
      # For each source file required for building this file:
      wait_for_sources = False;
      for source_file_name in file_config["sources"]:
        # If this file is not mentioned in the build configuration, it must be a static source file:
        if source_file_name not in file_configs:
          # Check if the source file exists:
          if not os.path.isfile(os.path.join(path, source_file_name)):
            print >>sys.stderr, "    * Missing source file \"%s\" for for \"%s\"." % (source_file_name, file_name);
            return False;
        # If this file is mentioned in the build configuration, see if it has already been built:
        elif not source_file_name in files_built:
          # No; we cannot built this file yet because its sources have not all been built yet.
          if g_verbose_output: print "      - Waiting for \"%s\"..." % source_file_name;
          wait_for_sources = True;
          break;
      if not wait_for_sources:
        # All sources have been built; we can build this file:
        if not BuildFile(path, build_info, build_config, project_config, file_config, file_name):
          return False;
        # Mark the file as built:
        files_built += [file_name];
        progress = True;
    # If there are circular dependencies, this loop will stop making progress before all files have been build:
    if not progress:
      # Show information about the circular dependencies found and exit:
      # For each file in the build configuration:
      for file_name, file_config in file_configs.items():
        # If it has not been built, it must have circular dependencies:
        if file_name not in files_built:
          print >>sys.stderr, "  * Circular dependencies for \"%s\":" % file_name;
          # For each source file required for building this file:
          for source_file_name in file_config["sources"]:
            # Files mentioned in the build configuration that have not been built cause circular dependencies:
            if source_file_name in file_configs and not source_file_name in files_built:
              print >>sys.stderr, "    * %s:" % source_file_name;
      return False;
  if not DoPostbuildTestFinishCommands(project_config, "    "):
    return False;
  if not CleanupProject(path, build_info, build_config, project_config, project_name):
    return False;
  return True;

def CleanupProject(path, build_info, build_config, project_config, project_name, clean_all = False):
  cleanup_errors = False;
  file_configs = GetOption("files", None, project_config);
  for file_name, file_config in file_configs.items():
    if "cleanup" in file_config:
      # If cleanup is specified, use that setting:
      cleanup = file_config["cleanup"] == True;
    else:
      # Otherwise default to True for .obj files and False for other files:
      cleanup = re.match(r".*\.obj$", file_name, re.IGNORECASE) is not None;
    if os.path.isfile(os.path.join(path, file_name)) and (cleanup or clean_all):
      print "    - Cleanup: %s" % file_name;
      try:
        os.remove(os.path.join(path, file_name));
      except OSError:
        print >>sys.stderr, "  * Cannot cleanup intermediate file \"%s\"." % file_name;
        cleanup_errors = True;
  return not cleanup_errors;

def BuildFile(path, build_info, build_config, project_config, file_config, file_name):
  print "    + Build: %s" % file_name;
  # Find out what types of source this file is to be build from:
  target_is_bin = re.match(r".*\.bin$", file_name, re.IGNORECASE) is not None;
  target_is_dll = re.match(r".*\.dll$", file_name, re.IGNORECASE) is not None;
  target_is_exe = re.match(r".*\.exe$", file_name, re.IGNORECASE) is not None;
  target_is_obj = re.match(r".*\.obj$", file_name, re.IGNORECASE) is not None;
  if not (target_is_bin or target_is_dll or target_is_exe or target_is_obj):
    print >>sys.stderr, "  * Unknown type of output file: \"%s\"." % file_name;
    return False;
  sources_includes_asm = False;
  sources_includes_c   = False;
  sources_includes_cpp = False;
  sources_includes_obj = False;
  sources_includes_def = False;
  # For each source file required for building this file:
  for source_file_name in file_config["sources"]:
    if not re.match(r".*\.(asm|c|cpp|obj|def)$", source_file_name, re.IGNORECASE):
      print >>sys.stderr, "  * Unknown type of source file for \"%s\": \"%s\"." % (file_name, source_file_name);
      return False;
    sources_includes_asm |= re.match(r".*\.asm$", source_file_name, re.IGNORECASE) is not None;
    sources_includes_c   |= re.match(r".*\.c$",   source_file_name, re.IGNORECASE) is not None;
    sources_includes_cpp |= re.match(r".*\.cpp$", source_file_name, re.IGNORECASE) is not None;
    sources_includes_obj |= re.match(r".*\.obj$", source_file_name, re.IGNORECASE) is not None;
    sources_includes_def |= re.match(r".*\.def$", source_file_name, re.IGNORECASE) is not None;
  # Check for some impossible combination of sources and targets:
  if sources_includes_c and sources_includes_asm:
    print >>sys.stderr, "  * Both .c and .asm source files found for \"%s\"." % file_name;
    print >>sys.stderr, "    A file can be build from either .c or .asm source files, not both.";
    return False;
  if sources_includes_cpp and sources_includes_asm:
    print >>sys.stderr, "  * Both .cpp and .asm source files found for \"%s\"." % file_name;
    print >>sys.stderr, "    A file can be build from either .cpp or .asm source files, not both.";
    return False;
  if sources_includes_c and sources_includes_cpp:
    print >>sys.stderr, "  * Both .c and .cpp source files found for \"%s\"." % file_name;
    print >>sys.stderr, "    A file can be build from either .c or .cpp source files, not both.";
    return False;
  if sources_includes_def and not target_is_dll:
    print >>sys.stderr, "  * A .def source file found for \"%s\"." % file_name;
    print >>sys.stderr, "    Only a .dll file can be build from a .def file.";
    return False;
  if sources_includes_asm and (target_is_dll or target_is_exe):
    print >>sys.stderr, "  * Cannot generate .%s files from .asm source files for \"%s\"." % (
      {True:"dll", False:"exe"}[target_is_dll], file_name);
    return False;
  if (sources_includes_c or sources_includes_c) and target_is_bin:
    print >>sys.stderr, "  * Cannot generate .bin files from .c/.cpp source files for \"%s\"." % file_name;
    return False;
  if not (sources_includes_c or sources_includes_cpp or sources_includes_asm) and (target_is_bin or target_is_obj):
    print >>sys.stderr, "  * Cannot generate .%s files from .obj source files for \"%s\"." % (
      {True:"bin", False:"obj"}[target_is_bin], file_name);
  # Parse architecture option if provided (default is x86):
  architecture = GetOption("architecture", "x86", file_config, project_config, build_config);
  if not architecture in ["x64", "x86"]:
    print >>sys.stderr, "  * Unknown architecture for \"%s\": \"%s\"." % (file_name, architecture);
    return False;
  # Parse subsystem option if provided (default is console):
  subsystem = GetOption("subsystem", "console", file_config, project_config, build_config);
  if not subsystem in ["console", "windows"]:
    print >>sys.stderr, "  * Unknown subsystem option for \"%s\": \"%s\"." % (file_name, subsystem);
    return False;
  # Parse debug option if provided (on by default for .exe and .dll targets):
  debug = GetOption("debug", target_is_exe or target_is_dll, file_config, project_config, build_config);
  if not debug in [True, False]:
    print >>sys.stderr, "  * Unknown debug option for \"%s\": \"%s\"." % (file_name, debug);
    return False;
  # Parse entry point option if provided (default is None: let the linker decide):
  entry_point = GetOption("entry point", None, file_config, project_config, build_config);

  # Parse defines options if provided:
  defines = {};
  for name, value in build_info.items():
    defines["BUILD_" + name.upper()] = value;
  for name, value in GetOption("defines", {}, build_config).items():
    defines[name] = value;
  for name, value in GetOption("defines", {}, project_config).items():
    defines[name] = value;
  for name, value in GetOption("defines", {}, file_config).items():
    defines[name] = value;
  if not debug in [True, False]:
    print >>sys.stderr, "  * Unknown debug option for \"%s\": \"%s\"." % (file_name, debug);
    return False;
  # Parse entry point option if provided (default is None: let the linker decide):
  entry_point = GetOption("entry point", None, file_config, project_config, build_config);

  # Optionally run prebuild commands:
  if not DoPrebuildCommands(file_config, "      "):
    return False;
  # Build the target
  if (target_is_obj or target_is_bin) and sources_includes_asm:
    # The source is assembler, use NASM:
    nasm_arguments = [];
    for source_file_name in file_config["sources"]:
      nasm_arguments += ["\"%s\"" % source_file_name];
    nasm_arguments += ["-w+error", "-o \"%s\"" % file_name];
    for name, value in defines.items():
      nasm_arguments += ["-D%s=\"%s\"" % (name, value)];
    if debug:
      nasm_arguments += ["-g"];
    if target_is_bin:
      nasm_arguments += ["-f bin"];
    elif target_is_obj:
      nasm_arguments += ["-f %s" % {"x86": "win32", "x64": "win64"}[architecture]];
    if not RunApplication(NASM, nasm_arguments):
      return False;
  elif (target_is_obj) and (sources_includes_c or sources_includes_cpp):
    # The source is C, use CL:
    cl_arguments = [];
    link_arguments = [];
    for source_file_name in file_config["sources"]:
      cl_arguments += ["\"%s\"" % source_file_name];
    cl_arguments += ["/c", "/nologo", "/WX", "/wd4996", "/wd4255", "/wd4826", "/wd4668", "/wd4820"];
    for name, value in defines.items():
      cl_arguments += ["/D%s=\"%s\"" % (name, value)];
    if debug:
      cl_arguments += ["/Zi"];
    if target_is_exe or target_is_dll:
      cl_arguments += ["/Fe\"%s\"" % file_name];
      if target_is_exe:
        link_arguments += ["/subsystem:%s" % subsystem];
      else:
        cl_arguments += ["/LD"];
    elif target_is_obj:
      cl_arguments += ["/Fo\"%s\"" % file_name];
    if link_arguments:
      cl_arguments += ["/link"];
      cl_arguments += link_arguments;
    msbuild_arguments = [architecture, "CL"] + cl_arguments;
    if not RunApplication(MSBUILD, msbuild_arguments):
      return False;
  elif (target_is_exe or target_is_dll) and sources_includes_obj:
    # The source is obj, use LINK:
    link_arguments = ["/NOLOGO", "/OUT:\"%s\"" % file_name];
    for source_file_name in file_config["sources"]:
      if re.match(r".*\.def$", source_file_name, re.IGNORECASE) is not None:
        link_arguments += ["/DEF:\"%s\"" % source_file_name];
      else:
        link_arguments += ["\"%s\"" % source_file_name];
    if entry_point:
      link_arguments += ["/entry:%s" % entry_point];
    if debug:
      link_arguments += ["/DEBUG"];
    if target_is_exe:
      link_arguments += ["/subsystem:%s" % subsystem];
    elif target_is_dll:
      link_arguments += ["/DLL"];
    msbuild_arguments = [architecture, "LINK"] + link_arguments;
    if not RunApplication(MSBUILD, msbuild_arguments):
      return False;
  else:
    print >>sys.stderr, "  * No handled file types in sources for \"%s\"." % file_name;
    return False;
  if not os.path.isfile(LongPath(path, file_name)):
    print >>sys.stderr, "  * The target file \"%s\" was not created, but the build command did not report an error." % (
        file_name);
    return False;
  # Optionally run postbuild/test/finish commands:
  if not DoPostbuildTestFinishCommands(file_config, "      "):
    return False;
  if not CleanupFile(path, file_name):
    return False;
  return True;

def CleanupFile(path, file_name, clean_all = False):
  cleanup_errors = False;
  if clean_all and os.path.isfile(os.path.join(path, file_name)):
    print "      - Cleanup: %s" % file_name;
    try:
      os.remove(os.path.join(path, file_name));
    except OSError:
      print >>sys.stderr, "    * Cannot cleanup file \"%s\"." % file_name;
      cleanup_errors = True;
  intermediate_file_names = [re.sub(r"\.[^\.]*$", ".ilk", file_name),
                             re.sub(r"\.[^\.]*$", ".exp", file_name),
                             re.sub(r"\.[^\.]*$", ".lib", file_name)];
  for intermediate_file_name in intermediate_file_names:
    if os.path.isfile(os.path.join(path, intermediate_file_name)):
      print "      - Cleanup: %s" % intermediate_file_name;
      try:
        os.remove(os.path.join(path, intermediate_file_name));
      except OSError:
        print >>sys.stderr, "    * Cannot cleanup intermediate file \"%s\"." % intermediate_file_name;
        cleanup_errors = True;
  return not cleanup_errors;

def DoPrebuildCommands(config, padding):
  # Optionally run prebuild commands:
  if "prebuild commands" in config:
    for prebuild_command in config["prebuild commands"]:
      print "%s+ Prebuild: %s" % (padding, file_name);
      if not RunApplication(prebuild_command, pipe_stdout = False):
        print >>sys.stderr, "%s* Prebuild command failed." % padding;
        return False;
  return True;

def DoPostbuildTestFinishCommands(config, padding):
  # Optionally run postbuild/test/finish commands:
  if "postbuild commands" in config:
    for postbuild_command in config["postbuild commands"]:
      print "%s+ Postbuild: %s" % (padding, postbuild_command);
      if not RunApplication(postbuild_command, pipe_stdout = False):
        print >>sys.stderr, "%s* Postbuild command failed." % padding;
        return False;
  if "test commands" in config:
    for test_command in config["test commands"]:
      print "%s+ Test: %s" % (padding, test_command);
      if not RunApplication(test_command, pipe_stdout = False):
        print >>sys.stderr, "%s* Test command failed." % padding;
        return False;
  if "finish commands" in config:
    for final_command in config["finish commands"]:
      print "%s+ Finish: %s" % (padding, final_command);
      if not RunApplication(final_command, pipe_stdout = False):
        print >>sys.stderr, "%s* Finish command failed." % padding;
        return False;
  return True;

def RunApplication(name, arguments=[], stdin="", pipe_stdout = True):
  command = "\"%s\" %s" % (name, " ".join(arguments));
  if g_verbose_output: print "      %s" % command;
  try:
    if pipe_stdout:
      popen = subprocess.Popen(command, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE);
    else:
      popen = subprocess.Popen(command, stdin = subprocess.PIPE,                           stderr = subprocess.PIPE);
  except WindowsError, e:
    if e.errno == 2:
      print >>sys.stderr, "  * Application \"%s\" not found." % name;
      return False;
    else:
      raise e;
  stdout_data, stderr_data = popen.communicate(stdin);
  returncode = popen.wait();
  if g_verbose_output: print "      ERRORLEVEL = %d" % returncode;
  if returncode != 0 or stderr_data != "":
    print >>sys.stderr, "  * %s returned error %d:" % (name, returncode);
    if stdout_data: print stdout_data;
    if stderr_data: print stderr_data;
    return False;
  if g_verbose_output: print "      STDOUT = %s" % repr(stdout_data);
  if g_verbose_output: print "      STDERR = %s" % repr(stderr_data);
  return True;

if __name__ == "__main__":
  result = Main();
  exit_code = {True:0, False:1}[result];
  exit(exit_code);