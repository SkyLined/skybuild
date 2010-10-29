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
g_clean_build = False;
g_dirty_build = False;

LOCAL_PATH = os.path.dirname(sys.argv[0]);         # Path of build.py

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
    "includes": None,
    "libs": None,
    "entry point": None, 
    "architecture": ["x86", "x64"],
    "subsystem": ["windows", "console"],
    "cleanup": [True, False],
    "debug": [True, False],
    "defines": None,
    "prebuild commands": None, 
    "build commands": None, 
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

def OsListDir(path):
  if sys.platform == "win32":
    return os.listdir(u'\\\\?\\' + os.path.abspath(path) + os.sep);
  else:
    return os.listdir(path);

def OsIsFile(path):
  if sys.platform == "win32":
    full_path = u'\\\\?\\' + os.path.abspath(path);
    try:
      os.listdir(full_path + os.sep); # If it is a dir it is not a folder
    except:
      return os.access(full_path, os.F_OK); # If it is not a folder and it exists, it is a file.
    else:
      return False;
  else:
    return os.path.isfile(path);

def OsDeleteFile(path):
  if sys.platform == "win32":
    return os.remove(u'\\\\?\\' + os.path.abspath(path));
  else:
    return os.remove(path);

def OsIsDir(path):
  if sys.platform == "win32":
    full_path = u'\\\\?\\' + os.path.abspath(path);
    try:
      os.listdir(full_path + os.sep);
    except:
      return False;
    else:
      return True;
  else:
    return os.path.isdir(path);

def OsChangeDir(path):
#  if sys.platform == "win32":
#    return os.chdir(u'\\\\?\\' + os.path.abspath(path));
#  else:
    return os.chdir(path);

def OsReadFile(path):
  if sys.platform == "win32":
    fd = open(u'\\\\?\\' + os.path.abspath(path), "rb");
  else:
    fd = open(path, "rb");
  try:
    return fd.read();
  finally:
    fd.close();

def OsWriteFile(path, contents):
  if sys.platform == "win32":
    fd = open(u'\\\\?\\' + os.path.abspath(path), "wb");
  else:
    fd = open(path, "wb");
  try:
    return fd.write(contents);
  finally:
    fd.close();

def Main():
  global g_verbose_output, g_loop_on_error, g_create_build_config_files, g_clean_build, g_dirty_build;
  options = command_line_options.CommandLineOptions(
    application_name = 'build',
    help_message = """
build - builds all projects in the current or given path, according to a build
configuration found in the %s file in each folder. If no build 
configuration file is found, a default build configuration is generated and 
used.""" % BUILD_CONFIG_FILE,
    help_notes = """
Notes:
  The default build configuration that is generated will build all .asm files
  into .bin files and all .c files into .exe files, unles there is a .asm file
  and a .c file with the same name, in that case it will build both files into
  one .exe file.""",
    arguments = {
      'path': {
        'help':     """Path of the folder to build. Use path#project if you only want to build one
project in a folder that contains more than one.""",
        'initial': os.getcwd(), 
        'required': False
      }
    },
    switches = {
      'verbose': {
        'short':    'v',
        'help':     'Output verbose information while building.',
        'initial':  'false', 
        'default':  'true',
        'valid':    command_line_options.BOOLEAN_SWITCH_VALUES
      },
      'loop': {
        'short':    'l',
        'help':     """If there is an error during build, pause to allow the user to fix the issue and
then press ENTER to attempt building again.""",
        'initial':  'true',
        'default':  'true',
        'valid':    command_line_options.BOOLEAN_SWITCH_VALUES
      },
      'create': {
        'short':    'c',
        'help':     'If no build config file or script is found, create one.',
        'initial':  'false',
        'default':  'true',
        'valid':    command_line_options.BOOLEAN_SWITCH_VALUES
      },
      'clean': {
        'short':    'n',
        'help':     'Do not clean up intermediate build files.',
        'initial':  'false',
        'default':  'true',
        'valid':    command_line_options.BOOLEAN_SWITCH_VALUES
      },
      'dirty': {
        'short':    'd',
        'help':     'Dirty build: do not clean up intermediate build files.',
        'initial':  'false',
        'default':  'true',
        'valid':    command_line_options.BOOLEAN_SWITCH_VALUES
      },
    },
  );
  valid_arguments, continue_execution = options.ParseArguments(sys.argv[1:]);
  if not continue_execution:
    return valid_arguments;
  path_project = options.GetArgumentValue('path').split("#", 1);
  if len(path_project) == 1:
    path_project.append(None);
  path, project = path_project;
  g_verbose_output            = options.GetSwitchValue('verbose');
  g_loop_on_error             = options.GetSwitchValue('loop');
  g_create_build_config_files = options.GetSwitchValue('create');
  g_clean_build               = options.GetSwitchValue('clean');
  g_dirty_build               = options.GetSwitchValue('dirty');

  while (1):
    if not BuildFolder(path, project):
      if g_clean_build:
        print "@ Clean failed.";
      else:
        print "@ Build failed.";
      if not g_loop_on_error:
        return False;
    else:
      if g_clean_build:
        print "@ Clean successful.";
      else:
        print "@ Build successful.";
      return True;
    print "Press CTRL+C to terminate or ENTER to retry...";
    raw_input();

