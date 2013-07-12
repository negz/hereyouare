"""Polls and stores all Facebook checkins in a chosen area.

Quick and dirty app to poll all Facebook checkins in the vicinity of a 
chosen venue, and store them for reference.
"""

import facebook
import jinja2
import logging
import os
import webapp2


#TODO(negz): Feel ashamed.
CFG = os.environ
JINJA = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'])


class AccessToken(object):
  def __init__(self, token_type='user'):
    self.token_type = token_type

  def Set(self, token):
    if self.token_type == 'user':
      self._ExtendAndSetUser(token)
    if self.token_type == 'app':
      self._SetApp(token)

  def Get(self):
    if self.token_type == 'user':
      return self._GetUser()
    if self.token_type == 'app':
      return self._GetApp()


  def _ExtendAndSetUser(self, token):
    """Exchanges a current Facebook user access token for a long lived one.

    https://developers.facebook.com/docs/facebook-login/login-flow-for-web-no-jssdk/

    Facebook hates freedom, so we must use OAuth to login and receive a short
    lived (~2h) user access token. We can then use our app access token to
    exchange the short lived token for a long lived (~60d) one.
    """
    #TODO(negz): Implement this.
    pass


  def _GetUser(self):
    """Returns the current long lived user access token from the data store."""
    #TODO(negz): Implement this. Test it and get sad if it's expired. Email?
    return 'Nope.'

  def _SetApp(self, token):
    pass

  def _GetApp(self):
    pass


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
    template_values = {}
    template = JINJA.get_template('root.html')
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.write(template.render(template_values))


class PollHandler(webapp2.RequestHandler):

  def get(self):
    user_token = AccessToken('user').Get()
    poller = CheckinPoller(CFG['EPICENTRE_ID'],
                           CFG['RADIUS'],
                           user_token)
    for place in poller.GetNearbyPlaces():
      logging.info(place)
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.write('Poll complete.')


class AccessTokenHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.write('Balls.')


app = webapp2.WSGIApplication([
    ('/', RootHandler),
    ('/token', AccessTokenHandler),
    ('/poll', PollHandler),
  ], debug=True)
