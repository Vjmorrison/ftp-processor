
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials
from oauth2client.service_account import ServiceAccountCredentials


class GoogleAPIWrapper(object):

	service_name = ''
	version = ''
	service_account_credentials_file = ''
	logger = None

	def __init__(self, service_account_credentials_file=None, logger=None, version='', service_name=''):
		self.service_account_credentials_file = service_account_credentials_file
		self.service_name = service_name
		self.version = version
		self.logger = logger

	def get_client(self, service_account_credentials_file=None):
		if not service_account_credentials_file:
			service_account_credentials_file = self.service_account_credentials_file
		"""Builds an http client authenticated with the service account credentials."""
		if service_account_credentials_file:
			scopes = ['https://www.googleapis.com/auth/' + self.service_name, 'https://www.googleapis.com/auth/cloud-platform']
			credentials = ServiceAccountCredentials.from_json_keyfile_name(service_account_credentials_file, scopes)
		else:
			credentials = GoogleCredentials.get_application_default()
		service = discovery.build(self.service_name, self.version, credentials=credentials)
		return service

	def log(self, log_level, message):
		if self.logger:
			self.logger.log(log_level, message)

	@classmethod
	def execute_request(cls, request):
		try:
			return request.execute()
		except HttpError:
			pass