def ReadWriteBuildInfo(path):
  build_info_path = os.path.join(path, BUILD_INFO_FILE);
  if OsIsFile(build_info_path):
    build_timestamp_txt = OsReadFile(build_info_path);
    build_number_start = build_timestamp_txt.find(BUILD_NUMBER_HEADER);
    if build_number_start == -1:
      print >>sys.stderr, "  * %s is missing build number." % build_info_path;
      return False;
    build_number_start += len(BUILD_NUMBER_HEADER);
    try:
      previous_build_number = int(re.sub(r"^\s*(\d+)[\s\S]*$", r"\1", build_timestamp_txt[build_number_start:]));
    except ValueError:
      print >>sys.stderr, "  * %s has corrupt build number." % build_info_path;
      return False;
    build_number = previous_build_number;
  else:
    build_number = 0;
  timestamp = time.strftime("%a, %d %b %Y %H:%M:%S (UTC)", time.gmtime());
  if not g_clean_build:
    build_number += 1;
    OsWriteFile(build_info_path,
        "This file is automatically generated by the build system to keep track of the\r\n" +
        "build number and save the timestamp of the last build.\r\n" +
        "%s %s\r\n" % (BUILD_NUMBER_HEADER, build_number) +
        "%s %s\r\n" % (TIMESTAMP_HEADER, timestamp));
  return {"number": "%s" % build_number, "timestamp": timestamp};

