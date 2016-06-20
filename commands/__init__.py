#modularization playground
import pkgutil

print("__INIT__")
print(pkgutil.extend_path(__path__, __name__))
# print(__path__)


# USE importlib.load_module()
# dont __import__()
modules = dict()

for importer, module, is_pkg in pkgutil.iter_modules(__path__):
    mod = importer.find_module(module).load_module(module)
    print(mod)

for i in pkgutil.walk_packages(__path__):
    print('pkgs:' + str(i))
    importer, module, is_pkg = i
    if not is_pkg:
        print("set:"+module)
        #mod = importer.find_module(module).load_module(module)
        #setattr(modules, module, __import__(module))


for importer, modname, ispkg in pkgutil.walk_packages(path=__path__, prefix=__name__+'.'):
    print(modname)

