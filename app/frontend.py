import urllib2
import urllib
from google.appengine.api import modules
from google.appengine.api import users

import webapp2
import sys
import traceback
import healthcheck
import json
import basemodule
import socket

from google.appengine.api import urlfetch

import os
import jinja2

from coms.requests import BaseRequestObject

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(template_dir),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)


class APIForwardRequest(BaseRequestObject):
	url = ""
	arguments = {}
	method = "GET"


class FrontEndApiTestHandler(webapp2.RequestHandler):
	def get(self):
		allModules = modules.get_modules()
		allResponses = []
		for moduleName in allModules:
			module_hostname = modules.get_hostname(module=moduleName)
			url = "http://{}/api/get_api_methods".format(module_hostname)
			try:
				response = urlfetch.fetch(
					url,
					payload=None,
					method=urlfetch.GET,
					validate_certificate=False,
					headers=self.request.headers,
					deadline=15)
				allResponses.append(json.loads(response.content))
			except (urllib2.URLError, socket.timeout, urlfetch.DeadlineExceededError, urlfetch.SSLCertificateError, ValueError):
				e_type, e_value, e_tb = sys.exc_info()
				formatted_exc = "".join(traceback.format_exception(e_type, e_value, e_tb))
				allResponses.append({'module': moduleName, 'result': 'Got Error: {}\r\n'.format(formatted_exc)})
		template_values = {
			'user': users.get_current_user(),
			'api_targets': allResponses
		}

		template = JINJA_ENVIRONMENT.get_template('index.html')
		self.response.write(template.render(template_values))


class FrontEndAPIHandler(basemodule.BaseApiHandler):
	test_method = healthcheck.test_registry()
	api_method = basemodule.api_registry()

	@test_method(expected_value=True)
	def test_jinja(self):
		"""verifies that the front end is serving and can run jinja templates"""
		template = JINJA_ENVIRONMENT.get_template('test.html')
		template.render({
			"test_value": 123
		})
		return True

	@api_method(response_type=basemodule.METHOD_OVERRIDE_RESPONSE)
	def _index(self):
		template = JINJA_ENVIRONMENT.get_template('test.html')
		template.render({
			"test_value": 123
		})
		return

	@api_method(req_type=basemodule.GET_METHOD, base_request=APIForwardRequest(required_args=["url"]))
	def forward_api(self):
		try:
			form_data = urllib.urlencode(self.parsed_arguments.arguments)
			if self.parsed_arguments.method == "GET":
				method = urlfetch.GET
			else:
				method = urlfetch.POST
			response = urlfetch.fetch(
				"{}?{}".format(self.parsed_arguments.url, form_data),
				payload=self.parsed_arguments.arguments,
				method=method,
				validate_certificate=False,
				headers=self.request.headers,
				deadline=180)
			self.response.set_status(response.status_code)
			try:
				response_json = json.loads(response.content)
				return response_json
			except ValueError:
				return response.content
		except (urllib2.URLError, socket.timeout, urlfetch.DeadlineExceededError, urlfetch.SSLCertificateError):
			e_type, e_value, e_tb = sys.exc_info()
			formatted_exc = "".join(traceback.format_exception(e_type, e_value, e_tb))
			return json.dumps({'url': self.parsed_arguments.url, 'result': 'Got Error: {}\r\n'.format(formatted_exc)})


class FrontEndHeathCheckHandler(healthcheck.HeathCheckMixIn, FrontEndAPIHandler):
	pass


class TestAllModulesHandler(basemodule.BaseApiHandler):
	def get(self):
		self.startup()
		if not self._validate_request():
			self.response.set_status(401, "unauthorized")
			return
		formatJson = self.request.get("json")

		allModules = modules.get_modules()
		allResponses = []

		for moduleName in allModules:
			module_hostname = modules.get_hostname(module=moduleName)
			url = "http://{}/healthcheck".format(module_hostname)
			if self.request.query_string:
				url += "?{}".format(self.request.query_string)
			if not formatJson:
				allResponses.append('{} Module: BackendURL <a href="{url}">{url}</a>\r\n'.format(moduleName, url=url))
			try:
				response = urlfetch.fetch(
					url,
					payload=None,
					method=urlfetch.GET,
					validate_certificate=False,
					headers=self.request.headers,
					deadline=15)
				self.info("testall response: {}", response)
				allResponses.append(response.content)
			except (urllib2.URLError, socket.timeout, urlfetch.DeadlineExceededError, urlfetch.SSLCertificateError):
				e_type, e_value, e_tb = sys.exc_info()
				formatted_exc = "".join(traceback.format_exception(e_type, e_value, e_tb))
				if formatJson:
					allResponses.append(
						json.dumps({'module': moduleName, 'result': 'Got Error: {}\r\n'.format(formatted_exc)}))
				else:
					allResponses.append('Got Error: {}\r\n'.format(formatted_exc))

		if formatJson:
			self.format_json(allResponses)
		else:
			self.format_html(allResponses)

	def format_html(self, allResponses):
		import datetime
		self.response.write('<h1>Test All  ({})</h1>'.format(datetime.datetime.utcnow()))
		self.response.write('<pre>')
		self.response.write("</br>".join(allResponses))
		self.response.write('</pre>')

	def format_json(self, allResponses):

		allJson = {'results': []}

		for jsonString in allResponses:
			parsedJson = json.loads(jsonString)
			allJson['results'].append(parsedJson)
		self.response.write(json.dumps(allJson, sort_keys=True, indent=4))


app = webapp2.WSGIApplication([
	('/cron/.*', FrontEndAPIHandler),
	('/api/.*', FrontEndAPIHandler),
	('/task/.*', FrontEndAPIHandler),
	('/qa/poll_metrics', FrontEndAPIHandler),
	('/testall', TestAllModulesHandler),
	('/healthcheck', FrontEndHeathCheckHandler),
	('/', FrontEndAPIHandler),
	('/api', FrontEndApiTestHandler)
], debug=True)
