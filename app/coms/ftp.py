from ftplib import FTP_TLS
import json
import os


class FtpService(object):
	connection = None
	cred_path = None
	server_keyname = None

	def __init__(self, credential_filepath, server_keyname):
		self.connection = FTP_TLS()
		self.cred_path = credential_filepath
		self.server_keyname = server_keyname

	def connect(self, cred_file):
		with open(cred_file) as data_file:
			data = json.load(data_file)
			data = data[self.server_keyname]

		self.connection.connect(host=data['host'], port=data['port'])
		self.connection.login(user=data['username'], passwd=data['password'])
		self.connection.prot_p()

	def quit(self):
		self.connection.quit()

	def __enter__(self):
		self.connect(self.cred_path)
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.quit()


class FtpInstance(FtpService):
	host = ""
	port = ""


if __name__ == "__main__":
	server = FtpService('../../ftp_creds.json', 'default')
	server.__enter__()
	server.connection.cwd('Get Jiro!')
	server.connection.retrlines('MLSD')
	server.__exit__(None, None, None)

	with FtpService('../../ftp_creds.json', 'default') as server:
		server.connection.cwd('Get Jiro!')
		server.connection.retrlines('MLSD')
