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


#TODO(negz): Feel ashamed.
CFG = os.environ
JINJA = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'])


def _DictFromParams(parameters):
  dictionary = {}
  parameters = parameters.split('&')
  for parameter in parameters:
    parameter = parameter.split('=')
    dictionary[parameter[0]] = parameter[1]
  return dictionary


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


class AccessToken(object):
  def __init__(self, id):
    self.id = id

  def _Store(self):
    """Store a token for future use."""
    pass

  def SetFromCode(self, app_id, code, app_secret, redirect_uri):
    """Convert a code into an access token."""
    logging.info('Getting an access token from code %s and secret %s', code, app_secret)
    args = urllib.urlencode({
        'client_id': app_id,
        'code': code,
        'client_secret': app_secret,
        'redirect_uri': redirect_uri
    })
    result = urllib2.urlopen('https://graph.facebook.com/oauth/access_token?%s' % args, None)
    parameters = _DictFromParams(result.readline())
    logging.info('Got access token %s', parameters['access_token'])
    # TODO(negz): Store token.

  def Extend(self, access_token):
    """Swap a short lived access token for a long lived one."""
    logging.info('Extending and storing %s', access_token)

  def Get(self):
    """Return an access token."""
    return 'Nope.'


class CheckinPoller(object):
  def __init__(self, epicentre_id, radius, access_token):
    self.epicentre_id = epicentre_id
    self.radius = radius
    self.access_token = access_token
    self.graph = facebook.GraphAPI(self.access_token)

  def GetNearbyPlaces(self, limit=100):
    """Yields a list of Facebook places near a chosen epicentre.

    Args:
      limit: Int, the amount of results to return with each search query.

    Yields:
      A list of tuples like (id, name) representing Facebook places.
    """
    try:
      location = self.graph.get_object(self.epicentre_id)['location']
      search_args = {
        'type': 'place',
        'center': '%s, %s' % (location['latitude'], location['longitude']),
        'distance': self.radius,
        'limit': limit,
        'offset': limit,
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
    poller = CheckinPoller(CFG['EPICENTRE_ID'],
                           CFG['RADIUS'],
                           user_token)
    for place in poller.GetNearbyPlaces():
      logging.info(place)
    self.response.headers['Content-Type'] = 'text/plain'
    return self.response.write('Poll complete.')


class AccessTokenHandler(webapp2.RequestHandler):
  def get(self):
    code = self.request.get('code')
    if code:
      app_secret = _PasswordFromFile(CFG['FACEBOOK_APP_SECRET_FILE'])
      user_token = AccessToken('poller')
      user_token.SetFromCode(CFG['FACEBOOK_APP_ID'], code, app_secret, self.request.url)
      return self.redirect('/')

    facebook_auth_args = {
        'client_id': CFG['FACEBOOK_APP_ID'],
        'redirect_uri': self.request.url,
        'response_type': 'code'
    }
    facebook_auth_uri = (
        'https://www.facebook.com/dialog/oauth'
        '?client_id=%(client_id)s'
        '&redirect_uri=%(redirect_uri)s'
        '&response_type=%(response_type)s'
    ) % facebook_auth_args
    return self.redirect(facebook_auth_uri)


app = webapp2.WSGIApplication([
    ('/', RootHandler),
    ('/token' , AccessTokenHandler),
    ('/poll', PollHandler),
  ], debug=True)
