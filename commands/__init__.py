#modularization playground
import pkgutil
import argparse


print("__INIT__")
print(pkgutil.extend_path(__path__, __name__))

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help="internal sub command help")


class CommandManager:
    def __init__(self):
        self.parser = argparse.ArgumentParser()

manager = CommandManager()
# print(__path__)


# USE importlib.load_module()
# dont __import__()
modules = dict()

print('\nfind module')
for importer, module, is_pkg in pkgutil.iter_modules(__path__):
    mod = importer.find_module(module).load_module(module)

    print('  '+ str(mod))

print('\nwalk packages')

for i in pkgutil.walk_packages(__path__):
    print('pkgs:' + str(i))
    importer, module, is_pkg = i
    if not is_pkg:
        print("  set:"+module)
        # mod = importer.find_module(module).load_module(module)
        # setattr(modules, module, __import__(module))

print(__path__)
print(__name__)
print('modules:')
for importer, modname, is_pkg in pkgutil.walk_packages(path=__path__, prefix=__name__+'.'):
    if not is_pkg:
        #print(dir(importer.find_module(modname)))
        module = importer.find_module(modname).load_module()
        if hasattr(module, 'register_subcommand'):
            module.register_subcommand(subparsers)
            print(module)
        #print(dir(module))

args = parser.parse_args('init --uid rawr'.split())

kwargs = vars(args)
print(kwargs)
func = kwargs.pop('func')
func(**kwargs)
