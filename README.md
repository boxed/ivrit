# ivrit

Generate type stubs for your project based on name->type mapping configuration. This is a hacky implementation of (Names can be so much more)[https://kodare.net/2023/02/02/names-can-be-so-much-more.html], as a proof-of-concept to show the idea.

Given the configuration in your `pyproject.toml` this code will generate `.pyi` stub files for your project next to the corresponding `.py` files, with types filled in. This way your primary code doesn't contain a lot of `user: User` and `name: str` annotations, as that is all centralized to the config file.

As this implementation is a hack based on type stub files, this has the pretty big disadvantage of having to be re-run on significant changes. It also can't insert this type information in other places than function signatures. Ideally a system like this should be able to handle local variables as well. 

Example configuration:

```toml
[tool.ivrit]
ignore_names = [
    's',
    'x',
    'a',
    'b',
    'c',
    'd',
    'e',
    'other',
]
ignore_filenames=[
]


[tool.ivrit.names]
request='django.core.handlers.wsgi.WSGIRequest'
user='example.models.User'
project='example.models.Project'
form='iommi.Form'
table='iommi.Table'
name='str'
pk='int'
url='str'
uuid='uuid.UUID'
path='str|pathlib.Path'
title='str'
```
