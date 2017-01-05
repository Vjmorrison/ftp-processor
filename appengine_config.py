"""`appengine_config` gets loaded when starting a new application instance."""
from google.appengine.ext import vendor
import os.path

vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))
