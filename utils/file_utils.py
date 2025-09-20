import json
import os

from cachetools import LRUCache, cached
from ruamel.yaml import YAML

PROJECT_BASE = os.getenv("PROJECT_BASE") or os.getenv("DEPLOY_BASE")
RAG_BASE = os.getenv("BASE")


def get_project_base_directory(*args):
    global PROJECT_BASE
    if PROJECT_BASE is None:
        PROJECT_BASE = os.path.dirname(os.path.abspath(os.path.join(__file__, '..')))

    if args:
        return os.path.join(PROJECT_BASE, *args)
    return PROJECT_BASE
def join_project_base_path(relative_path):
    base_path=get_project_base_directory()
    return os.path.join(base_path, relative_path)



def get_rag_directory(*args):
    global RAG_BASE
    if RAG_BASE is None:
        RAG_BASE = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                os.pardir,
                os.pardir,
                os.pardir,
            )
        )
    if args:
        return os.path.join(RAG_BASE, *args)
    return RAG_BASE

@cached(cache=LRUCache(maxsize=10))
def load_json_conf(conf_path):
    if os.path.isabs(conf_path):
        json_conf_path = conf_path
    else:
        json_conf_path = os.path.join(get_project_base_directory(), conf_path)
    try:
        with open(json_conf_path) as f:
            return json.load(f)
    except BaseException:
        raise EnvironmentError("loading json file config from '{}' failed!".format(json_conf_path))


def dump_json_conf(config_data, conf_path):
    if os.path.isabs(conf_path):
        json_conf_path = conf_path
    else:
        json_conf_path = os.path.join(get_project_base_directory(), conf_path)
    try:
        with open(json_conf_path, "w") as f:
            json.dump(config_data, f, indent=4)
    except BaseException:
        raise EnvironmentError("loading json file config from '{}' failed!".format(json_conf_path))


def load_json_conf_real_time(conf_path):
    if os.path.isabs(conf_path):
        json_conf_path = conf_path
    else:
        json_conf_path = os.path.join(get_project_base_directory(), conf_path)
    try:
        with open(json_conf_path) as f:
            return json.load(f)
    except BaseException:
        raise EnvironmentError("loading json file config from '{}' failed!".format(json_conf_path))


def load_yaml_conf(conf_path):
    if not os.path.isabs(conf_path):
        conf_path = os.path.join(get_project_base_directory(), conf_path)
    try:
        with open(conf_path) as f:
            yaml = YAML(typ="safe", pure=True)
            return yaml.load(f)
    except Exception as e:
        raise EnvironmentError("loading yaml file config from {} failed:".format(conf_path), e)


def rewrite_yaml_conf(conf_path, config):
    if not os.path.isabs(conf_path):
        conf_path = os.path.join(get_project_base_directory(), conf_path)
    try:
        with open(conf_path, "w") as f:
            yaml = YAML(typ="safe")
            yaml.dump(config, f)
    except Exception as e:
        raise EnvironmentError("rewrite yaml file config {} failed:".format(conf_path), e)


def rewrite_json_file(filepath, json_data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4, separators=(",", ": "))
    f.close()
