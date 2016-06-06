import functools
import pathlib
import typing  # noqa
import warnings

from pytest import fixture, mark, raises

from settei.app import config_property, Configuration, ConfigWarning
from settei.cli import Cli


@fixture
def fx_mock_input():
    def fake_input(m=None, answer='y', config_value=None):
        if m is not None:
            if m.startswith('Use default?'):
                return answer
            elif m.startswith('Custom configuration'):
                return config_value
        return None

    return fake_input


class TestConfig(dict):
    depth1_required = config_property('key', int)
    depth1_optional = config_property('key', int, default='')
    depth1_warn = config_property('key', int, default='', default_warning=True)
    depth1_default_func = config_property(
        'key', int,
        default_func=lambda self: self.depth1_optional
    )
    depth1_default_func_warn = config_property(
        'key', int,
        default_func=lambda self: self.depth1_optional,
        default_warning=True
    )
    depth2_required = config_property('section.key', str)
    depth2_optional = config_property('section.key', str, default=None)
    depth2_warn = config_property('section.key', str,
                                  default=None, default_warning=True)
    union = config_property('union', typing.Union[int, str])


class TestAppConfig(Configuration):
    database_url = config_property(
        'database.url', str,
        default='sqlite:///test_app.db', default_warning=True
    )


@mark.parametrize('union_value', [123, 'string'])
def test_config_property(union_value: typing.Union[int, str]):
    c = TestConfig(key=123, section={'key': 'val'}, union=union_value)
    assert c.depth1_required == 123
    with warnings.catch_warnings(record=True) as w:
        assert c.depth1_optional == 123
        assert len(w) == 0
    with warnings.catch_warnings(record=True) as w:
        assert c.depth1_warn == 123
        assert len(w) == 0
    with warnings.catch_warnings(record=True) as w:
        assert c.depth1_default_func == 123
        assert len(w) == 0
    with warnings.catch_warnings(record=True) as w:
        assert c.depth1_default_func_warn == 123
        assert len(w) == 0
    assert c.depth2_required == 'val'
    with warnings.catch_warnings(record=True) as w:
        assert c.depth2_optional == 'val'
        assert len(w) == 0
    with warnings.catch_warnings(record=True) as w:
        assert c.depth2_warn == 'val'
        assert len(w) == 0
    assert c.union == union_value


def test_config_property_absence():
    c = TestConfig()
    with raises(KeyError):
        c.depth1_required
    with warnings.catch_warnings(record=True) as w:
        assert c.depth1_optional == ''
        assert len(w) == 0
    with warnings.catch_warnings(record=True) as w:
        assert c.depth1_warn == ''
        assert len(w) == 1
        assert issubclass(w[-1].category, ConfigWarning)
    with warnings.catch_warnings(record=True) as w:
        assert c.depth1_default_func == ''
        assert len(w) == 0
    with warnings.catch_warnings(record=True) as w:
        assert c.depth1_default_func_warn == ''
        assert len(w) == 1
        assert issubclass(w[-1].category, ConfigWarning)
    with raises(KeyError):
        c.depth2_required
    with warnings.catch_warnings(record=True) as w:
        assert c.depth2_optional is None
        assert len(w) == 0
    with warnings.catch_warnings(record=True) as w:
        assert c.depth2_warn is None
        assert len(w) == 1
        assert issubclass(w[-1].category, ConfigWarning)
    with raises(KeyError):
        c.union


def test_config_property_absence_2nd_depth():
    c = TestConfig(section={})
    with raises(KeyError):
        c.depth2_required
    with warnings.catch_warnings(record=True) as w:
        assert c.depth2_optional is None
        assert len(w) == 0
    with warnings.catch_warnings(record=True) as w:
        assert c.depth2_warn is None
        assert len(w) == 1
        assert issubclass(w[-1].category, ConfigWarning)


def test_app_from_file(tmpdir):
    path = tmpdir.join('cfg.toml')
    path.write('''
    [database]
    url = "sqlite:///a.db"
    ''')
    with path.open() as f:
        cfg = TestAppConfig.from_file(f)
    assert cfg.database_url == 'sqlite:///a.db'


def test_app_from_path(tmpdir):
    path = tmpdir.join('cfg.toml')
    path.write('''
    [database]
    url = "sqlite:///b.db"
    ''')
    cfg = TestAppConfig.from_path(pathlib.Path(path.strpath))
    assert cfg.database_url == 'sqlite:///b.db'


def test_cli_config_properties():
    cli = Cli(TestAppConfig)
    properties = list(cli.config_properties)
    assert len(properties) == 1
    assert properties[0] == ('database_url', TestAppConfig.database_url)


def test_cli_input_configs_default_y(monkeypatch, fx_mock_input):
    monkeypatch.setitem(__builtins__, 'input', fx_mock_input)
    cli = Cli(TestAppConfig)
    config = cli.input_configs()
    assert config == {'database': {'url': 'sqlite:///test_app.db'}}


def test_cli_input_configs_default_n(monkeypatch, fx_mock_input):
    pgsql_url = 'postgresql://local'
    monkeypatch.setitem(
        __builtins__,
        'input',
        functools.partial(fx_mock_input, answer='N', config_value=pgsql_url)
    )
    cli = Cli(TestAppConfig)
    config = cli.input_configs()
    assert config == {'database': {'url': pgsql_url}}
