hereyouare
==========

Prototype for Grace Kingston's Here You Are exhibit.

A simple web interface protected by AppEngine's admin user capacity. Lets
people with the right creds login and hit 'poke'. This oauths them to Facebook,
then extends their access token for two months.

Once it has an access token it will poll Facebook for checkins around 1km of
ARCHIVE Space in Newtown, Sydney and store some details about them in the
AppEngine datastore. Checkins can then be displayed via the interface.

This data will be used by Grace to create an exhibition exploring our desire to
'be' somewhere. In her words:

http://gracekingston.com/here-you-are-archive_-space-9th-of-october-2013/