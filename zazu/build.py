# -*- coding: utf-8 -*-
"""Build command for zazu."""
import zazu.cmake_helper
import zazu.config
import zazu.util
zazu.util.lazy_import(locals(), [
    'click',
    'git',
    'os',
    'shutil',
    'semantic_version',
    'subprocess'
])


__author__ = "Nicholas Wiles"
__copyright__ = "Copyright 2016"


class ComponentConfiguration(object):
    """Store a configuration for a single component."""

    def __init__(self, component):
        """Construct configuration from config dictionary."""
        self._name = component['name']
        self._description = component.get('description', '')
        self._goals = {}
        for g in component['goals']:
            self._goals[g['name']] = BuildGoal(g)

    def get_spec(self, goal, arch, type):
        """Get a BuildSpec object for the given params."""
        try:
            build_goal = self.goals()[goal]
            ret = build_goal.get_build(arch)
            if type is not None:
                ret._build_type = type
        except KeyError:
            ret = BuildSpec(goal)
        return ret

    def description(self):
        """Get string description."""
        return self._description

    def name(self):
        """Get string name."""
        return self._name

    def goals(self):
        """Get list of goals."""
        return self._goals


class BuildGoal(object):
    """Store a configuration for a single build goal with one or more architectures."""

    def __init__(self, goal):
        """Create a build goal.

        Args:
            goal (str): the name of the goal.

        """
        self._name = goal.get('name', '')
        self._description = goal.get('description', '')
        self._build_type = goal.get('buildType', 'minSizeRel')
        self._build_vars = goal.get('buildVars', {})
        self._build_goal = goal.get('buildGoal', self._name)
        self._artifacts = goal.get('artifacts', [])
        self._builds = {}
        for b in goal['builds']:
            vars = b.get('buildVars', self._build_vars)
            type = b.get('buildType', self._build_type)
            build_goal = b.get('buildGoal', self._build_goal)
            description = b.get('description', '')
            arch = b['arch']
            script = b.get('script', None)
            artifacts = b.get('artifacts', self._artifacts)
            self._builds[arch] = BuildSpec(goal=build_goal,
                                           type=type,
                                           vars=vars,
                                           description=description,
                                           arch=arch,
                                           script=script,
                                           artifacts=artifacts)

    def description(self):
        """Get string description."""
        return self._description

    def name(self):
        """Get string name."""
        return self._name

    def goal(self):
        """Get string build goal."""
        return self._build_goal

    def builds(self):
        """Get dictionary of builds."""
        return self._builds

    def get_build(self, arch):
        """Get a build by arch."""
        if arch is None:
            if len(self._builds) == 1:
                only_arch = self._builds.keys()[0]
                click.echo("No arch specified, but there is only one ({})".format(only_arch))
                return self._builds[only_arch]
            else:
                raise click.ClickException("No arch specified, but there are multiple arches available")
        return self._builds[arch]


class BuildSpec(object):
    """A build specification that may have multiple target architectures."""

    def __init__(self, goal, type='minSizeRel', vars={}, requires={}, description='', arch='', script=None, artifacts=[]):
        """Create a BuildSpec.

        Args:
            goal (str): the goal name.
            type (str): the build type.
            vars (dict): key value pairs that are passed to the build.
            description (str): a description of the build spec.
            arch (str): the target architecture.
            script (list of str): the build script steps if one exists.
            artifacts (list of str): the list of artifacts to pass to CI.
        """
        self._build_goal = goal
        self._build_type = type
        self._build_vars = vars
        self._build_description = description
        self._build_arch = arch
        self._build_script = script
        self._build_artifacts = artifacts

    def build_type(self):
        """Return the build type string."""
        return self._build_type

    def build_artifacts(self):
        """Return the list of build artifacts."""
        return self._build_artifacts

    def build_goal(self):
        """Return the build goal string."""
        return self._build_goal

    def build_vars(self):
        """Return the dictionary of build variables."""
        return self._build_vars

    def build_description(self):
        """Return the build description string."""
        return self._build_description

    def build_arch(self):
        """Return the build architecture string."""
        return self._build_arch

    def build_script(self):
        """Return the list of build script steps."""
        return self._build_script


def cmake_build(repo_root, arch, type, goal, verbose, vars):
    """Build using cmake."""
    if arch not in zazu.cmake_helper.known_arches():
        raise click.BadParameter('Arch "{}" not recognized, choose from:\n'.format(arch, zazu.util.pprint_list(zazu.cmake_helper.known_arches())))

    build_dir = os.path.join(repo_root, 'build', '{}-{}'.format(arch, type))
    try:
        os.makedirs(build_dir)
    except OSError:
        pass
    ret = zazu.cmake_helper.configure(repo_root, build_dir, arch, type, vars, click.echo if verbose else lambda x: x)
    if ret:
        raise click.ClickException('Error configuring with cmake')
    ret = zazu.cmake_helper.build(build_dir, arch, type, goal, verbose)
    if ret:
        raise click.ClickException('Error building with cmake')
    return ret


def tag_to_version(tag):
    """Convert a git tag into a semantic version string.

    i.e. R4.1 becomes 4.1.0. A leading 'r' or 'v' is optional on the tag.
    """
    components = []
    if tag is not None:
        if tag.lower().startswith('r') or tag.lower().startswith('v'):
            tag = tag[1:]
        components = tag.split('.')
    major = '0'
    minor = '0'
    patch = '0'
    try:
        major = components[0]
        minor = components[1]
        patch = components[2]
    except IndexError:
        pass

    return '.'.join([major, minor, patch])


