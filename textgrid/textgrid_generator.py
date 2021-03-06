# -*- coding: utf-8 -*-
# textgrid_generator.py - usage: python textgrid_generator.py configure.txt
# to parse the configure.txt and translate it into textgrid files
# author: xiao yang <xiaoyang0117@gmail.com>
# date: 2015.01.19
# the format of the text to parse is below:
# http://crowdfile.blob.core.chinacloudapi.cn/cutted-wav-blob/20150810_225453_52_193.63_194.975.wav	1	0.00785	1.44	我有去问我一个	1.44

import os
import sys
import re
import subprocess


APPENDIX = ".TextGrid"
TEMPLATE_HEADER = """File type = "ooTextFile"
Object class = "TextGrid"

xmin = {global_xmin}
xmax = {global_xmax}
tiers? <exists>
size = 2
item []:
"""

TEMPLATE_ITEM = """	item [{item_index}]:
		class = "IntervalTier"
		name = "text"
		xmin = {global_xmin}
		xmax = {global_xmax}
		intervals: size = {intervals_size}
"""

TEMPLATE_INTERVALS = """			intervals [{interval_index}]:
			xmin = {local_xmin}
			xmax = {local_xmax}
			text = "{text}"
"""

# URL_PATTERN = '.*/(?P<name>.+)_(?P<slice>\d+)_(?P<start>[\d.]+)_(?P<end>[\d.]+)\.[wav|mp3|8K]'
URL_PATTERN = '^(?P<name>.+)_(?P<slice>\d+)_(?P<start>[\d.]+)_(?P<end>[\d.]+)\.[mp3|wav]'
# URL_PATTERN = '.*/(?P<name>.+)_(?P<start>[\d.]+)_(?P<end>[\d.]+)\.[wav|mp3|8K]'

PATTERN_BODY = '(?P<name>.+)_(?P<slice>\d+)_(?P<start>[\d.]+)_(?P<end>[\d.]+)\.[mp3|wav|8K]'
SLICE_PATTERN = '_(?P<slice>\d+)'
DEFAULT_MEDIA = u'.wav'
SLICE_BOUND = 10000

#sort and organize
def parse_file(src, items):
	with open(src, "r") as f:
		for line in f:
			parse_line(line, items)

# a line could be "http://crowdfile.blob.core.chinacloudapi.cn/cutted-wav-blob/20150825_124045_945_3693.92_3695.515.wav"
# or "20150825_124045_945_3693.92_3695.515.wav"
# or "20150825_124045_192392392_3693.92_3695.515.wav" (no slice)
def guess_pattern(line):
	if line.startswith('http:'):
		PATTERN_HEAD = '.*/'
	else:
		PATTERN_HEAD = '^'
	pattern = PATTERN_HEAD + PATTERN_BODY
	try:
		groups = re.match(pattern, line, re.UNICODE).groupdict()
		assert float(groups['slice']) < SLICE_BOUND
		return pattern
	except (AttributeError, AssertionError) as e:
		return pattern.replace(SLICE_PATTERN, '')


# to convert lines in the config into a dict with keys described below
# items = { 
# 	'20150810_225453': [
# 		{ 'slice': 52, 'xmin': 193.63785, 'xmax': 195.07, 'text': u'我有去问我一个'},
# 		{ ... }
# 		] 
# 	}
def parse_line(line, items):
	columns = line.split('\t')
	if columns[1] == '1':
		url = unicode(columns[0], 'utf-8')
		try:
			pattern = guess_pattern(url)
			groups = re.search(pattern, url, re.UNICODE).groupdict()
			# for an exception
			if columns[2] == 'None':
				columns[2] = 0
			# for the pattern without the variable slice
			slice_no = groups.setdefault('slice', None)
			info = {'slice': slice_no, 'xmin': float(groups['start'])+float(columns[2]), 'xmax': float(groups['start'])+float(columns[3]), 'text': columns[4]}
		except (AttributeError, ValueError) as e:
			print "Unable to parse the url: " + url
			return

		items.setdefault(groups['name'], []).append(info)


def generate_interval(aslice, interval_index, text=''):
	return TEMPLATE_INTERVALS.format(interval_index=interval_index, local_xmin=aslice['xmin'], local_xmax=aslice['xmax'], text=text.encode('utf-8'))

def generate_output(filled_slices):
	intervals_size = len(filled_slices)
	global_xmin = filled_slices[0]['xmin']
	global_xmax = filled_slices[intervals_size-1]['xmax']
	
	output = TEMPLATE_HEADER.format(**locals())
	# first time: fill it with empty text
	item_index = 1
	output += TEMPLATE_ITEM.format(**locals())
	for i, aslice in enumerate(filled_slices, start=1):
		output += generate_interval(aslice, i)

	# second time: fill it with real text
	item_index = 2
	output += TEMPLATE_ITEM.format(**locals())
	for i, aslice in enumerate(filled_slices, start=1):
		output += generate_interval(aslice, i, text=aslice['text'])
	return output

# to fill 'gaps' in the list of slices
# gaps means the values of xmax and xmin in continus slices are not the same
def prefill_slices(slices):
	ordered_slices = sorted(slices, key=lambda x:x['xmin'])
	previous_xmax = 0
	filled_slices = []
	for aslice in ordered_slices:
		if previous_xmax < aslice['xmin']:
			filled_slices.append({'slice': int(aslice['slice'])-1, 'xmin': previous_xmax, 'xmax': aslice['xmin'], 'text': ''})
		elif previous_xmax > aslice['xmin']:
			continue  # abandon the slice for the repeated one
		
		filled_slices.append(aslice)
		previous_xmax = aslice['xmax']
	return filled_slices

# added latter
# to solve the case that several pieces with same name but without slice number
# this case may lead an incorrectly prefilling
def reslice(slices):
	INCREMENT = 2
	if slices[0]['slice'] == None:	# unsliced before
		slices.sort(key=lambda x: x['xmin'])
		slices[0]['slice'] = 1 if slices[0]['xmin'] == 0 else 2 
		for s in slices:
			if s['slice'] is None:
				s['slice'] = pre_slice_no + INCREMENT
			pre_slice_no = s['slice']
	return slices

# output all audio files' name
def write_filenames(dst_file, items):
	with open(dst_file, 'w') as f:
		for filename in items.keys():
			name = (filename+DEFAULT_MEDIA+'\n')
			f.write(name.encode('utf-8'))

def preprocess(items):
	for filename, slices in items.items():
		reslice(slices)
		items[filename] = prefill_slices(slices)

def output_textgrids(root_dir, items):
	if not os.path.exists(root_dir):
		os.makedirs(root_dir)
	# ordered = collections.OrderedDict(sorted(items.items()))
	for filename, slices in items.items():
		dst = root_dir + os.sep + filename + '.textgrid'
		with open(dst, "w") as f:
			f.write(generate_output(slices))

	names_txt = root_dir + 'names.txt'
	write_filenames(names_txt, items)


if __name__ == '__main__':
	items = {}
	parse_file(sys.argv[1], items)
	directory_name = sys.argv[1].split('.')[0]
	preprocess(items)
	output_textgrids(directory_name, items)