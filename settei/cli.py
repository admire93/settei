"""
settei.cli
~~~~~~~~~~

"""
import argparse
import inspect
import pathlib
import typing

from pytoml import dumps

from .app import config_property, Configuration

__all__ = 'Cli',


def _prompt(doc: str, is_required: bool=True,
            default: typing.Optional[str]=None):
    """Ask you to create default or custom configuration."""
    yes_opt = {'y', 'yes', 'YES'}
    no_opt = {'N', 'no', 'NO'}
    all_opt = yes_opt.union(no_opt)
    choice = False
    print(doc)
    if not is_required:
        c = None
        while c not in all_opt:
            default_help = default if default is not None else ''
            c = input('Use default? {} y/N:'.format(default_help))
            if c not in all_opt:
                print('Invalid option `{}`, choice one of ({})'.format(
                    c,
                    ','.join(all_opt)
                ))
        choice = c in no_opt
    if not is_required and not choice:
        return default
    conf = None
    while not conf:
        conf = input('Custom configuration value: ')
    return conf


def _set_config(s: typing.Mapping[str, typing.Any], k: str, v: typing.Any):
    """Set config value ``v`` into ``s`` using ``k``\ ."""
    splited = k.split('.')
    this_key, splited = splited[0], splited[1:]
    if splited:
        s.setdefault(this_key, {})
        _set_config(s[this_key], '.'.join(splited), v)
    else:
        s[this_key] = v


class Cli:
    """Provide CLI help writing Settei configuration into TOML.

    .. code-block:: python

       class App(Configuration):
           pass


       if __name__ == '__main__':
           Cli(App).main()


    :param config_class: the configuration class which is inherited
                         :class:`~settei.config.Configuration`\ .

    """

    def __init__(self, config_class: Configuration):
        self.config_class = config_class

    @property
    def config_properties(self) -> typing.Generator:
        """Yield :class:`~settei.config.config_property` of
        :attr:`~.Cli.config_class`

        :return: the generator a tuple of attribute name and config property.

        """
        for attribute_name in dir(self.config_class):
            attr = getattr(self.config_class, attribute_name)
            if isinstance(attr, config_property):
                yield attribute_name, attr

    def input_configs(self) -> typing.Mapping[str, typing.Any]:
        """Take a configuration to config_property into :class:`dict`\ .

        :return: the dictionary contains configuration.

        """
        settings = {}
        for attr_name, prop in self.config_properties:
            docstring = inspect.getdoc(prop)
            if not docstring:
                docstring = "`{}`".format(attr_name)
            default = None
            if prop.default_set and not prop.default_value:
                default = prop.default_func(None)
            config_value = _prompt(
                docstring,
                not prop.default_set,
                default
            )
            if config_value:
                _set_config(settings, prop.key, prop.cls(config_value))
        return settings

    def main(self):
        """Run CLI.

        Suppose you write ``gen_config.py`` with ``service_name.config.App`` to
        create TOML.

        .. code-block:: python

           from service_name.config import App
           from settei.cli import Cli


           if __name__ == '__main__':
               Cli(App).main()

        then, run python script you wrote to get TOML.

        .. code-block::

           $ python gen_config.py -o ./dev.toml

        it generates ``dev.toml`` you are able to initialize with
        ``service_name.config.App`` class.

        .. code-block::

           app_config = App.from_path(pathlib.Path('.') / 'dev.toml')

        """
        parser = argparse.ArgumentParser(
            description='Generate Settei TOML configuration.'
        )
        parser.add_argument('--out', '-o', type=pathlib.Path,
                            action='store',
                            default=pathlib.Path.cwd() / 'sample.toml')
        args = parser.parse_args()
        confs = self.input_configs()
        with args.out.open('w') as f:
            f.write(dumps(confs).strip())