def make_semver(repo_root, build_number):
    """Parse SCM info and creates a semantic version."""
    branch_name, sha, tags = parse_describe(repo_root)
    if tags:
        # There are git tags to consider. Parse them all then choose the one that is latest (sorted by semver rules)
        return sorted([make_version_number(branch_name, build_number, tag, sha) for tag in tags])[-1]
    else:
        return make_version_number(branch_name, build_number, None, sha)


def parse_describe(repo_root):
    """Parse the results of git describe into branch name, sha, and tags."""
    repo = git.Repo(repo_root)
    try:
        sha = 'g{}{}'.format(repo.git.rev_parse('HEAD')[:7], '-dirty' if repo.git.status(['--porcelain']) else '')
        branch_name = repo.git.rev_parse(['--abbrev-ref', 'HEAD']).strip()
        # Get the list of tags that point to HEAD
        tag_result = repo.git.tag(['--points-at', 'HEAD'])
        tags = filter(None, tag_result.strip().split('\n'))
    except git.GitCommandError as e:
        raise click.ClickException(str(e))

    return branch_name, sha, tags


def sanitize_branch_name(branch_name):
    """Replace punctuation that cannot be in semantic version from a branch name with dashes."""
    return branch_name.replace('/', '-').replace('_', '-')


def make_version_number(branch_name, build_number, tag, sha):
    """Convert repo metadata and build version into a semantic version."""
    branch_name_sanitized = sanitize_branch_name(branch_name)
    build_info = ['sha', sha, 'build', str(build_number), 'branch', branch_name_sanitized]
    prerelease = []
    if tag is not None:
        version = tag_to_version(tag)
    elif branch_name.startswith('release/') or branch_name.startswith('hotfix/'):
        version = tag_to_version(branch_name.split('/', 1)[1])
        prerelease = [str(build_number)]
    else:
        version = '0.0.0'
        prerelease = [str(build_number)]
    semver = semantic_version.Version(version)
    semver.prerelease = prerelease
    semver.build = build_info

    return semver


def pep440_from_semver(semver):
    """Convert semantic version to PEP440 compliant version."""
    segment = ''
    if semver.prerelease:
        segment = '.dev{}'.format('.'.join(semver.prerelease))
    local_version = '.'.join(semver.build)
    local_version = local_version.replace('-', '.')
    version_str = '{}.{}.{}{}'.format(semver.major, semver.minor, semver.patch, segment)
    # Include the local version if we are not a true release
    if local_version and semver.prerelease:
        version_str = '{}+{}'.format(version_str, local_version)
    return version_str


def script_build(repo_root, spec, build_args, verbose):
    """Build using a provided shell script."""
    env = os.environ
    env.update(build_args)
    for s in spec.build_script():
        if verbose:
            click.echo(str(s))
        ret = subprocess.call(str(s), shell=True, cwd=repo_root, env=env)
        if ret:
            raise click.ClickException("{} exited with code {}".format(str(s), ret))


def parse_key_value_pairs(arg_string):
    """Parse a argument string in the form x=y j=k and returns a dictionary of the key value pairs."""
    try:
        return {key: value for (key, value) in [tuple(str(arg).split('=', 1)) for arg in arg_string]}
    except ValueError:
        raise click.ClickException("argument string must be in the form x=y")


def add_version_args(repo_root, build_num, args):
    """Add version strings and build number arguments to args."""
    try:
        semver = semantic_version.Version(args['ZAZU_BUILD_VERSION'])
    except KeyError:
        semver = make_semver(repo_root, build_num)
        args['ZAZU_BUILD_VERSION'] = str(semver)
    args["ZAZU_BUILD_NUMBER"] = str(build_num)
    args['ZAZU_BUILD_VERSION_PEP440'] = pep440_from_semver(semver)


@click.command()
@click.pass_context
@click.option('-a', '--arch', help='the desired architecture to build for')
@click.option('-t', '--type', type=click.Choice(zazu.cmake_helper.build_types),
              help='defaults to what is specified in the config file, or release if unspecified there')
@click.option('-n', '--build_num', help='build number', default=os.environ.get('BUILD_NUMBER', 0))
@click.option('-v', '--verbose', is_flag=True, help='generates verbose output from the build')
@click.argument('goal')
@click.argument('extra_args_str', nargs=-1)
def build(ctx, arch, type, build_num, verbose, goal, extra_args_str):
    """Build project targets, the GOAL argument is the configuration name from zazu.yaml file or desired make target."""
    # Run the supplied build script if there is one, otherwise assume cmake
    # Parse file to find requirements then check that they exist, then build
    project_config = ctx.obj.project_config()
    component = ComponentConfiguration(project_config['components'][0])
    spec = component.get_spec(goal, arch, type)
    build_args = {}
    extra_args = parse_key_value_pairs(extra_args_str)
    build_args.update(spec.build_vars())
    build_args.update(extra_args)
    add_version_args(ctx.obj.repo_root, build_num, build_args)
    if spec.build_script() is None:
        cmake_build(ctx.obj.repo_root, spec.build_arch(), spec.build_type(), spec.build_goal(), verbose, build_args)
    else:
        script_build(ctx.obj.repo_root, spec, build_args, verbose)
    try:
        ctx.obj.build_server().publish_artifacts(spec.build_artifacts())
    except click.ClickException:
        pass