def ReadBuildConfig(path):
  build_config_path = os.path.join(path, BUILD_CONFIG_FILE);
  if not OsIsFile(build_config_path):
    build_config = GenerateBuildConfig(path)
    if not build_config:
      return None;
  else:
    print >>sys.stderr, "  @ Reading build configuration.";
    build_config_py = re.sub(r"[\r\n]+", "\n", OsReadFile(build_config_path));
    build_config_exec_result = {};
    try:
      exec(build_config_py, build_config_exec_result);
    except SyntaxError, e:
      try:
        # Try to construct a human readable error message
        error_messages = [
            "  * Syntax error in \"%s\" on line #%s, character %s:" % \
                (build_config_path, e.lineno, e.offset),
            "    ->%s" % re.sub(r"[\r\n]*$", "", e.text) ];
      except:
        print >>sys.stderr, "  * Syntax error in \"%s\":" % build_config_path;
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
  for file_or_folder in OsListDir(path):
    file_or_folder_path = os.path.join(path, file_or_folder);
    if OsIsFile(file_or_folder_path):
      source_filename = file_or_folder;
      source_filename_without_extension = re.sub(r"\.[^\.]+$", "", source_filename);
      if source_filename.endswith(".asm"):
        if OsIsFile(os.path.join(path, source_filename_without_extension + ".c")) \
            or OsIsFile(os.path.join(path, source_filename_without_extension + ".cpp")):
          # Both .c/.cpp and .asm exist; assume they need to be build and linked into one .exe:
          target = source_filename_without_extension + "_asm.obj"
        else:
          target = source_filename_without_extension + ".bin"
      elif source_filename.endswith(".c") or source_filename.endswith(".cpp"):
        if OsIsFile(os.path.join(path, source_filename_without_extension + ".asm")):
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
    elif OsIsDir(file_or_folder_path):
      child_folder = file_or_folder;
      # We do not want to add ".svn" folders and such!
      if not child_folder.startswith("."):
        # Only if there is something to build in the child folder or its children, do we add it to the build config:
        for build_script in BUILD_SCRIPTS:
          # Does the child folder have a build script?
          if OsIsFile(os.path.join(path, child_folder, build_script)):
            folders += [child_folder];
            folders_lines += ["    %s," % repr(child_folder)];
            folder_has_targets = True;
            break;
        else:
          # Does the child folder have a BUILD_CONFIG_FILE or can we create one (only returns true if there is something
          # to build in the child folder or its children):
          if OsIsFile(os.path.join(path, child_folder, BUILD_CONFIG_FILE)) \
              or GenerateBuildConfig(os.path.join(path, child_folder), sub_folder = True):
            folders += [child_folder];
            folders_lines += ["    %s," % repr(child_folder)];
            folder_has_targets = True;
    else:
      print >>sys.stderr, "  * \"%s\" is neither a file or a folder!?" % file_or_folder_path;
      return False;
  if not folder_has_targets:
    if sub_folder:
      # If this is request to create a build config for a sub-folder and there is nothing to build in this folder or
      # any of its sub-folders, we will not create a build config:
      return None;
    print >>sys.stderr, "  * Found nothing to build in \"%s\"." % path;
    return None;
  project_name = os.path.basename(path);
  if project_name == ".":
    project_name = os.path.basename(os.getcwd());
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
    try:
      build_config_path = os.path.join(path, BUILD_CONFIG_FILE);
      OsWriteFile(build_config_path, "\r\n".join(build_config_lines + [""]));
    except:
      print >>sys.stderr, "  * Creating file \"%s\" failed." % os.path.join(path, BUILD_CONFIG_FILE);
      return False;
  return build_config;

