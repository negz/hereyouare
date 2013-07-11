import webapp2


class RootHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.write('Boop.')


class PollHandler(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.write('Borp.')


root = webapp2.WSGIApplication([('/', RootHandler),], debug=True)
poll = webapp2.WSGIApplication([('/poll', PollHandler),], debug=True)
