"""Polls and stores all Facebook checkins in a chosen area.

Quick and dirty app to poll all Facebook checkins in the vicinity of a
chosen venue, and store them for reference.
"""

import facebook
import jinja2
import logging
import os
import urllib
import urllib2
import webapp2
from google.appengine.ext import db


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


class AccessToken(object):
  def __init__(self, token_id, app_id=None, app_secret=None):
    self.token_id = token_id
    self.app_id = app_id or CFG['FACEBOOK_APP_ID']
    self.app_secret = app_secret or _PasswordFromFile(CFG['FACEBOOK_APP_SECRET_FILE'])
    self.access_token = self.Get()
    self.redirect_uri = None

  class Token(db.Model):
    token = db.StringProperty(required=True)
  
  def _Store(self, new_token):
    """Store a token for future use."""
    token = self.Token(
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
    token = self.Token.get_by_key_name(self.token_id)
    if not token:
      return None
    logging.debug('Got token %s', token.token)
    return token.token


class Place(object):
  def __init__(self, place_id, access_token):
    self.place_id = place_id
    self.access_token = access_token
    self.graph = facebook.GraphAPI(self.access_token)

  def GetNearbyPlaces(self, radius, limit=100):
    """Yields a list of Facebook places near a chosen place.

    Args:
      limit: Int, the amount of results to return with each search query.

    Yields:
      A list of tuples like (id, name) representing Facebook places.
    """
    try:
      location = self.graph.get_object(self.place_id)['location']
      search_args = {
        'type': 'place',
        'center': '%s, %s' % (location['latitude'], location['longitude']),
        'distance': radius,
        'limit': limit,
        'offset': 0,
      }
      while True:
        results = self.graph.request('search', search_args)
        if not results['data']:
          break
        search_args['offset'] += limit
        for place in results['data']:
          yield (place['id'], place['name'])
    except facebook.GraphAPIError as why:
      logging.exception(why)


class RootHandler(webapp2.RequestHandler):
  def get(self):
    template = JINJA.get_template('root.html')
    return self.response.write(template.render())


class PollHandler(webapp2.RequestHandler):
  def get(self):
    user_token = AccessToken('poller').Get()
    epicentre = Place(CFG['EPICENTRE_ID'],
                      user_token)
    for place in epicentre.GetNearbyPlaces(CFG['RADIUS']):
      logging.info(place)
    self.response.headers['Content-Type'] = 'text/plain'
    return self.response.write('Poll complete.')


class AccessTokenHandler(webapp2.RequestHandler):
  def get(self):
    code = self.request.get('code')
    if code:
      user_token = AccessToken('poller')
      user_token.SetFromCode(code, self.request.url)
      user_token.Extend()
      return self.redirect('/')

    facebook_auth_args = {
        'client_id': CFG['FACEBOOK_APP_ID'],
        'redirect_uri': self.request.url,
        'response_type': 'code',
    }
    facebook_auth_uri = ('https://www.facebook.com/dialog/oauth?%s' %
                         urllib.urlencode(facebook_auth_args))
    return self.redirect(facebook_auth_uri)


app = webapp2.WSGIApplication([
    ('/', RootHandler),
    ('/token' , AccessTokenHandler),
    ('/poll', PollHandler),
  ], debug=DEBUG)
