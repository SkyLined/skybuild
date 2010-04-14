BOOLEAN_SWITCH_VALUES = {'true': True, 'false': False};
HELP_SWITCHES = ['-h', '-?', '/?', '/h', '--help'];
HELP_SWITCH_NAMES = ['h', '?', '?', 'h', 'help'];
class CommandLineOptions():
  def __init__(self, application_name, arguments=[], switches=[], 
      help_message=None, help_notes=None):
    assert application_name, 'You must provide an application name.';
    self.application_name = application_name;
    self.help_message = help_message;
    self.help_notes = help_notes;
    self.argument_names = [];
    self.arguments = {};
    self.switches = {};
    for argument_name, argument_data in arguments.items():
      self.argument_names.append(argument_name);
      self.arguments[argument_name] = Argument(argument_name, argument_data);
    for switch_name, switch_data in switches.items():
      switch = Switch(switch_name, switch_data);
      assert switch_name not in HELP_SWITCH_NAMES, "Switch name \"%s\" is reserved for help." % switch_name;
      assert switch_name not in self.switches, "Switch name \"%s\" is specified twice." % switch_name;
      self.switches[switch_name] = switch;
      if switch.short_name is not None:
        assert switch.short_name not in HELP_SWITCH_NAMES, (
            "Switch short name \"%s\" is reserved for help." % switch.short_name);
        assert switch.short_name not in self.switches, (
            "Switch short name \"%s\" is specified twice." % switch.short_name);
        self.switches[switch.short_name] = switch;

  def ParseArguments(self, argv):
    # Returns two booleans: (arguments parsed ok, continue execution): The first specifies if the arguments were parsed
    # correctly. The second specifies if the program should continue execution. The values that are returned are:
    # True, True: Parsed correctly, continue execution.
    # False, False: Invalid arguments, stop execution.
    # True, False: Found a help switch and displayed a help message, stop execution.
    argi = 0;
    for argument_value in argv:
      if argument_value in HELP_SWITCHES:
        self.ShowHelp();
        return True, False;
      if argument_value.startswith('-') or argument_value.startswith('/'):
        switch_header_length = {True:2, False:1}[argument_value.startswith('--')];
        split_at = argument_value.find('=');
        if split_at == -1:
          switch_name = argument_value[switch_header_length:].lower();
          switch_value = '';
        else:
          switch_name = argument_value[switch_header_length:split_at].lower();
          switch_value = argument_value[split_at + 1:];
        if not self.SetSwitchValue(switch_name, switch_value):
          self.ShowHelp();
          return False, False;
      else:
        if argi >= len(self.argument_names):
          print 'Surplus argument: %s' % repr(argument_value);
          self.ShowHelp();
          return False, False;
        argument_name = self.argument_names[argi];
        if not self.SetArgumentValue(argument_name, argument_value):
          self.ShowHelp();
          return False, False;
        argi += 1;
    for argument in self.arguments.values():
      if not argument.Check():
        self.ShowHelp();
        return False, False;
    return True, True;

  def ShowHelp(self):
    if self.help_message:
      print self.help_message;
    print '\nSyntax:';
    syntax = [self.application_name];
    if self.argument_names:
      for argument_name in self.argument_names:
        if self.arguments[argument_name].required:
          syntax.append(argument_name);
        else:
          syntax.append('[%s]' % argument_name);
    if self.switches:
      syntax.append('[switches]');
    print '  %s' % ' '.join(syntax);
    if self.argument_names:
      print
      print 'Arguments: ';
      for argument in self.arguments.values():
        argument.ShowHelp();
    if self.switches:
      print
      print 'Switches: ';
      for switch in set(self.switches.values()):
        switch.ShowHelp();
    if self.help_notes:
      print 
      print self.help_notes;

  def SetArgumentValue(self, argument_name, argument_value):
    assert argument_name in self.arguments, 'Unknown argument: %s.' % repr(argument_name);
    return self.arguments[argument_name].SetValue(argument_value);

  def GetArgumentValue(self, argument_name):
    assert argument_name in self.arguments, 'Unknown argument %s' % repr(argument_name);
    return self.arguments[argument_name].GetValue();

  def SetSwitchValue(self, switch_name, switch_value):
    if switch_name in self.switches:
      return self.switches[switch_name].SetValue(switch_value);
    print 'Unknown switch: %s.' % repr(switch_name);
    return False;

  def GetSwitchValue(self, switch_name):
    assert switch_name in self.switches, 'Unknown switch %s' % repr(switch_name);
    return self.switches[switch_name].GetValue();

