import argparse
import re
from operator import contains
from pathlib import Path

REGEX_LABEL = re.compile(r"label %(.*?)(?:\,|$)")
REGEX_DEFINE = re.compile(r"define .*? (.*?)\(")
REGEX_BLOCK_LABEL = re.compile(r"^\s*(.*?):")
REGEX_RETURN = re.compile(r"\bret\b")
REGEX_CALL = re.compile(r"\bcall\b")
REGEX_STORE = re.compile(r"store (?P<storetype>.*?) %(?P<storefrom>.*?), ptr %(?P<storeto>.*?)$")
REGEX_STORE_CONST = re.compile(
	r"store (?P<storetype>.*?) (?P<storefrom>.*?), ptr %(?P<storeto>.*?)$"
)
REGEX_SOURCE = re.compile(r"%(?P<varname>.*?) {0,}= {0,}call .*?@(.*?)\b")
REGEX_SINK = re.compile(r"\bcall void @SINK\(.*? %(?P<varname>.*?)\)")
REGEX_LOAD = re.compile(
	r"%(?P<loadto>.*?)\s{0,}=\s{0,}load\s{0,}(?P<type>.*?),\s{0,}ptr %(?P<loadfrom>.*?)$"
)
SECRET_SOURCES: dict[str, list[str]] = {}
SINKS: dict[str, list[str]] = {}


class expression:
	expressiontype: str = ""
	regexresult: re.Match[str] | None = None
	text: str = ""

	def __init__(self, text: str, expressiontype: str, regexresult: re.Match[str] | None):
		self.expressiontype = expressiontype
		self.regexresult = regexresult
		self.text = text

	def __repr__(self) -> str:
		return f'expression(type={self.expressiontype}, text="{self.text}")'


class blockType:
	parts: list[expression]
	name: str
	connections: list[str]
	referenced: list[str]
	setvars: list[dict[str, str]]

	def __init__(
		self,
		name: str,
		connections: list[str] | None = None,
		referenced: list[str] | None = None,
		setvars: list[dict[str, str]] | None = None,
		parts: list[expression] | None = None,
	):
		self.parts = [] if parts is None else parts
		self.name = name
		self.connections = [] if connections is None else connections
		self.referenced = [] if referenced is None else referenced
		self.setvars = [] if setvars is None else setvars
		# Immediant modified and referenced


class function:
	gref: set[str]
	fromblock: str
	toblock: str

	def __init__(self, gref: set[str], fromblock: str, toblock: str):
		self.gref = gref
		self.fromblock = fromblock
		self.toblock = toblock


def resolve(name: str, values: dict[str, str]) -> str:
	seen: set[str] = set()
	while name not in seen and name in values:
		# add to prevent loops
		seen.add(name)
		# set to its next value
		name = values[name]
		# return the result
	return name


def worklist(
	blocks: dict[str, blockType],
) -> bool:
	# return true if there is a flow from a secret source to a sink
	work: list[blockType] = list(blocks.values())
	while work:
		# pop off the top
		block = work.pop()
		# get the connected blocks
		for connection in block.connections:
			# make sure the connected block is real, mostly just here for type checking
			if connection in blocks:
				# get the block
				connected_block: blockType = blocks[connection]
				# get the set for the currect blocks refrences
				merged_referenced: set[str] = set(block.referenced)
				# merge them and the connected blocks refrences
				merged_referenced.update(connected_block.referenced)
				list_setvars = block.setvars
				for setvar in connected_block.setvars:
					# make sure we don't have dupes
					if setvar not in list_setvars:
						list_setvars.append(setvar)
						# appending conedention mentioned in class
				if merged_referenced != set(block.referenced) or list_setvars != block.setvars:
					# update the referenced to the merged referenced
					block.referenced = list(merged_referenced)
					# update the setvars to the merged setvars
					block.setvars = list_setvars
					# append the block to work
					work.append((block))
				else:
					continue
			else:
				continue
	values: dict[str, str] = {}
	sources: set[str] = set()
	sinks: list[str] = []
	# basicly this section is just checking for flow from source -> sink now that we have sorted out setvars and refrences.
	# Their is a hidden bug with this because if you store into a pointer after the sink, because we resolve it all first it will think that their is no flow when their is.
	# I am however, very tiered, and that would require me to completly rewrite everything to fix it.
	for blockname, block in blocks.items():
		for assignment in block.setvars:
			values.update(assignment)
		sources.update(SECRET_SOURCES.get(blockname, []))
		sinks.extend(SINKS.get(blockname, []))
	return any(resolve(sink, values) in sources for sink in sinks)


