# -*- coding: utf-8 -*-
"""Defines helper functions for teamcity interaction"""
import zazu.build_server
import zazu.credential_helper
import zazu.github_helper
import zazu.util
zazu.util.lazy_import(locals(), [
    'click',
    'json',
    'pyteamcity',
    'requests',
    'teamcity.messages'
])

__author__ = "Nicholas Wiles"
__copyright__ = "Copyright 2016"


class TeamCityBuildServer(zazu.build_server.BuildServer):
    """Extends the pyteamcity.Teamcity object to expose interfaces to create projects and build configurations"""

    def __init__(self, address, port=80, protocol='http'):
        self._address = address
        self._protocol = protocol
        self._port = port
        self._tc_handle = None

    def teamcity_handle(self):
        if self._tc_handle is None:
            use_saved_credentials = True
            while True:
                tc_user, tc_pass = zazu.credential_helper.get_user_pass_credentials('TeamCity', use_saved_credentials)
                tc = pyteamcity.TeamCity(username=tc_user, password=tc_pass,
                                         server=self._address, port=self._port,
                                         protocol=self._protocol)
                try:
                    tc.get_user_by_username(tc_user)
                    self._tc_handle = tc
                    break
                except pyteamcity.HTTPError:
                    click.echo("incorrect username or password!")
                    use_saved_credentials = False

        return self._tc_handle

    def setup_root_template(self):
        """Sets up the ZazuGitHubDefault buildType template"""
        template = {
            "name": "ZazuGitHubDefault",
            "parameters": {
                "count": 4,
                "property": [
                    {
                        "name": "architecture",
                        "value": ""
                    },
                    {
                        "name": "buildType",
                        "value": ""
                    },
                    {
                        "name": "gitHubRepoPath",
                        "value": ""
                    },
                    {
                        "name": "goal",
                        "value": ""
                    }
                ]
            },
            "settings": {
                "count": 1,
                "property": [
                    {
                        "name": "executionTimeoutMin",
                        "value": "15"
                    }
                ]
            },
            "projectName": "<Root project>",
            "triggers": {
                "count": 1,
                "trigger": [
                    {
                        "type": "vcsTrigger",
                        "id": "vcsTrigger"
                    }
                ]
            },
            "templateFlag": True,
            "steps": {
                "count": 2,
                "step": [
                    {
                        "properties": {
                            "count": 3,
                            "property": [
                                {
                                    "name": "script.content",
                                    "value": "rm -rf %teamcity.agent.jvm.user.home%/buildEnv\nvirtualenv --system-site-packages %teamcity.agent.jvm.user.home%/buildEnv\n. %teamcity.agent.jvm.user.home%/buildEnv/bin/activate\n%teamcity.agent.jvm.user.home%\\buildEnv\\bin\\activate.bat\npip install pip==9.0.1\npip install --upgrade --force-reinstall --trusted-host pypi.lily.technology --index-url http://pypi.lily.technology:8080/simple zazu\nzazu upgrade"
                                },
                                {
                                    "name": "teamcity.step.mode",
                                    "value": "default"
                                },
                                {
                                    "name": "use.custom.script",
                                    "value": "true"
                                }
                            ]
                        },
                        "type": "simpleRunner",
                        "id": "RUNNER_1",
                        "name": "Install zazu"
                    },
                    {
                        "properties": {
                            "count": 3,
                            "property": [
                                {
                                    "name": "script.content",
                                    "value": ". %teamcity.agent.jvm.user.home%/buildEnv/bin/activate\n%teamcity.agent.jvm.user.home%\\buildEnv\\bin\\activate.bat\nzazu build --arch=%architecture% %goal%"
                                },
                                {
                                    "name": "teamcity.step.mode",
                                    "value": "default"
                                },
                                {
                                    "name": "use.custom.script",
                                    "value": "true"
                                }
                            ]
                        },
                        "type": "simpleRunner",
                        "id": "RUNNER_2",
                        "name": "Zazu build"
                    }
                ]
            },
            "projectId": "_Root",
            "id": "ZazuGitHubDefault",
            "agent-requirements": {
                "count": 0
            },
            "features": {
                "count": 2,
                "feature": [
                    {
                        "type": "xml-report-plugin",
                        "id": "BUILD_EXT_1",
                        "properties": {
                            "count": 2,
                            "property": [
                                {
                                    "name": "xmlReportParsing.reportDirs",
                                    "value": "test_detail.xml\ntest/test_detail.xml"
                                },
                                {
                                    "name": "xmlReportParsing.reportType",
                                    "value": "gtest"
                                }
                            ]
                        }
                    },
                    {
                        "type": "teamcity.github.status",
                        "id": "BUILD_EXT_2",
                        "properties": {
                            "count": 7,
                            "property": [
                                {
                                    "name": "github_report_on",
                                    "value": "on start and finish"
                                },
                                {
                                    "name": "guthub_authentication_type",
                                    "value": "token"
                                },
                                {
                                    "name": "guthub_context",
                                    "value": "%env.TEAMCITY_PROJECT_NAME%/%env.TEAMCITY_BUILDCONF_NAME%"
                                },
                                {
                                    "name": "guthub_host",
                                    "value": "https://api.github.com/"
                                },
                                {
                                    "name": "guthub_owner",
                                    "value": "%gitHubOwner%"
                                },
                                {
                                    "name": "guthub_repo",
                                    "value": "%gitHubRepoPath%"
                                },
                                {
                                    "name": "secure:github_access_token",
                                    "value": ""
                                }
                            ]
                        }
                    }
                ]
            }
        }
        try:
            ret = self.get_build_type(build_type_id=template['id'])
            for p in template['parameters']['property']:
                self._put_helper('buildTypes/{}/parameters/{}'.format(template['id'], p['name']), str(p['value']),
                                 content_type='text/plain')
            for p in template['settings']['property']:
                self._put_helper('buildTypes/{}/settings/{}'.format(template['id'], p['name']), str(p['value']),
                                 content_type='text/plain')
            self.delete_and_post(ret, template, 'buildTypes', 'steps',    'step')
            self.delete_and_post(ret, template, 'buildTypes', 'triggers', 'trigger')
            # update all features that are not of type "teamcity.github.status", this requires special handling
            github_feature_id = ""
            for f in ret['features']['feature']:
                if f['type'] != 'teamcity.github.status':
                    self._delete_helper('buildTypes/{}/features/{}'.format(template['id'], f['id']))
                else:
                    github_feature_id = f['id']
            for f in template['features']['feature']:
                if f['type'] != 'teamcity.github.status':
                    self._post_helper('buildTypes/{}/features'.format(template['id']), f)
                else:
                    if github_feature_id:
                        for p in f['properties']['property']:
                            if 'secure:' not in p['name']:
                                self._put_helper('buildTypes/{}/features/{}/parameters/{}'.format(template['id'], github_feature_id, p['name']), str(p['value']),
                                                 content_type='text/plain')
                    else:
                        self._post_helper('buildTypes/{}/features'.format(template['id']), f)['id']

            ret = self.get_build_type(build_type_id=template['id'])
        except pyteamcity.HTTPError:
            ret = self._post_helper('buildTypes', template)
        return ret

    def delete_and_post(self, current, target, uri, field, subfield):
        for p in current[field][subfield]:
            self._delete_helper('{}/{}/{}/{}'.format(uri, target['id'], field, p['id']))
        for p in target[field][subfield]:
            self._post_helper('{}/{}/{}'.format(uri, target['id'], field), p)

    def setup_vcs_root(self, name, parent_project_id, git_url):
        vcs_root = {
            'name': str(name),
            'id': '{}_{}'.format(parent_project_id, name),
            'vcsName': 'jetbrains.git',
            'project': {'id': str(parent_project_id)},
            'properties': {
                'property': [
                    {'name': 'agentCleanFilesPolicy',
                     'value': 'ALL_UNTRACKED'},
                    {'name': 'agentCleanPolicy',
                     'value': 'ON_BRANCH_CHANGE'},
                    {"name": "authMethod",
                     "value": "TEAMCITY_SSH_KEY"},
                    {"name": "teamcitySshKey",
                     "value": "TeamCity SSH Key"},
                    {'name': 'branch',
                     'value': 'refs/heads/develop'},
                    {'name': 'ignoreKnownHosts',
                     'value': 'true'},
                    {'name': 'submoduleCheckout',
                     'value': 'CHECKOUT'},
                    {'name': 'teamcity:branchSpec',
                     'value': '+:refs/heads/develop\n+:refs/heads/master\n+:refs/pull/(*/merge)'},
                    {'name': 'url',
                     'value': str(git_url)},
                    {'name': 'useAlternates',
                     'value': 'true'},
                    {'name': 'username',
                     'value': 'git'},
                    {'name': 'usernameStyle',
                     'value': 'USERID'}
                ]
            }
        }
        try:
            ret = self.teamcity_handle().get_vcs_root_by_vcs_root_id(vcs_root['id'])
            for p in vcs_root['properties']['property']:
                self._put_helper('vcs-roots/{}/properties/{}'.format(vcs_root['id'], p['name']), str(p['value']),
                                 content_type='text/plain')
        except pyteamcity.HTTPError:
            ret = self._post_helper('vcs-roots', vcs_root)
        return ret

    def setup_project(self, name, description, parent_project_id):
        project_data = {
            'name': name,
            'description': description
        }
        if parent_project_id is not None:
            id = '{}_{}'.format(parent_project_id, name)
        else:
            id = name
        try:
            ret = self.teamcity_handle().get_project_by_project_id(id)
            # TODO update description
            for k, v in project_data.items():
                self._put_helper('projects/{}/{}'.format(id, k), str(v), content_type='text/plain')
            ret = self.teamcity_handle().get_project_by_project_id(id)
        except pyteamcity.HTTPError:
            if parent_project_id is not None:
                project_data['parentProject'] = {'id': parent_project_id}
            project_data['id'] = id
            ret = self._post_helper('projects', project_data)
        return ret

    def add_vcs_root_to_build(self, vcs_root_id, build_config_id):
        vcs_root_entry = {
            "id": str(vcs_root_id),
            "checkout-rules": "",
            "vcs-root": {
                "id": str(vcs_root_id)
            }
        }
        return self._post_helper('buildTypes/id:{}/vcs-root-entries'.format(build_config_id), vcs_root_entry)

    def add_template_to_build(self, template_id, build_config_id):
        return self._put_helper('buildTypes/id:{}/template'.format(build_config_id), template_id,
                                content_type='text/plain', accept_type='application/json')

    def add_parameters_to_build(self, parameters, build_config_id):
        for k, v in parameters.items():
            self._put_helper('buildTypes/id:{}/parameters/{}'.format(build_config_id, k), str(v),
                             content_type='text/plain')

    def apply_settings_to_build(self, settings, build_config_id):
        for k, v in settings.items():
            self._put_helper('buildTypes/id:{}/settings/{}'.format(build_config_id, k), str(v),
                             content_type='text/plain')

    def add_agent_requirements_to_build(self, agent_requirements, build_config_id):
        for a in agent_requirements:
            request = {
                "id": a['name'],
                "type": a['type'],
                "properties": {
                    "count": 2,
                    "property": [
                        {
                            "name": "property-name",
                            "value": a['name']
                        },
                        {
                            "name": "property-value",
                            "value": a['value']
                        }
                    ]
                }
            }
            try:
                self._put_helper('buildTypes/id:{}/agent-requirements/{}'.format(build_config_id, request['id']), request)
            except Exception:
                self._post_helper('buildTypes/id:{}/agent-requirements'.format(build_config_id), request)

    def setup_build_configuration(self, name, description, parent_project_id,
                                  vcs_root_id, template_id, parameters, settings, agent_requirements):
        build_conf = {
            'name': str(name),
            'project': {
                'id': str(parent_project_id)
            }
        }
        if description is not None:
            build_conf['description'] = str(description),

        try:
            project = self.teamcity_handle().get_project_by_project_id(parent_project_id)
            build_types = project['buildTypes']['buildType']
            ret = [x for x in build_types if x['name'] == name][0]
        except (pyteamcity.HTTPError, IndexError):
            ret = self._post_helper(
                str('projects/id:{}/buildTypes').format(parent_project_id), build_conf)
        self.add_vcs_root_to_build(vcs_root_id, ret['id'])
        self.add_template_to_build(template_id, ret['id'])
        self.add_parameters_to_build(parameters, ret['id'])
        self.apply_settings_to_build(settings, ret['id'])
        self.add_agent_requirements_to_build(agent_requirements, ret['id'])
        return ret

    def _post_helper(self, uri, json_data):
        click.echo("POST to {} {}".format(uri, json.dumps(json_data)))
        ret = requests.post(str(self.teamcity_handle().base_url + '/' + uri),
                            auth=(self.teamcity_handle().username, self.teamcity_handle().password),
                            headers={'Accept': 'application/json'},
                            json=json_data)
        if 300 < ret.status_code >= 200:
            raise Exception("Request returned error code {}, {}".format(
                ret.status_code, ret.text))
        return ret.json()

    def _delete_helper(self, uri):
        click.echo("DELETE {}".format(uri))
        ret = requests.delete(str(self.base_url + '/' + uri),
                              auth=(self.username, self.password),
                              headers={'Accept': 'application/json'})
        if 300 < ret.status_code >= 200:
            raise Exception("Request returned error code {}, {}".format(
                ret.status_code, ret.text))
        return ret

    def _put_helper(self, uri, data, content_type='application/json', accept_type=None):
        if 'application/json' in content_type:
            data = json.dumps(data)
        click.echo("PUT to {} {}".format(uri, data))
        if accept_type is None:
            accept_type = content_type
        ret = requests.put(str(self.teamcity_handle().base_url + '/' + uri),
                           auth=(self.teamcity_handle().username, self.teamcity_handle().password),
                           headers={'Accept': accept_type,
                                    'Content-type': content_type},
                           data=data)
        if 300 < ret.status_code >= 200:
            raise Exception("Request returned error code {}, {}".format(
                ret.status_code, ret.text))
        if content_type == 'application/json':
            ret = ret.json()
        return ret

    @staticmethod
    def publish_artifacts(artifact_paths):
        if teamcity.is_running_under_teamcity():
            messenger = teamcity.messages.TeamcityServiceMessages()
            for a in artifact_paths:
                messenger.publishArtifacts(a)

    @staticmethod
    def type():
        return 'TeamCity'

    @staticmethod
    def from_config(config):
        try:
            url = config['url']
        except KeyError:
            raise zazu.ZazuException('TeamCity config requires a "url" field')

        from future.moves.urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.netloc:
            components = parsed.netloc.split(':')
            address = components.pop(0)
            try:
                port = int(components.pop(0))
            except IndexError:
                port = 80
            protocol = parsed.scheme

        else:
            raise zazu.ZazuException('Unable to parse Teamcity URL "{}"'.format(url))

        tc = TeamCityBuildServer(address=address,
                                 port=port,
                                 protocol=protocol)
        return tc

    def setup_component(self, component, repo_name, git_url):
        project_name = component.name()
        project_description = component.description()
        parent_project_id = self.setup_project(project_name, project_description, None)['id']
        vcs_root_id = self.setup_vcs_root(project_name, parent_project_id, git_url)['id']
        organization, repo = github_helper.parse_github_url(git_url)
        for g in component.goals().values():
            subproject_id = self.setup_project(
                g.name(), g.description(), parent_project_id)['id']
            for a in g.builds().values():
                template_id = 'ZazuGitHubDefault'
                parameters = {
                    'architecture': a.build_arch(),
                    'goal': g.name(),
                    'gitHubRepoPath': repo_name,
                    'gitHubOwner': organization,
                    'buildType': a.build_type()
                }

                settings = {
                    'checkoutMode': 'ON_AGENT'
                }

                agent_requirements = []
                if 'win-msvc' in a.build_arch():
                    agent_requirements.append({
                        'name': "teamcity.agent.jvm.os.name",
                        'type': 'contains',
                        'value': 'Windows'
                    })
                else:
                    agent_requirements.append({
                        'name': "teamcity.agent.jvm.os.name",
                        'type': 'equals',
                        'value': 'Linux'
                    })
                self.setup_build_configuration(a.build_arch(),
                                               a.build_description(),
                                               subproject_id,
                                               vcs_root_id,
                                               template_id,
                                               parameters,
                                               settings,
                                               agent_requirements)

# Some ideas for more TC interaction:
# check status of builds associated with this branch
# add support for tagging builds (releases)
