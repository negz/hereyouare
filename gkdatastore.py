"""Datastore models for gkhereyouare.py"""

from google.appengine.ext import db


class Token(db.Model):
  token = db.StringProperty(required=True)


class CheckIn(db.Model):
  type = db.StringProperty(required=True)
  place_id = db.IntegerProperty(required=True)
  person_id = db.IntegerProperty(required=True)
  person_name = db.StringProperty(required=True)


class Place(db.Model):
  name = db.StringProperty(required=True)
  checkins = db.IntegerProperty(required=True)
