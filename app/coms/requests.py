import autoparse


class BaseRequestObject(autoparse.AutoParseObject):
	required_args = []

	def __init__(self, required_args=None):
		if not required_args:
			required_args = []
		self.required_args = required_args
