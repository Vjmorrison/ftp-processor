
from googlewrapper import GoogleAPIWrapper
import datetime


class StackdriverService(GoogleAPIWrapper):
	service_name = "monitoring"
	version = 'v3'

	def __init__(self, service_account_credentials_file=None, logger=None):
		super(StackdriverService, self).__init__(
			service_account_credentials_file=service_account_credentials_file,
			logger=logger,
			service_name=self.service_name,
			version=self.version
		)

	def _format_rfc3339(self, datetime_instance):
		"""Formats a datetime per RFC 3339."""
		return datetime_instance.isoformat("T") + "Z"

	def parse_formatted_time(self, rfc3339_time):
		return datetime.datetime.strptime(rfc3339_time, "%Y-%m-%dT%H:%M:%S.%fZ")

	def get_formatted_time(self, start_time=None, offset=None):
		if not start_time:
			start_time = datetime.datetime.utcnow()

		if not offset:
			offset = datetime.timedelta()
		start_time = (start_time - offset)
		return self._format_rfc3339(start_time)

	def list_monitored_resource_descriptors(self, project_resource, client=None):
		"""Query the projects.monitoredResourceDescriptors.list API method.
		This lists all the resources available to be monitored in the API.
		"""
		if not client:
			client = self.get_client(self.service_account_credentials_file)
		request = client.projects().monitoredResourceDescriptors().list(
			name=project_resource)
		response = request.execute()
		return response

	def list_metric_descriptors(self, client, project_resource, metric):
		"""Query to MetricDescriptors.list
		This lists the metric specified by METRIC.
		"""
		request = client.projects().metricDescriptors().list(
			name=project_resource,
			filter='metric.type="{}"'.format(metric))
		response = request.execute()
		return response

	def list_timeseries(self, project_resource, metric, from_date=None, to_date=None, now_offset=None, client=None):
		"""Query the TimeSeries.list API method.
		This lists all the timeseries created between START_TIME and END_TIME.
		"""
		if now_offset and (from_date or to_date):
			raise TypeError("Cannot supply a now_offset as well as start/end times")

		if now_offset:
			from_date = datetime.datetime.utcnow() - now_offset
			to_date = datetime.datetime.utcnow()

		if not client:
			client = self.get_client(self.service_account_credentials_file)
		request = client.projects().timeSeries().list(
			name=project_resource,
			filter='metric.type="{}"'.format(metric),
			pageSize=3,
			interval_startTime=self.get_formatted_time(from_date),
			interval_endTime=self.get_formatted_time(to_date))
		response = request.execute()
		return response

	def get_last_metric(self, project_resource, metric, client=None):
		results = self.list_timeseries(
			project_resource=project_resource,
			metric=metric,
			now_offset=datetime.timedelta(hours=1)
		)
		timeseries = results["timeSeries"][0]
		points = timeseries["points"]
		last_point_value = points[0]['value']
		last_point_time = points[0]['interval']['endTime']
		last_point_time = self.parse_formatted_time(last_point_time)
		return last_point_value, last_point_time