def BuildFolder(path, project, build_info = None, root_folder_build_config = None):
  saved_path = os.getcwd();
  print "== %s ==" % os.path.basename(path);
  if not OsIsDir(path):
    print >>sys.stderr, "  @ Folder \"%s\" not found!" % path;
    return False;
  OsChangeDir(path);
  try:
    if build_info is None:
      # Read build info and update build number and timestamp:
      build_info = ReadWriteBuildInfo(path);
      if not build_info:
        print >>sys.stderr, "  * Getting/setting build number and timestamp failed.";
        return False;
    for build_script in BUILD_SCRIPTS:
      if OsIsFile(build_script):
        return RunApplication(build_script, [build_info["number"], build_info["timestamp"]], pipe_stdout = False);
    build_config = ReadBuildConfig(path);
    if build_config is None:
      return False;
    if project is not None:
      # We will only be building one project
      if "projects" not in build_config:
        print >>sys.stderr, "  @ Build config contains no projects!";
        return False;
      if project not in build_config["projects"].values():
        print >>sys.stderr, "  @ Project \"%s\" not found!" % project;
        return False;
      build_config["projects"] = {project: build_config["projects"][project]};
    build_info["version"] = GetOption("version", DEFAULT_VERSION, build_config, root_folder_build_config);
    print "  @ Version %s, build %s, started at %s" % (
        build_info["version"], build_info["number"], build_info["timestamp"])
    if not root_folder_build_config:
      root_folder_build_config = build_config;
    # See if we need to build sub-folders:
    child_folders = GetOption("folders", None, build_config);
    if child_folders is not None:
      if g_clean_build:
        print "  @ Cleaning child folders:";
      else:
        print "  @ Building child folders:";
      for child_folder in child_folders:
        if not BuildFolder(os.path.join(path, child_folder), None, build_info, root_folder_build_config):
          return False;
      print "== %s ==" % os.path.basename(path);
      if g_clean_build:
        print "  @ Child folders cleaned successfully.";
      else:
        print "  @ Child folders built successfully.";
    # Start building this folder:
    # Optionally run prebuild commands:
    if not g_clean_build:
      if not DoPrebuildCommands(build_config, "  "):
        return False;
    project_configs = GetOption("projects", {}, build_config);
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
          if not g_dirty_build:
            CleanupFolder(path, build_info, build_config, clean_all = True);
          return False;
        # For each project that this project depends on:
        wait_for_dependencees = False;
        if not g_clean_build:
          if "dependencies" in project_config:
            for dependee_project_name in project_config["dependencies"]:
              # The dependee must be a project in the build configuration, or it can never be build:
              if dependee_project_name not in project_configs:
                print >>sys.stderr, "    * Unknown dependee project \"%s\" for project \"%s\"." % (
                    dependee_project_name, project_name);
                if not g_dirty_build:
                  CleanupFolder(path, build_info, build_config, clean_all = True);
                return False;
              # Check if the dependee has already been built:
              elif not dependee_project_name in projects_built:
                # No; we cannot built this project yet until the dependee is built.
                if g_verbose_output:
                  if not wait_for_dependencees:
                    print "  [%s]" % project_name;
                  print "    - Waiting for \"%s\"..." % dependee_project_name;
                wait_for_dependencees = True;
                break;
        if not wait_for_dependencees:
          # All dependees have been built; we can build this project:
          if not BuildProject(path, build_info, build_config, project_config, project_name):
            if not g_dirty_build:
              CleanupFolder(path, build_info, build_config, clean_all = True);
            if g_clean_build:
              print "    @ Project clean failed.";
            else:
              print "    @ Project build failed.";
            return False;
          if g_clean_build:
            print "    @ Project cleaned successfully.";
          else:
            print "    @ Project built successfully.";
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
        if not g_dirty_build:
          CleanupFolder(path, build_info, build_config, clean_all = True);
        return False;
    # Optionally run postbuild/test/finish commands:
    if not g_clean_build:
      if not DoPostbuildTestFinishCommands(build_config, "  "):
        if not g_dirty_build:
          CleanupFolder(path, build_info, build_config, clean_all = True);
        return False;
    if not g_dirty_build:
      CleanupFolder(path, build_info, build_config, clean_all = False);
    return True;
  finally:
    os.chdir(saved_path);

