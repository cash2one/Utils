# -*- coding: utf-8 -*-
# parse_blocks.py - usage:
	# tp = TextgridBlocksParser();
	# tp.read(src_file);
	# intervals = tp.parse_blocks();
	# process intervals
# class to parse intevals in textgrid, generates a list containing all inforamtion 
# author: xiao yang <xiaoyang0117@gmail.com>
# date: 2016.Mar.09

import re
import chardet
from itertools import cycle
import settings
from settings import logger

class UpperLayerException(Exception):
	pass


class CycleIterator(object):
	""" a wrapper for the itertools.cycle """
	def __init__(self, iterable):
		super(CycleIterator, self).__init__()
		self.iterable = iterable
		self.iterator = cycle(iterable)
		self.value = None
	
	def head(self):
		return self.iterable[0]

	def tail(self):
		return self.iterable[-1]

	def next(self):
		self.value = self.iterator.next()
		return self.value

	def begins(self):
		return self.value == self.iterable[0]

	def ends(self):
		return self.value == self.iterable[-1]

	# to loop from the begining
	def reset(self):
		self.iterator = cycle(self.iterable)
		return self.next()

	def index(self, i):
		return self.iterable[i]


class TextgridBlocksParser(object):
	"""translate the textgrid into a dict"""

	ITEM_PATTERN = (
		(re.compile('^\s*item \[(?P<item_index>\d+)\]:'), 'item_index', int),
        (re.compile('^\s*class = "(?P<class>\w+)"', re.UNICODE), 'class', unicode), 
        (re.compile('^\s*name = "(?P<name>\w*)"', re.UNICODE), 'name', unicode),
        (re.compile('^\s*xmin = (?P<xmin>[\d\.]+)'), 'xmin', float),
		(re.compile('^\s*xmax = (?P<xmax>[\d\.]+)'), 'xmax', float),
        (re.compile('^\s*intervals: size = (?P<size>\d+)'), 'size', int),
		)

	# a block stands for each interval in an item
	BLOCK_PATTERN = (
		(re.compile('^\s*intervals \[(?P<slice>\d+)\]:', re.UNICODE), 'slice', int),
		(re.compile('^\s*xmin = (?P<xmin>[\d\.]+)', re.UNICODE), 'xmin', float),
		(re.compile('^\s*xmax = (?P<xmax>[\d\.]+)', re.UNICODE), 'xmax', float),
		(re.compile('^\s*text = "(?P<text>.*)"', re.UNICODE), 'text', unicode),
		)
	# for a special case that one text has multiple lines
	MULTILINES_PATTERN = (
		(re.compile('^\s*text = "(?P<text>.*)', re.UNICODE), 'text', unicode),
		(re.compile('^(?P<text>.*)$', re.UNICODE), 'text', unicode),	# to adapt the new line
		(re.compile('^(?P<text>.*)"\s*$', re.UNICODE), 'text', unicode),
	)

	# keys for each element of the tuple in BLOCK_PATTERN and MULTILINES_PATTERN
	PATTERN_KEYS = ('pattern', 'key', 'type')
	# after calling self.__pack(PATTERN_KEYS, BLOCK_PATTERN) 
	# BLOCK_PATTERN will be transformed into a dict as below:
	# BLOCK_PATTERN = (
	# 	{'pattern': re.compile('^\s*intervals \[(?P<slice>\d+)\]:'), 'key: 'slice', 'type': int},
	# 	......
	# 	)

	def __init__(self, coding='utf-8'):
		super(TextgridBlocksParser, self).__init__()
		self.default_coding = coding
		self.lineno = 0
		self.data = {}
		self.original_duration_sum = 0

	def __reset(self):
		self.data = {}

	def read(self, filename, quiet=False):
		self.filename = filename
		if not quiet:
			try:
				logger.info('processing file: %s' % filename.decode(settings.DECODING).encode(settings.ENCODING))
			except UnicodeDecodeError, e:
				logger.info('processing file ...')

		with open(self.filename, 'rb') as f:
			raw_data = f.read()
			self.coding = chardet.detect(raw_data)['encoding']
			# self.coding = self.__code_det(raw_data[0:10])
			try:
				self.content = raw_data.decode(self.coding)
				self.lines = self.content.splitlines()
			except UnicodeError, e:
				logger.error('unable to decode file %s, please open with a text editor and save it with encoding utf-8' % self.filename)
				raise e
		return self

	# auxiliary method to assemble tuples with corresponding keys
	# provided for those lazy people
	def __pack(self, keys, tuples):
		package = []
		for vals in tuples:
			package.append({ keys[i]:vals[i] for i in range(len(keys)) })
		return package

	# to update values in interval
	def __update(self, interval, line_pattern, line, append=False):
		ip = line_pattern
		if append:
			# only for text in multiple lines
			interval[ip['key']] += ip['type'](ip['pattern'].match(line).group(ip['key']))
		else:
			# eg. interval.update('slice': int(re_parser.match(line).group('slice')))
			interval.update({ ip['key']: ip['type'](ip['pattern'].match(line).group(ip['key'])) }) 
		return interval

	# only works with BLOCK_PATTERN
	def __match(self, line_pattern, line):
		return line_pattern['pattern'].match(line)

	# adaptor to get information about item, such as name, class
	def parse_items(self):
		item, items = {}, []
		ip_iter = CycleIterator(self.__pack(TextgridBlocksParser.PATTERN_KEYS, TextgridBlocksParser.ITEM_PATTERN))
		line_pattern = ip_iter.next()

		def block_ends(item, items):
			item['lineno'] = lineno - 5
			items.append(item)

		for lineno, line in enumerate(self.lines, start=1):
			if not ip_iter.begins() and self.__match(ip_iter.head(), line):
				item, line_pattern = {}, ip_iter.reset()

			if self.__match(line_pattern, line):
				self.__update(item, line_pattern, line)

				if ip_iter.ends():
					block_ends(item, items)
					item = {}
			else:
				continue
			line_pattern = ip_iter.next()
		return items


	def parse_blocks(self):		
		lineno, interval, intervals = 0, {}, []

		def block_ends(interval, intervals):
			interval['lineno'] = lineno
			intervals.append(interval)

		# iterator for MULTILINES_PATTERN
		mp_iter = CycleIterator(self.__pack(TextgridBlocksParser.PATTERN_KEYS, TextgridBlocksParser.MULTILINES_PATTERN))
		# iterator for BLOCK_PATTERN
		bp_iter = CycleIterator(self.__pack(TextgridBlocksParser.PATTERN_KEYS, TextgridBlocksParser.BLOCK_PATTERN))
		line_pattern = bp_iter.next()

		for line in self.lines:
			lineno += 1

			# always try to match the begining pattern at first to avoid missing a normal block 
			# therefore, reset the block parsing once a line was matched to the begining pattern
			# but unmatched to the current one.
			if not bp_iter.begins() and self.__match(bp_iter.head(), line):
				logger.error('unable to parse line %d, ignored' % (lineno-1))
				interval, line_pattern = {}, bp_iter.reset()

			# to match the pattern one by one until it ends
			if self.__match(line_pattern, line):
				self.__update(interval, line_pattern, line)

				# if the end of block was matched
				# block ends here for most situation
				if bp_iter.ends():
					block_ends(interval, intervals)
					interval = {}

			# when a text existed in multiple lines
			elif bp_iter.ends():
					# match the begining of text in multi-lines
					if self.__match(mp_iter.head(), line):
						self.__update(interval, mp_iter.head(), line)
						continue # should not to call the next block pattern

					# match the pattern of end line
					# block also may end here for multiple lines
					elif self.__match(mp_iter.tail(), line): 
						self.__update(interval, mp_iter.tail(), line, append=True)
						block_ends(interval, intervals)
						interval = {}

					# match the pattern without quotes
					else:
						# append the middle part of the text
						self.__update(interval, mp_iter.index(1), line, append=True)
						continue
			else:
				# does not match anything
				# logger.error('unable to parse line %d, ignored' % (lineno-1))
				continue
			
			line_pattern = bp_iter.next()	# match the next pattern

		return intervals
