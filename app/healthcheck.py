import json
import traceback
import sys


class HealthStatus(object):
	UNKNOWN, PASS, FAIL = range(0, 3)


class HeathCheckTest(object):
	def __init__(self):
		self.status = HealthStatus.UNKNOWN
		self.name = "UNKNOWN"
		self.description = "UNKNOWN"
		self.method = None
		self.instance = None
		self.expected_value = None
		self.message = "UNKNOWN"

	def format_html(self):
		formattedText = "<p><b>Health Test: {name}</b></p>" \
						"<p><ul>" \
						"<li>Status: {status}</li>" \
						"<li>Description: {description}</li>" \
						"<li>Description: {message}</li>" \
						"</ul></p>"
		return formattedText.format(name=self.name, status=self.status, description=self.description, message=self.message)

	def format_json(self, to_string):
		jsonData = {
			'name': self.name,
			'status': self.status,
			'description': self.description,
			'expected_value': self.expected_value,
			'message': self.message
		}
		if to_string:
			return json.dumps(jsonData)
		else:
			return jsonData


class HealthCheckData(object):
	def __init__(self):
		self.name = "UNKNOWN MODULE"
		self.status = HealthStatus.UNKNOWN
		self.message = "uninitialized"
		self.tests = []

	def format_html(self):
		formattedText = "<p><b>Health Check: {name}</b></p>" \
						"<p><ul>" \
						"<li>Status: {status}</li>" \
						"<li>Message: {message}</li>" \
						"<li>Tests: {tests}</li>" \
						"</ul></p>"

		try:
			formattedTests = "<ol><li>" + "</li><li>".join([test.format_html() for test in self.tests]) + "</li></ol>"
		except:
			formattedTests = "NONE"

		return formattedText.format(name=self.name, status=self.status, message=self.message, tests=formattedTests)

	def format_json(self, to_string):
		jsonData = {
				'name': self.name,
				'status': self.status,
				'message': self.message,
				'tests': [test.format_json(to_string=False) for test in self.tests]
			}
		if to_string:
			return json.dumps(jsonData)
		else:
			return jsonData


class HeathCheckMixIn(object):
	health_data = HealthCheckData()

	def get(self):
		self.startup()
		if not self._validate_request():
			self.response.set_status(401, "unauthorized")
			self.render_json({
				'error': 'Unauthorized',

			}, True)
			return
		try:
			htmlString, jsonObj = self.process_health_check(self.test_method.all)
		except AttributeError, e:
			if "test_method" in e.message:
				raise AttributeError("The class using the HeathCheckMixIn must have a self.test_method value registered.")
			else:
				raise sys.exc_info()

		try:
			isJson = self.request.get('json')
		except AttributeError:
			raise AttributeError("The HealthCheckMixIn class must be used in conjunction with a class that extends webapp2.RequestHandler")

		if isJson:
			self.response.write(json.dumps(jsonObj, indent=4, sort_keys=True))
		else:
			self.response.write(htmlString)

	def process_health_check(self, all_tests):
		self.health_data = HealthCheckData()
		self.health_data.name = self.__class__.__name__
		self.health_data.status = HealthStatus.PASS
		for test in sorted(all_tests.itervalues()):
			try:
				returnValue = test.method(self)
				if returnValue == test.expected_value:
					test.status = HealthStatus.PASS
				else:
					test.status = HealthStatus.FAIL
					self.health_data.status = HealthStatus.FAIL
				test.message = "Expected Value: {}, Actual Value: {}".format(test.expected_value, returnValue)
			except:
				e_type, e_val, e_tb = sys.exc_info()
				test.status = HealthStatus.FAIL
				self.health_data.status = HealthStatus.FAIL
				test.message = "".join(traceback.format_exception(e_type, e_val, e_tb))

			self.health_data.tests.append(test)

		if self.health_data.status == HealthStatus.PASS:
			self.health_data.message = "All Tests Passed"
		else:
			self.health_data.message = "{} Tests Failed".format(len([test for test in self.health_data.tests if test.status == HealthStatus.FAIL]))

		return self._format_html(), self._format_json()

	def _format_html(self):
		return self.health_data.format_html()

	def _format_json(self):
		return self.health_data.format_json(to_string=False)


def test_registry():
	all_tests = {}

	def registrar(expected_value=None):
		def wrapper(func):
			newTest = HeathCheckTest()
			newTest.name = func.__name__
			newTest.description = func.__doc__
			newTest.expected_value = expected_value
			newTest.method = func
			all_tests[func.__name__] = newTest
			return func
		return wrapper

	registrar.all = all_tests
	return registrar

