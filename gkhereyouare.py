"""Polls and stores all Facebook checkins in a chosen area.

Quick and dirty app to poll all Facebook checkins in the vicinity of a
chosen venue, and store them for reference.
"""

import jinja2
import logging
import os
import urllib
import urllib2
import webapp2
from google.appengine.ext import db

import facebook
import gkdatastore


#TODO(negz): Feel ashamed.
CFG = os.environ
DEBUG = CFG['SERVER_SOFTWARE'].startswith('Dev')
JINJA = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'])


def _PasswordFromFile(password_file):
  """Read a password from a file."""
  try:
    with open(password_file, 'r') as pf:
      for line in pf.readlines():
        if not line.startswith('#'):
          return line.strip()
  except IOError as why:
    logging.exception(why)
    return None


def _DictFromParams(parameters):
  dictionary = {}
  parameters = parameters.split('&')
  for parameter in parameters:
    parameter = parameter.split('=')
    dictionary[parameter[0]] = parameter[1]
  return dictionary


def _Search(graph, search_args, limit=100):
  search_args['limit'] = limit
  search_args['offset'] = 0
  try:
    while True:
      results = graph.request('search', search_args)
      if not results['data']:
        break
      search_args['offset'] += limit
      for result in results['data']:
        yield result
  except facebook.GraphAPIError as why:
    logging.exception(why)


class AccessToken(object):
  def __init__(self, token_id, app_id=None, app_secret=None):
    self.token_id = token_id
    self.app_id = app_id or CFG['FACEBOOK_APP_ID']
    self.app_secret = app_secret or _PasswordFromFile(CFG['FACEBOOK_APP_SECRET_FILE'])
    self.access_token = self.Get()
    self.redirect_uri = None

  def _Store(self, new_token):
    """Store a token for future use."""
    token = gkdatastore.Token(
        key_name=self.token_id,
        token=new_token,
    )
    token.put()
    self.access_token = new_token
    logging.debug('Stored token %s', new_token)

  def _PokeFacebook(self, args=None):
    args = args or {}
    args = urllib.urlencode(args)
    try:
      result = urllib2.urlopen('https://graph.facebook.com/oauth/access_token?%s' % args, None)
      return _DictFromParams(result.readline())
    except urllib2.HTTPError as why:
      logging.exception(why)
      return None

  def SetFromCode(self, code, redirect_uri):
    """Convert a code into an access token."""
    self.redirect_uri = redirect_uri
    args = {
        'client_id': self.app_id,
        'client_secret': self.app_secret,
        'code': code,
        'redirect_uri': self.redirect_uri,
    }
    result = self._PokeFacebook(args)
    if result:
      self._Store(result['access_token'])

  def Extend(self):
    """Swap a short lived access token for a long lived one."""
    if not self.access_token:
      logging.error('No access token to extend.')
    args = {
        'client_id': self.app_id,
        'client_secret': self.app_secret,
        'grant_type': 'fb_exchange_token',
        'fb_exchange_token': self.access_token,
        'redirect_uri': self.redirect_uri,
    }
    result = self._PokeFacebook(args)
    if result:
      self._Store(result['access_token'])

  def Get(self):
    """Return an access token."""
    token = gkdatastore.Token.get_by_key_name(self.token_id)
    if not token:
      return None
    logging.debug('Got token %s', token.token)
    return token.token

class CheckIn(object):
  def __init__(self, checkin_id, access_token, graph=None, fb_object=None):
    self.checkin_id = checkin_id
    self.access_token = access_token
    self.graph = graph or facebook.GraphAPI(self.access_token)
    self.fb_object = fb_object or self.graph.get_object(self.checkin_id)

  def Store(self):
    """Store a checkin."""
    checkin = gkdatastore.CheckIn(
        key_name=self.checkin_id,
        type=self.fb_object['type'],
        place_id=int(self.fb_object['place']['id']),
        person_id=int(self.fb_object['from']['id']),
        person_name=self.fb_object['from']['name'],
    )
    checkin.put()

class Place(object):
  def __init__(self, place_id, access_token, graph=None, fb_object=None):
    self.place_id = place_id
    self.access_token = access_token
    self.graph = graph or facebook.GraphAPI(self.access_token)
    self.fb_object = fb_object or self.graph.get_object(self.place_id)
    self.checkins = 0

  def Store(self):
    """Store a place."""
    place = gkdatastore.Place(
        key_name=self.place_id,
        name=self.fb_object['name'],
        checkins=self.checkins,
    )
    place.put()

  def GetCheckIns(self):
    """Yields Facebook objects (checkins, statuses, etc) at this place."""
    try:
      search_args = {
        'type': 'location',
        'place': self.place_id,
      }
      for checkin in _Search(self.graph, search_args):
        yield CheckIn(checkin['id'], self.access_token, self.graph, checkin)
    except facebook.GraphAPIError as why:
      logging.exception(why)

  def GetNearbyPlaces(self, radius):
    """Yields Facebook places near this place.

    Args:
      radius: Int, the radius in kilometers inside which places are considered
        'nearby'.

    Yields:
      A Place() object for each nearby place.
    """
    try:
      location = self.fb_object['location']
      search_args = {
        'type': 'place',
        'center': '%s, %s' % (location['latitude'], location['longitude']),
        'distance': radius,
      }
      for place in _Search(self.graph, search_args):
        yield Place(place['id'], self.access_token, self.graph, place)
    except facebook.GraphAPIError as why:
      logging.exception(why)


class RootHandler(webapp2.RequestHandler):
  def get(self):
    user_token = AccessToken('gk').Get()
    epicentre = Place(CFG['EPICENTRE_ID'],
                      user_token)
    places = db.Query(gkdatastore.Place)
    places.filter('checkins >', 0)
    places.order('-checkins')
    template_values = {
      'epicentre': epicentre,
      'places': places,
    }
    template = JINJA.get_template('root.html')
    return self.response.write(template.render(template_values))


class PollHandler(webapp2.RequestHandler):
  def get(self):
    user_token = AccessToken('gk').Get()
    epicentre = Place(CFG['EPICENTRE_ID'],
                      user_token)
    for place in epicentre.GetNearbyPlaces(CFG['RADIUS']):
      checkins = len([checkin.Store() for checkin in place.GetCheckIns()])
      place.checkins = checkins
      place.Store()
    self.response.headers['Content-Type'] = 'text/plain'
    return self.response.write('Poll complete.')


class AccessTokenHandler(webapp2.RequestHandler):
  def get(self):
    code = self.request.get('code')
    if code:
      user_token = AccessToken('gk')
      user_token.SetFromCode(code, self.request.url)
      user_token.Extend()
      return self.redirect('/')

    facebook_auth_args = {
        'client_id': CFG['FACEBOOK_APP_ID'],
        'redirect_uri': self.request.url,
        'response_type': 'code',
        'scope': CFG['SCOPE']
    }
    facebook_auth_uri = ('https://www.facebook.com/dialog/oauth?%s' %
                         urllib.urlencode(facebook_auth_args))
    return self.redirect(facebook_auth_uri)


app = webapp2.WSGIApplication([
    ('/', RootHandler),
    ('/token' , AccessTokenHandler),
    ('/poll', PollHandler),
  ], debug=DEBUG)
