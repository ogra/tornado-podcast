#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml

__SETTINGS_FILE__ = "configs.yaml"

f = open(__SETTINGS_FILE__, 'r')
configs = yaml.load(f)
f.close()

if __name__ == '__main__':
    pass