def CleanupFolder(path, build_info, build_config, clean_all = False):
  if clean_all:
    project_configs = GetOption("projects", {}, build_config);
    for project_name, project_config in project_configs.items():
      CleanupProject(path, build_info, build_config, project_config, project_name, clean_all = True);
  for pdb_file_name in ["vc80.pdb", "vc90.pdb"]:
    pdb_file_path = os.path.join(path, pdb_file_name);
    if OsIsFile(pdb_file_path):
      print "  - Cleanup: %s" % pdb_file_name;
      try:
        OsDeleteFile(pdb_file_path);
      except OSError:
        print >>sys.stderr, "    * Cannot cleanup intermediate file \"%s\"." % pdb_file_path;
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
  if not g_clean_build:
    if not DoPrebuildCommands(project_config, "    "):
      return False;
  file_configs = GetOption("files", {}, project_config);
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
      if g_clean_build:
        CleanupFiles(path, file_name, clean_all = True);
        files_built += [file_name];
        progress = True;
      else:
        # For each source file required for building this file:
        wait_for_sources = False;
        for source_file_name in file_config["sources"]:
          # If this file is not mentioned in the build configuration, it must be a static source file:
          if source_file_name not in file_configs:
            # Check if the source file exists:
            if not OsIsFile(os.path.join(path, source_file_name)):
              print >>sys.stderr, "    * Missing source file \"%s\" for \"%s\"." % (source_file_name, file_name);
              return False;
          # If this file is mentioned in the build configuration, see if it has already been built:
          elif not source_file_name in files_built:
            # No; we cannot built this file yet because its sources have not all been built yet.
            if g_verbose_output:
              if not wait_for_sources:
                print "    + File: %s" % file_name;
              print "      - Waiting for \"%s\"..." % source_file_name;
            wait_for_sources = True;
            break;
        if "includes" in file_config:
          for include_file_name in file_config["includes"]:
            # If this file is not mentioned in the build configuration, it must be a static include source file:
            if include_file_name not in file_configs:
              # Check if the include source file exists:
              if not OsIsFile(os.path.join(path, include_file_name)):
                print >>sys.stderr, "    * Missing include source file \"%s\" for \"%s\"." % \
                    (include_file_name, file_name);
                return False;
            # If this file is mentioned in the build configuration, see if it has already been built:
            elif not include_file_name in files_built:
              # No; we cannot built this file yet because its include sources have not all been built yet.
              if g_verbose_output:
                if not wait_for_sources:
                  print "    + File: %s" % file_name;
                print "      - Waiting for \"%s\"..." % include_file_name;
              wait_for_sources = True;
              break;
        # libs need no checking
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
              print >>sys.stderr, "    * %s" % source_file_name;
          if "includes" in file_config:
            # For each include source file required for building this file:
            for include_file_name in file_config["includes"]:
              # Files mentioned in the build configuration that have not been built cause circular dependencies:
              if include_file_name in file_configs and not include_file_name in files_built:
                print >>sys.stderr, "    * (include) %s" % include_file_name;
      return False;
  if not g_clean_build:
    if not DoPostbuildTestFinishCommands(project_config, "    "):
      return False;
  if not g_dirty_build:
    if not CleanupProject(path, build_info, build_config, project_config, project_name):
      return False;
  return True;

def CleanupProject(path, build_info, build_config, project_config, project_name, clean_all = False):
  cleanup_errors = False;
  file_configs = GetOption("files", {}, project_config);
  for file_name, file_config in file_configs.items():
    if "cleanup" in file_config:
      # If cleanup is specified, use that setting:
      cleanup = file_config["cleanup"] == True;
    else:
      # Otherwise default to True for .obj files and False for other files:
      cleanup = re.match(r".*\.obj$", file_name, re.IGNORECASE) is not None;
    file_path = os.path.join(path, file_name);
    if OsIsFile(file_path) and (cleanup or clean_all):
      print "    - Cleanup: %s" % file_name;
      try:
        OsDeleteFile(file_path);
      except OSError:
        print >>sys.stderr, "  * Cannot cleanup intermediate file \"%s\"." % file_path;
        cleanup_errors = True;
  return not cleanup_errors;

