import webapp2


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
