# Ivrit "Hebrew". The True Name gives power of the thing. In hebrew every word is the True Name.

import os
import re
from _ast import (
    alias,
    AnnAssign,
    arg,
    arguments,
    Assign,
    ClassDef,
    FunctionDef,
    Import,
    ImportFrom,
    Name,
)
from ast import (
    parse,
    unparse,
)
from collections import Counter
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Dict,
    List,
    Optional,
    Set,
)

import toml
from gitignorefile import Cache


@dataclass(kw_only=True)
class Config:
    names: Dict[str, str] = field(default_factory=lambda: {})
    ignore_names: Set[str] = field(default_factory=lambda: set())
    ignore_filenames: Set[str] = field(default_factory=lambda: set())


# noinspection PyArgumentList
def read_config() -> Config:
    try:
        with open('pyproject.toml') as f:
            config = Config(**toml.load(f)['tool']['ivrit'])
            config.ignore_names = set(config.ignore_names)
            config.ignore_filenames = set(config.ignore_filenames)
            return config
    except (FileNotFoundError, KeyError):
        return Config()


ellipsis = parse('...').body[0]


def walk_respecting_gitignore(path):
    ignored = Cache()
    for root, dirs, files in os.walk(path):
        dirs[:] = [x for x in dirs if not ignored(x) and not x == '.git']
        files[:] = [x for x in files if not ignored(x)]
        yield root, dirs, files


def generate_stubs(x, config, possible_names):
    made_changes = False

    ast = parse(x)

    needed_imports = set()

    class_annotations: Optional[List] = None

    def mod_arg(arg):
        if arg.annotation:
            return

        if arg.arg in ('self', 'cls') or arg.arg in config.ignore_names:
            return

        full_type_name = config.names.get(arg.arg)
        if not full_type_name:
            possible_names[arg.arg] += 1
            return

        arg.annotation = Name(id=full_type_name)

        needed_imports.add(full_type_name)

        nonlocal made_changes
        made_changes = True

    def mod(node):
        nonlocal class_annotations

        if isinstance(node, FunctionDef):
            if node.name == '__init__':
                return node

            for arg_ in node.args.args:
                mod_arg(arg_)
            for arg_ in node.args.kwonlyargs:
                mod_arg(arg_)
            for arg_ in node.args.posonlyargs:
                mod_arg(arg_)

            node.body = [ellipsis]
            return node

        if hasattr(node, 'body'):
            node.body = [mod(x) for x in node.body]
            node.body = [x for x in node.body if x]
            if not node.body:
                node.body = [ellipsis]

        if isinstance(node, ClassDef):
            prev_class_annotations = class_annotations
            class_annotations = []

            for x in node.body:
                mod(x)

            has_constructor = any(x for x in node.body if isinstance(x, FunctionDef) and x.name == '__init__')
            if class_annotations and not has_constructor:
                node.body.append(
                    FunctionDef(
                        name='__init__',
                        decorator_list=[],
                        lineno=0,
                        args=arguments(
                            posonlyargs=[],
                            args=[
                                arg(
                                    arg='self',
                                ),
                            ],
                            defaults=[],
                            kw_defaults=[
                                x.value
                                for x in class_annotations
                            ],
                            kwonlyargs=[
                                arg(
                                    arg=x.target.id,
                                    annotation=x.annotation,
                                )
                                for x in class_annotations
                            ]
                        ),
                        body=[ellipsis],
                    )
                )

            class_annotations = prev_class_annotations
            return node

        if isinstance(node, AnnAssign):
            if class_annotations is not None:
                class_annotations.append(node)
            return node

        if isinstance(node, (Import, ImportFrom, Assign)):
            return node

        return None

    mod(ast)

    imports = set()

    for full_type_name in needed_imports:
        for name in re.findall(r'''(\b[^\[\]]+)''', full_type_name):
            imports.add(name)

    for name in imports:
        module_name, _, type_name = name.rpartition('.')
        if not module_name:
            continue

        ast.body.insert(0, Import(names=[alias(module_name)]))

    return unparse(ast) if made_changes else None


def main():
    config = read_config()
    possible_names = Counter()

    for root, dirs, files in walk_respecting_gitignore('.'):
        for filename in files:
            if not filename.endswith('.py'):
                continue

            if filename in config.ignore_filenames:
                continue

            full_path = os.path.join(root, filename)
            with open(full_path) as f:
                result = generate_stubs(f.read(), config=config, possible_names=possible_names)

            if result is not None:
                with open(full_path + 'i', 'w') as f:
                    f.write(result)

    total = possible_names.total()

    for name, count in possible_names.most_common(40):
        if count / total > 0.05:
            print(name.ljust(20), str(count).rjust(6))


if __name__ == '__main__':
    main()
