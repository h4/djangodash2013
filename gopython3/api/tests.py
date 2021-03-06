from django.test import TestCase
from httpretty import HTTPretty

from api.wrappers import github, pypi


class APITestCase(TestCase):
    def setUp(self):
        HTTPretty.reset()
        HTTPretty.enable()

    def tearDown(self):
        HTTPretty.disable()

    def registerApiGetResponse(self, url, body, status_code=200, content_type='text/json'):
        HTTPretty.register_uri(HTTPretty.GET, url, body=body, status=status_code, content_type=content_type)

    def registerApiGetRequestWithMultipleResponses(self, url, responses):
        HTTPretty.register_uri(HTTPretty.GET, url, responses=[HTTPretty.Response(**r) for r in responses])


class PyPITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.package_name = 'Django'
        self.package_version = '1.5.1'
        self.api_wrapper = pypi.PyPIWrapper()

    def test_wrapper_parses_data_correct(self):
        self.registerApiGetResponse(
            "http://pypi.python.org/pypi/%s/json" % self.package_name,
            '{"info": {"author": "Django Software Foundation", "version": "1.5.4"}}',
        )
        data = self.api_wrapper.ask_about_package_info(name=self.package_name)
        self.assertTrue(isinstance(data, dict))
        self.assertTrue('info' in data)
        self.assertEqual(data['info']['author'], 'Django Software Foundation')
        self.assertEqual(data['info']['version'], '1.5.4')

    def test_works_with_version(self):
        self.registerApiGetResponse(
            "http://pypi.python.org/pypi/%s/%s/json" % (self.package_name, self.package_version),
            '{"info": {"author": "Django Software Foundation", "version": "1.5.1"}}',
        )
        data = self.api_wrapper.ask_about_package_info(name=self.package_name, version=self.package_version)
        self.assertEqual(data['info']['version'], self.package_version)


class GithubTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.owner = 'django'
        self.repo = 'django'
        self.api_wrapper = github.GithubWrapper()

    def test_wrapper_parses_data_correct(self):
        self.registerApiGetResponse(
            "https://api.github.com/repos/%s/%s" % (self.owner, self.repo),
            '{"html_url": "https://github.com/django/django", "updated_at": "2013-09-28T08:25:15Z"}',
        )
        data = self.api_wrapper.ask_about_repo_info(owner=self.owner, repo=self.repo)
        self.assertEqual(data['html_url'], 'https://github.com/django/django')
        self.assertEqual(data['updated_at'], '2013-09-28T08:25:15Z')

    def test_wrapper_gets_correct_py3_issues(self):
        self.registerApiGetRequestWithMultipleResponses(
            url="https://api.github.com/repos/%s/%s/issues" % (self.owner, self.repo),
            responses=(
                {'body': '[{"number": "123", "html_url": "gh.com/issue/123", "state": "closed", "title": "UnicodeError", "body": "sometext", "owner": {"login": "dummy"}}]', 'status': 200},
                {'body': '[{"number": "456", "html_url": "gh.com/issue/456", "state": "open", "title": "Python 3 support", "body": "sometext", "owner": {"login": "py3lover"}}]', 'status': 200}
            )
        )
        py3_issues = self.api_wrapper.get_py3_issues_info(self.owner, self.repo)
        self.assertListEqual(py3_issues, [{'state': 'open', 'title': 'Python 3 support', 'url': 'gh.com/issue/456'}])


class GithubSearchTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.api_wrapper = github.GithubSearchWrapper()

    def test_gives_most_popular_result_from_repos_with_same_name(self):
        self.registerApiGetResponse(
            "https://api.github.com/search/repositories",
            '{"items": [{"name": "django", "owner": {"login": "django"}}, {"name": "django-cms", "owner": {"login": "divio"}}, {"name": "django", "owner": {"login": "fc"}}]}',
        )

        owner, _ = self.api_wrapper.get_most_popular_repo('django')
        self.assertEqual(owner, 'django')