def BuildFile(path, build_info, build_config, project_config, file_config, file_name):
  print "    + Build: %s" % file_name;
  # Optionally run build commands rather than do a build through compile/assemble:
  if "build commands" in file_config:
    for build_command in file_config["build commands"]:
      if type(build_command) == str:
        build_arguments = [];
      else:
        build_arguments = build_command[1:];
        build_command   = build_command[0];
      if not RunApplication(build_command, build_arguments, pipe_stdout = True):
        print >>sys.stderr, "      * Build command failed.";
        return False;
    return True;

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
    if "libs" in file_config:
      print >>sys.stderr, "  * Cannot use .lib files when generating .%s file." % \
          {True:"bin", False:"obj"}[target_is_bin];
      return False;
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
    if not RunNasm(nasm_arguments):
      return False;
  elif (target_is_obj) and (sources_includes_c or sources_includes_cpp):
    if "libs" in file_config:
      print >>sys.stderr, "  * Cannot use .lib files when generating .obj file.";
      return False;
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
    if not RunMsBuild(msbuild_arguments):
      return False;
  elif (target_is_exe or target_is_dll) and sources_includes_obj:
    # The source is obj, use LINK:
    link_arguments = ["/NOLOGO", "/OUT:\"%s\"" % file_name];
    for source_file_name in file_config["sources"]:
      if re.match(r".*\.def$", source_file_name, re.IGNORECASE) is not None:
        link_arguments += ["/DEF:\"%s\"" % source_file_name];
      else:
        link_arguments += ["\"%s\"" % source_file_name];
    if "libs" in file_config:
      for lib_file_name in file_config["libs"]:
        link_arguments += ["\"%s\"" % lib_file_name];
    if entry_point:
      link_arguments += ["/entry:%s" % entry_point];
    if debug:
      link_arguments += ["/DEBUG"];
    if target_is_exe:
      link_arguments += ["/subsystem:%s" % subsystem];
    elif target_is_dll:
      link_arguments += ["/DLL"];
    msbuild_arguments = [architecture, "LINK"] + link_arguments;
    if not RunMsBuild(msbuild_arguments):
      return False;
  else:
    print >>sys.stderr, "  * No handled file types in sources for \"%s\"." % file_name;
    return False;
  if not OsIsFile(os.path.join(path, file_name)):
    print >>sys.stderr, "  * The target file \"%s\" was not created, but the build command did not report an error." % (
        file_name);
    return False;
  # Optionally run postbuild/test/finish commands:
  if not DoPostbuildTestFinishCommands(file_config, "      "):
    return False;
  if not g_dirty_build:
    if not CleanupFiles(path, file_name, clean_all = False):
      return False;
  return True;

def CleanupFiles(path, file_name, clean_all = False):
  cleanup_errors = False;
  file_path = os.path.join(path, file_name);
  if clean_all and OsIsFile(file_path):
    print "      - Cleanup: %s" % file_name;
    try:
      OsDeleteFile(file_path);
    except OSError:
      print >>sys.stderr, "    * Cannot cleanup file \"%s\"." % file_path;
      cleanup_errors = True;
    pdb_file_name = re.sub(r"\.[^\.]*$", ".pdb", file_name);
    pdb_file_path = os.path.join(path, pdb_file_name);
    if OsIsFile(pdb_file_path):
      print "      - Cleanup: %s" % pdb_file_name;
      try:
        OsDeleteFile(pdb_file_path);
      except OSError:
        print >>sys.stderr, "    * Cannot cleanup debug symbols file \"%s\"." % pdb_file_path;
        cleanup_errors = True;
  intermediate_file_names = [re.sub(r"\.[^\.]*$", ".ilk", file_name),
                             re.sub(r"\.[^\.]*$", ".exp", file_name),
                             re.sub(r"\.[^\.]*$", ".lib", file_name)];
  for intermediate_file_name in intermediate_file_names:
    intermediate_file_path = os.path.join(path, intermediate_file_name);
    if OsIsFile(intermediate_file_path):
      print "      - Cleanup: %s" % intermediate_file_name;
      try:
        OsDeleteFile(intermediate_file_path);
      except OSError:
        print >>sys.stderr, "    * Cannot cleanup intermediate file \"%s\"." % intermediate_file_path;
        cleanup_errors = True;
  return not cleanup_errors;

