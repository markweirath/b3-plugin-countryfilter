#
# Plugin for BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2005 www.xlr8or.com
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

__version__ = '1.1.5'
__author__  = 'guwashi / xlr8or'

import sys, re, b3, threading
import b3.events
import b3.extplugins.GeoIP.PurePythonGeoIP
from b3.extplugins.GeoIP.PurePythonGeoIP import GeoIP

#--------------------------------------------------------------------------------------------------
class CountryfilterPlugin(b3.plugin.Plugin):
  # Defaults
  _adminPlugin = None
  cf_country_print_mode = 'name'
  cf_allow_message = '^7%(name)s ^2(Country: %(country)s)^7 connected.'
  cf_deny_message =  '^7%(name)s ^1(Country: %(country)s)^7 was rejected by B3.'
  cf_message_exclude_from = ''
  cf_order = 'deny,allow'
  cf_deny_from = ''
  cf_allow_from = 'all'
  cf_geoipdat_path = 'b3/extplugins/GeoIP/GeoIP.dat'
  ignore_names = []
  ignore_ips = []

  gi = None


  def onStartup(self):
    """\
    Create a new GeoIP object and register callback functions.
    """

    # get the admin plugin so we can register commands, issue kicks and such
    self._adminPlugin = self.console.getPlugin('admin')
    if not self._adminPlugin:
      # something is wrong, can't start without admin plugin
      self.error('Could not find admin plugin')
      return False
    
    # register our commands
    if 'commands' in self.config.sections():
      for cmd in self.config.options('commands'):
        level = self.config.get('commands', cmd)
        sp = cmd.split('-')
        alias = None
        if len(sp) == 2:
          cmd, alias = sp

        func = self.getCmd(cmd)
        if func:
          self._adminPlugin.registerCommand(self, cmd, level, func, alias)

    self.gi = GeoIP.open(self.cf_geoipdat_path, GeoIP.GEOIP_STANDARD)
    self.registerEvent(b3.events.EVT_CLIENT_AUTH)
    self.debug('Started')


  def getCmd(self, cmd):
    cmd = 'cmd_%s' % cmd
    if hasattr(self, cmd):
      func = getattr(self, cmd)
      return func

    return None


  def onLoadConfig(self):
    """\
    Load the config
    """
    self.verbose('Loading config')
    try:
      self.cf_country_print_mode = self.config.get('settings', 'cf_country_print_mode')
    except:
      pass
    try:
      self.cf_allow_message = self.config.get('messages', 'cf_allow_message')
    except:
      pass

    try:
      self.cf_deny_message = self.config.get('messages', 'cf_deny_message')
    except:
      pass

    try:
      self.cf_message_exclude_from = self.config.get('settings', 'cf_message_exclude_from')
    except:
      pass
    try:
      self.cf_order = self.config.get('settings', 'cf_order')
    except:
      pass
    try:
      self.cf_deny_from = self.config.get('settings', 'cf_deny_from')
    except:
      pass
    try:
      self.cf_allow_from = self.config.get('settings', 'cf_allow_from')
    except:
      pass
    try:
      self.cf_geoipdat_path = self.config.get('settings', 'cf_geoipdat_path')
    except:
      pass
    try:
      self.ignore_names = self.config.get('ignore', 'names').split(",")
    except:
      pass
    try:
      self.ignore_ips = self.config.get('ignore', 'ips').split(",")
    except:
      pass


  def onEvent(self, event):
    """\
    Handle intercepted events
    """
    if event.type == b3.events.EVT_CLIENT_AUTH:
      self.onPlayerConnect(event.client)


  def onPlayerConnect(self, client):
    """\
    Examine players country and allow/deny to connect.
    """
    self.debug('Connecting slot: %s, %s, %s' % (client.cid, client.name, client.ip))
    countryId = self.gi.id_by_addr(str(client.ip))
    countryCode = GeoIP.id_to_country_code(countryId)
    country = self.idToCountry(countryId)
    self.debug('Country: %s' % (country))
    if self.isAllowConnect(countryCode, client):
      if (0 < len(self.cf_allow_message) and (not self.isMessageExcludeFrom(countryCode))) and client.guid and self.console.upTime() > 300:
        message = self.getMessage('cf_allow_message', { 'name':client.name,  'country':country})
        self.console.say(message)
      pass # do nothing
    else:
      if 0 < len(self.cf_deny_message) and (not self.isMessageExcludeFrom(countryCode)):
        message = self.getMessage('cf_deny_message', { 'name':client.name,  'country':country})
        self.console.say(message)
      client.kick(silent=True)
    self.debug('Connecting done.')

  
  def isAllowConnect(self, countryCode, client):
    """\
    Is player allowed to connect?
    """
    # http://httpd.apache.org/docs/mod/mod_access.html
    result = True

    if client.name in self.ignore_names:
      self.debug('Name is on ignorelist, allways allowed to connect')
      result = True
    elif client.ip in self.ignore_ips:
      self.debug('Ip address is on ignorelist, allways allowed to connect')
      result = True
    elif 'allow,deny' == self.cf_order:
      #self.debug('allow,deny - checking')
      result = False # deny
      if -1 != self.cf_allow_from.find('all'):
        result = True
      if -1 != self.cf_allow_from.find(countryCode):
        result = True
      if -1 != self.cf_deny_from.find('all'):
        result = False
      if -1 != self.cf_deny_from.find(countryCode):
        result = False
    else: # 'deny,allow' (default)
      #self.debug('deny,allow - checking')
      result = True; # allow
      if -1 != self.cf_deny_from.find('all'):
        result = False
      if -1 != self.cf_deny_from.find(countryCode):
        result = False
      if -1 != self.cf_allow_from.find('all'):
        result = True
      if -1 != self.cf_allow_from.find(countryCode):
        result = True
    return result
  
  def isMessageExcludeFrom(self, countryCode):
    """\
    Is message allowed to print?
    """
    result = False
    if -1 != self.cf_message_exclude_from.find('all'):
      result = True
    if -1 != self.cf_message_exclude_from.find(countryCode):
      result = True
    return result
  
  def idToCountry(self, countryId):
    """\
    Convert country id to country representation.
    """
    if 'code3' == self.cf_country_print_mode:
      return GeoIP.id_to_country_code3(countryId)
    elif 'name' == self.cf_country_print_mode:
      return GeoIP.id_to_country_name(countryId)
    else: # 'code' (default)
      return GeoIP.id_to_country_code(countryId)


  def cmd_cfcountry(self, data, client, cmd=None):
    """\
    <player> - What country is this player from?
    """
    # this will split the player name and the message (oops, no message...)
    input = self._adminPlugin.parseUserCmd(data)
    if input:
      # input[0] is the player id
      sclient = self._adminPlugin.findClientPrompt(input[0], client)
      if not sclient:
        # a player matchin the name was not found, a list of closest matches will be displayed
        # we can exit here and the user will retry with a more specific player
        return False
    else:
      client.message('^7Invalid or missing data, try !help cfcountry')
      return False

    # are we still here? Let's get the country
    countryId = self.gi.id_by_addr(str(sclient.ip))
    countryCode = GeoIP.id_to_country_code(countryId)
    country = self.idToCountry(countryId)
    cmd.sayLoudOrPM(client, '^1%s^7 is connecting from ^1%s^7' % (sclient.name, country))

    return True

if __name__ == '__main__':
  print '\nThis is version '+__version__+' by '+__author__+' for BigBrotherBot.\n'
