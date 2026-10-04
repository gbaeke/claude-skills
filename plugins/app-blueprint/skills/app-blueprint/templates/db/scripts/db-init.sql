-- Runs once, when the container's volume is new: the database the tests use, next to the app's.
CREATE DATABASE {{pkg}}_test OWNER {{pkg}};
