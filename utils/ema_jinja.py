# -*- coding: utf-8 -*-
"""
Created on Sat Mar  2 08:02:04 2024

@author: workm
"""
import jinja2
def percent_format(val: float):
    return f"{round(val*100)}%"

def datetime_format(value, format="%Y-%m-%d"):
    return value.strftime(format)

jinja = jinja2.Environment()
jinja.filters["date"] = datetime_format
jinja.filters["pc"] = percent_format