class Argument():
  def __init__(self, name, data):
    self.name = name;
    if 'help' in data:
      self.help_message = data['help'];
    else:
      self.help_message = '(no help available)';

    if 'required' in data:
      self.required = data['required'];
      assert self.required in [False, True], 'Invalid required state for argument %s.' % repr(name);
    else:
      self.required = False;

    if 'initial' in data:
      self.initial_value = data['initial'];
    else:
      assert not self.required, 'Missing initial value for optional argument %s.' % repr(name);
      self.initial_value = None;
    self.value = self.initial_value;
    
    self.value_set = False;
    
  def SetValue(self, value):
    self.value = value;
    self.value_set = True;
    return True;

  def GetValue(self):
    assert not self.required or self.value_set, 'Value for argument %s not set!' % repr(self.name);
    if self.value_set:
      return self.value;
    else:
      return self.initial_value;

  def Check(self):
    if self.required and not self.value_set:
      print 'Required option %s not set.' % self.name;
      return False;
    return True;

  def ShowHelp(self):
    if self.required:
      print ('  %s' % self.name).ljust(40) + "(required)";
    else:
      print ('  %s' % self.name).ljust(40) + "(default=%s)" % self.initial_value;
    print '      %s' % self.help_message;

class Switch():
  def __init__(self, name, data):
    self.name = name;
    if 'help' in data:
      self.help_message = data['help'];
    else:
      self.help_message = '(no help available)';

    if 'valid' in data:
      self.valid_values = data['valid'];
    else:
      self.valid_values = None;

    assert 'initial' in data, 'Missing initial value for switch %s.' % repr(name);
    assert (self.valid_values == None or data['initial'] in self.valid_values), (
        'The initial value for switch %s is not a valid value for that switch!') % repr(name);
    self.initial_value = data['initial'];
    self.SetValue(self.initial_value);

    assert 'default' in data, 'Missing default value for switch %s.' % repr(name);
    self.default_value = data['default'];
    assert (self.valid_values == None or self.default_value in self.valid_values), (
        'The default value for switch %s is not a valid value for that switch!') % repr(name);

    if 'value required' in data:
      self.value_required = data['value required'];
      assert self.value_required in [False, True], (
          'Invalid required state for argument %s.' % repr(name));
    else:
      self.value_required = False;
    
    if 'short' in data:
      self.short_name = data['short'];
    else:
      self.short_name = None;
  
  def SetValue(self, switch_value):
    if not switch_value:
      switch_value = self.default_value;
    if not self.valid_values:
      self.value = switch_value;
    elif switch_value.lower() not in self.valid_values:
      print 'Invalid value for switch %s: %s' % (repr(self.name), repr(switch_value));
      return False;
    else:
      self.value = self.valid_values[switch_value.lower()];
    return True;

  def GetValue(self):
    return self.value;

  def ShowHelp(self):
    if self.valid_values:
      valid_values = [];
      for value in self.valid_values.keys():
        valid_values.append(value);
      valid_values = '|'.join(valid_values);
    else:
      valid_values = '...';
    if self.value_required:
      if self.short_name is not None:
        print '  -%s, --%s=%s' % (self.short_name, self.name, valid_values);
      else:
        print '  --%s=%s' % (self.name, valid_values);
    else:
      if self.short_name is not None:
        names = '  -%s, --%s [=%s]' % (self.short_name, self.name, valid_values);
      else:
        names = '  --%s [=%s]' % (self.name, valid_values);
      print names.ljust(40) + '(default=%s)' % self.default_value;
    print '      %s' % self.help_message;
    if not self.value_required and self.initial_value != self.default_value:
      print '      (If this switch is not specified default=%s).' % self.initial_value;