def DoPrebuildCommands(config, padding):
  # Optionally run prebuild commands:
  if "prebuild commands" in config:
    for prebuild_command in config["prebuild commands"]:
      print "%s+ Prebuild: %s" % (padding, file_name);
      if type(prebuild_command) == str:
        prebuild_arguments = [];
      else:
        prebuild_arguments = prebuild_command[1:];
        prebuild_command   = prebuild_command[0];
      if not RunApplication(prebuild_command, prebuild_arguments, pipe_stdout = False):
        print >>sys.stderr, "%s* Prebuild command failed." % padding;
        return False;
  return True;

def DoPostbuildTestFinishCommands(config, padding):
  # Optionally run postbuild/test/finish commands:
  if "postbuild commands" in config:
    for postbuild_command in config["postbuild commands"]:
      print "%s+ Postbuild: %s" % (padding, postbuild_command);
      if type(postbuild_command) == str:
        postbuild_arguments = [];
      else:
        postbuild_arguments = postbuild_command[1:];
        postbuild_command   = postbuild_command[0];
      if not RunApplication(postbuild_command, postbuild_arguments, pipe_stdout = False):
        print >>sys.stderr, "%s* Postbuild command failed." % padding;
        return False;
  if "test commands" in config:
    for test_command in config["test commands"]:
      print "%s+ Test: %s" % (padding, test_command);
      if type(test_command) == str:
        test_arguments = [];
      else:
        test_arguments = test_command[1:];
        test_command   = test_command[0];
      if not RunApplication(test_command, test_arguments, pipe_stdout = False):
        print >>sys.stderr, "%s* Test command failed." % padding;
        return False;
  if "finish commands" in config:
    for finish_command in config["finish commands"]:
      print "%s+ Finish: %s" % (padding, finish_command);
      if type(finish_command) == str:
        finish_arguments = [];
      else:
        finish_arguments = finish_command[1:];
        finish_command   = finish_command[0];
      if not RunApplication(finish_command, finish_arguments, pipe_stdout = False):
        print >>sys.stderr, "%s* Finish command failed." % padding;
        return False;
  return True;

def FindInPath(file_name):
  for path in os.environ["PATH"].split(";"):
    file_path = os.path.join(path, file_name);
    if OsIsFile(file_path):
      return file_path;
  print >>sys.stderr, "\"%s\" not found." % file_name;
  return None;

def RunNasm(nasm_arguments):
  nasm_exe_path = FindInPath("nasm.exe");
  if nasm_exe_path is None:
    return False;
  return RunApplication(nasm_exe_path, nasm_arguments);

def RunMsBuild(msbuild_arguments):
  msbuild_cmd_path = FindInPath("MSBUILD.cmd");
  if msbuild_cmd_path is None:
    return False;
  return RunApplication(msbuild_cmd_path, msbuild_arguments);

def RunApplication(path, arguments=[], stdin="", pipe_stdout = True):
  command = "\"%s\" %s" % (path, " ".join(arguments));
  if g_verbose_output:
    print "      %s" % command;
  try:
    if pipe_stdout:
      popen = subprocess.Popen(command, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE);
    else:
      popen = subprocess.Popen(command, stdin = subprocess.PIPE,                           stderr = subprocess.PIPE);
  except WindowsError, e:
    if e.errno == 2:
      print >>sys.stderr, "  * Application \"%s\" not found." % path;
      return False;
    else:
      raise e;
  stdout_data, stderr_data = popen.communicate(stdin);
  returncode = popen.wait();
  if g_verbose_output:
    print "      ERRORLEVEL = %d" % returncode;
  if returncode != 0 or stderr_data != "":
    print >>sys.stderr, "  * %s returned error %d:" % (path, returncode);
    if stdout_data: print "    |" + stdout_data.replace("\n", "\n    |");
    if stderr_data: print "    |" + stderr_data.replace("\n", "\n    |");
    return False;
  if g_verbose_output:
    print "      STDOUT = %s" % repr(stdout_data);
  if g_verbose_output:
    print "      STDERR = %s" % repr(stderr_data);
  return True;

if __name__ == "__main__":
  result = Main();
  exit_code = {True:0, False:1}[result];
  sys.exit(exit_code);