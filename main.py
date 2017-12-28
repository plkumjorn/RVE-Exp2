#!/usr/bin/python
# -*- coding: utf-8 -*-

# ---------------------------------------------------------------------------------------------------
# Basic libraries
import sys, json, csv, re, string, nltk, math, urllib, io
import numpy as np
# ---------------------------------------------------------------------------------------------------
# Our methods and helpers
from xmlOWL import *
from SPARQLEndpoint import *
import SDType
# ---------------------------------------------------------------------------------------------------
def loadTestCases(filename):
	testcases = list()
	input_file = csv.DictReader(io.open(filename, encoding="utf-8"))
	for row in input_file:
		testcases.append({'s': row['s'], 'p': row['p'], 'o': row['o'], 'r':row['r']})
	return testcases

def processATestCase(rve):
	print(SDType.probOfType(rve['r'], rve['o']), rve['r'], rve['o'])


testcases = loadTestCases('RVEsSampledServer300-20171229033026.csv')
for t in testcases[0:5]:
	processATestCase(t)


		