def process_function(lines: list[str]) -> None:
	# STARTS BLOCK: define, LABELNAME:.
	# ENDS BLOCK: br, ret
	# jumps to block: br, call
	# step 1: go line by line, breaking into blocks
	# step 2: find jump points
	# step 3: output graph
	inblock = False
	blocknames: list[str] = []
	blocks: dict[str, blockType] = {}
	currentname = ""
	functioname = ""
	for i in lines:
		if i.strip().startswith(";"):
			continue
		if not inblock:
			# regex for checking for define
			define = REGEX_DEFINE.match(i)
			if define is not None:
				blocknames.append(define.group(1))
				inblock = True
				currentname = define.group(1)
				blocks[currentname] = blockType(currentname)
				functioname = currentname
				blocks[currentname].parts.append(expression(i, "define", define))
				SECRET_SOURCES[currentname] = []
				SINKS[currentname] = []

				continue
			labels = REGEX_BLOCK_LABEL.match(i)
			if labels is not None:
				blocknames.append(labels.group(1))
				currentname = labels.group(1)
				blocks[currentname] = blockType(currentname)

				blocks[currentname].parts.append(expression(i, "labels", labels))
				SECRET_SOURCES[currentname] = []
				SINKS[currentname] = []
				inblock = True
				continue
		else:
			# we are in a block
			# so look for end points
			if REGEX_RETURN.search(i):
				blocks[currentname].parts.append(expression(i, "return", None))
				inblock = False
				continue
			# the issue is their can be multiple labels per br so
			isBr = i.strip().startswith("br")
			if isBr:
				# now we can safly just match for label %LABEL
				brLabels = REGEX_LABEL.findall(i)
				brs = REGEX_LABEL.match(i)
				for x in brLabels:
					blocks[currentname].connections.append(x)
				blocks[currentname].parts.append(expression(i, "br", brs))
				inblock = False
				continue
			sink = REGEX_SINK.search(i)
			if sink:
				namer = sink.group("varname")
				SINKS[currentname].append(namer)
				blocks[currentname].parts.append(expression(i, "sink", sink))
				continue
			source_match = REGEX_SOURCE.search(i)

			if source_match:
				# add the source to the secret sources list
				source_name = source_match.group("varname")
				SECRET_SOURCES[currentname].append(source_name)
				blocks[currentname].setvars.append({source_name: source_name})
				blocks[currentname].parts.append(expression(i, "source", source_match))
				continue

			store = REGEX_STORE.match(i.strip())

			# dumb hack to handle constants in store not matching the standerd one.
			if store is None:
				store = REGEX_STORE_CONST.match(i.strip())
			if store is not None:
				storefrom = store.group("storefrom")
				storeto = store.group("storeto")
				blocks[currentname].setvars.append({storeto: storefrom})
				blocks[currentname].referenced.extend([storefrom, storeto])
				blocks[currentname].parts.append(expression(i, "store", store))
				continue

			load = REGEX_LOAD.match(i.strip())
			if load is not None:
				loadfrom = load.group("loadfrom")
				loadto = load.group("loadto")
				blocks[currentname].setvars.append({loadto: loadfrom})
				blocks[currentname].referenced.extend([loadto, loadfrom])
				blocks[currentname].parts.append(expression(i, "load", load))
				continue

			call = REGEX_CALL.search(i)
			if call:
				blocks[currentname].parts.append(expression(i, "call", call))
				continue

			blocks[currentname].parts.append(expression(i, "unknown", None))

	if worklist(blocks):
		print("FLOW")
	else:
		print("NO FLOW")

	# outputToFile(functioname.strip("@"), blocks)


def main() -> None:
	parser = argparse.ArgumentParser(
		prog="llvm to graph", description="converts ll to dot notation graph"
	)
	_ = parser.add_argument("filename")
	args = parser.parse_args()
	# get the provided file
	llfile = Path("./" + args.filename)
	# open it in read mode
	with llfile.open("r") as f:
		# get the lines
		lines = f.readlines()

		# first we need to get the functions
		# then we send them to process_function
		functions: dict[str, list[str]] = {}
		infunction = False
		# keeps track if a function has started yet
		firstfunction = False
		name = ""
		for i in lines:
			if not infunction:
				define = REGEX_DEFINE.match(i)
				if define is not None:
					name = define.group(1)
					functions[name] = []
					functions[name].append(i)
					infunction = True
					firstfunction = True
				elif firstfunction == False:
					name = "global"
					functions[name] = []
					functions[name].append(i)

			else:
				if contains(i, "}"):
					functions[name].append(i)
					name = ""
					infunction = False
				else:
					functions[name].append(i)
		for _, functionlist in functions.items():
			process_function(functionlist)


def outputToFile(name: str, blocks: dict[str, blockType]) -> None:
	outfile = Path(f"./{name}.dot")
	x = 0
	output = "digraph {\n"
	nodes: dict[str, int] = {}
	for key in blocks:
		# this line is for testing to see what is in each block
		label = (
			"\\n".join([i.text for i in blocks[key].parts])
			.replace("\n", "\\n")
			.replace("{", "")
			.replace("}", "")
		)
		# label = ""
		output += "		Node" + str(x) + f' [shape=record,label="{label}"]\n'
		nodes[key] = x
		x += 1
	x = 0
	for key, value in blocks.items():
		j = 0
		for i in value.connections:
			output += (
				"		Node" + str(x) + " -> Node" + str(nodes[i]) + " [label=" + str(j) + "];\n"
			)
			j += 1
		x += 1
	output += "}"
	with outfile.open("w+") as f:
		_ = f.write(output)


if __name__ == "__main__":
	main()
