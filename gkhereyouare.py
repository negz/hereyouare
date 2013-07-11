"""Polls and stores all Facebook checkins in a chosen area.

Quick and dirty app to poll all Facebook checkins in the vicinity of a 
chosen venue, and store them for reference.
"""
import facebook
import webapp2

EPICENTRE_PAGE='239927392813748'
RADIUS='1500'

# search?type=place&center=-33.897947275461,151.17869226555&distance=1500
# 158480197527281/checkins

class RootHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.write('Boop.')


class PollHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.write('Borp.')


app = webapp2.WSGIApplication([
    ('/', RootHandler),
    ('/poll', PollHandler),
  ], debug=True)
